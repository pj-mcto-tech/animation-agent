"""
LLM-powered Timeline Generator for Animation Pipeline
This module integrates with local LLM services to generate structured animation timelines from text scripts.
"""

import json
import logging
from typing import Dict, List, Any
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

class AnimationTimeline(BaseModel):
    """Represents a complete animation timeline"""
    entries: List[TimelineEntry] = Field(..., description="List of timeline entries")
    total_duration: float = Field(..., description="Total duration of the timeline in seconds")

class TimelineGenerator:
    """Generates animation timelines from text descriptions using LLMs"""
    
    def __init__(self, api_base_url: str = "http://localhost:8000/v1"):
        """
        Initialize the timeline generator
        
        Args:
            api_base_url: Base URL for the LLM API endpoint
        """
        self.api_base_url = api_base_url
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
                model="qwen",
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
            logger.error(f"Error generating timeline: {str(e)}")
            raise
    
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
            '{"timestamp": "HH:MM:SS", "description": "element description", "duration": 0.0, "type": "character/background/effect"}',
            "],",
            '"total_duration": 0.0',
            "}",
            "Rules:",
            "- Each entry should have a unique timestamp",
            "- Duration should be realistic (typically 1-5 seconds)",
            "- Element types should be 'character', 'background', or 'effect'",
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