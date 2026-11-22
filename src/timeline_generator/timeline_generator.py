"""
LLM-powered Timeline Generator for Animation Pipeline
This module integrates with local LLM services to generate structured animation timelines from text scripts.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TimelineEntry(BaseModel):
    """Represents a single entry in the animation timeline"""
    timestamp: str = Field(..., description="Timestamp in HH:MM:SS format")
    description: str = Field(..., description="Description of the animation element")
    duration: float = Field(..., description="Duration in seconds")
    type: str = Field(..., description="Type of animation element (character, background, effect)")
    visual_prompt: Optional[str] = Field(None, description="Detailed visual prompt for video/image generation")
    dialogue: Optional[str] = Field(None, description="Spoken dialogue or narration for this shot, if any")
    audio_required: bool = Field(True, description="Whether this shot requires audio generation")
    camera_movement: Optional[str] = Field(None, description="Camera directive, e.g. static, pan, push")

class AnimationTimeline(BaseModel):
    """Represents a complete animation timeline"""
    entries: List[TimelineEntry] = Field(..., description="List of timeline entries")
    total_duration: float = Field(..., description="Total duration of the timeline in seconds")

class TimelineGenerator:
    """Generates animation timelines from text descriptions using LLMs"""
    
    def __init__(self, api_base_url: str = "http://localhost:8000/v1", model: str = "qwen"):
        """
        Initialize the timeline generator
        
        Args:
            api_base_url: Base URL for the LLM API endpoint
            model: Model name served by the OpenAI-compatible endpoint
        """
        self.api_base_url = api_base_url
        self.model = model
        self.client = OpenAI(
            base_url=api_base_url,
            api_key="dummy-key"  # We'll use dummy key since we're using vLLM
        )
        
        logger.info(f"Initialized TimelineGenerator with API base URL: {api_base_url}")
    
    def generate_timeline(self, script: str, context: Dict[str, Any] = None) -> AnimationTimeline:
        """
        Generate an animation timeline from a text script
        
        Args:
            script: Text script describing the animation sequence
            context: Additional context for timeline generation
            
        Returns:
            AnimationTimeline: Structured timeline object
        """
        try:
            # Prepare the prompt for the LLM
            prompt = self._build_prompt(script, context or {})
            
            # Call the LLM API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert animation timeline generator. Convert text descriptions into structured JSON format with timestamps, descriptions, durations, and element types."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            result = response.choices[0].message.content
            timeline_data = json.loads(result)
            
            # Validate and return the timeline
            timeline = AnimationTimeline.model_validate(timeline_data)
            
            logger.info(f"Successfully generated timeline with {len(timeline.entries)} entries")
            return timeline
            
        except Exception as e:
            logger.warning(f"LLM timeline generation failed or offline ({e}). Using deterministic script parser fallback.")
            return self._fallback_parse_script(script)

    def _fallback_parse_script(self, script: str) -> AnimationTimeline:
        """Deterministic rule-based parser when LLM inference node is offline."""
        lines = [line.strip() for line in script.strip().splitlines() if line.strip()]
        entries = []
        current_shot = {}
        total_time = 0.0

        for line in lines:
            line_lower = line.lower()
            if line_lower.startswith("shot") or line_lower.startswith("scene:"):
                if current_shot.get("description"):
                    entries.append(self._create_entry(current_shot, total_time))
                    total_time += current_shot.get("duration", 2.0)
                    current_shot = {}
                current_shot["description"] = line
            elif line_lower.startswith("visual:"):
                current_shot["visual_prompt"] = line.split(":", 1)[1].strip()
                if "description" not in current_shot:
                    current_shot["description"] = current_shot["visual_prompt"]
            elif line_lower.startswith("dialogue:"):
                current_shot["dialogue"] = line.split(":", 1)[1].strip().strip('"')
            elif line_lower.startswith("duration:"):
                try:
                    dur_str = line.split(":", 1)[1].replace("seconds", "").replace("s", "").strip()
                    current_shot["duration"] = float(dur_str)
                except ValueError:
                    current_shot["duration"] = 2.0

        if current_shot.get("description") or current_shot.get("visual_prompt"):
            entries.append(self._create_entry(current_shot, total_time))
            total_time += current_shot.get("duration", 2.0)

        if not entries:
            # Fallback for plain text
            entries.append(
                TimelineEntry(
                    timestamp="00:00:00",
                    description=script[:50],
                    duration=3.0,
                    type="character",
                    visual_prompt=script,
                    dialogue=script,
                    audio_required=True,
                    camera_movement="static",
                )
            )
            total_time = 3.0

        return AnimationTimeline(entries=entries, total_duration=round(total_time, 2))

    @staticmethod
    def _create_entry(shot_data: Dict[str, Any], current_time: float) -> TimelineEntry:
        mins = int(current_time // 60)
        secs = int(current_time % 60)
        timestamp = f"00:{mins:02d}:{secs:02d}"
        dur = shot_data.get("duration", 2.5)
        desc = shot_data.get("description", "Animation shot")
        vis = shot_data.get("visual_prompt") or desc
        dia = shot_data.get("dialogue")
        return TimelineEntry(
            timestamp=timestamp,
            description=desc,
            duration=dur,
            type="character",
            visual_prompt=vis,
            dialogue=dia,
            audio_required=bool(dia),
            camera_movement="static",
        )
    
    def _build_prompt(self, script: str, context: Dict[str, Any]) -> str:
        """
        Build a comprehensive prompt for the LLM
        
        Args:
            script: Original script text
            context: Additional context
            
        Returns:
            Formatted prompt string
        """
        prompt_parts = [
            f"Convert this animation script into a structured timeline:",
            f"Script: '{script}'",
            "Response format:",
            "{",
            '"entries": [',
            '{"timestamp": "HH:MM:SS", "description": "element description", "duration": 0.0, "type": "character/background/effect", "visual_prompt": "Cinematic visual prompt for video generation", "dialogue": "Spoken line or null", "camera_movement": "static/push/pan"}',
            "],",
            '"total_duration": 0.0',
            "}",
            "Rules:",
            "- Each entry should have a unique timestamp",
            "- Duration should be realistic (typically 1-5 seconds)",
            "- Element types should be 'character', 'background', or 'effect'",
            "- Provide a rich visual_prompt suitable for AI video generation",
            "- Total duration should be sum of all entry durations"
        ]
        
        if context:
            prompt_parts.extend([
                "Context information:",
                json.dumps(context, indent=2)
            ])
        
        return "\n".join(prompt_parts)

# Example usage function
def demo_timeline_generation():
    """Demonstrate timeline generation functionality"""
    generator = TimelineGenerator()
    
    sample_script = "A character walks from left to right across a scenic landscape, then jumps and lands with a splash effect"
    
    try:
        timeline = generator.generate_timeline(sample_script)
        print("Generated Timeline:")
        print(json.dumps(timeline.model_dump(), indent=2))
        return timeline
    except Exception as e:
        print(f"Error in demo: {e}")
        return None

if __name__ == "__main__":
    demo_timeline_generation()