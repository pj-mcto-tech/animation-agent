# Timeline Generator Integration

This document provides detailed information about the timeline generator integration within the animation pipeline, covering its architecture, API contracts, and integration points.

## Overview

The timeline generator is a core component of the animation pipeline that transforms text scripts into structured animation timelines using local LLM services. It serves as the bridge between natural language descriptions and structured animation data.

## Architecture

### Core Components

#### TimelineEntry Model
```python
class TimelineEntry(BaseModel):
    timestamp: str = Field(..., description="Timestamp in HH:MM:SS format")
    description: str = Field(..., description="Description of the animation element")
    duration: float = Field(..., description="Duration in seconds")
    type: str = Field(..., description="Type of animation element (character, background, effect)")
```

#### AnimationTimeline Model
```python
class AnimationTimeline(BaseModel):
    entries: List[TimelineEntry] = Field(..., description="List of timeline entries")
    total_duration: float = Field(..., description="Total duration of the timeline in seconds")
```

#### TimelineGenerator Class
```python
class TimelineGenerator:
    def __init__(self, api_base_url: str = "http://localhost:8000/v1"):
        """Initialize the timeline generator"""
        
    def generate_timeline(self, script: str, context: Dict[str, Any] = None) -> AnimationTimeline:
        """Generate an animation timeline from a text script"""
```

### Integration Points

The timeline generator integrates with the core pipeline through:
1. **Pipeline Stage 2**: Called from `src/core/pipeline.py` in the `_generate_timeline()` method
2. **API Communication**: Connects to local LLM endpoint at `http://localhost:8000/v1`
3. **Data Flow**: Exchanges structured JSON data with the pipeline

## API Contracts

### TimelineGenerator Interface
```python
class TimelineGenerator:
    def generate_timeline(self, script: str, context: Dict[str, Any] = None) -> AnimationTimeline
```

### Expected Data Formats

#### TimelineEntry Structure
```json
{
  "timestamp": "HH:MM:SS",
  "description": "Element description",
  "duration": 0.0,
  "type": "character/background/effect"
}
```

#### AnimationTimeline Structure
```json
{
  "entries": [
    {
      "timestamp": "HH:MM:SS",
      "description": "Element description",
      "duration": 0.0,
      "type": "character/background/effect"
    }
  ],
  "total_duration": 0.0
}
```

## Implementation Details

### Initialization
The timeline generator initializes with an API base URL pointing to the local LLM service:
- Default endpoint: `http://localhost:8000/v1`
- Uses OpenAI-compatible client for LLM communication
- Configures logging for debugging and monitoring

### Prompt Engineering
The generator constructs comprehensive prompts for LLM processing:
- Converts natural language script to structured timeline
- Defines required response format with timestamps, descriptions, durations, and types
- Includes rules for realistic timing and element categorization

### Data Validation
- Uses Pydantic models for strict data validation
- Ensures all required fields are present and correctly formatted
- Validates timestamp format (HH:MM:SS)
- Validates element types (character, background, effect)

## Integration with Core Pipeline

### Pipeline Flow
1. **Stage 1**: Script Processing - Extracts and prepares input script
2. **Stage 2**: Timeline Generation - Calls `TimelineGenerator.generate_timeline()` 
3. **Stage 3**: Audio Coordination - Uses timeline data for audio generation
4. **Stage 4**: Asset Packaging - Packages timeline and audio assets
5. **Stage 5**: Final Results - Returns complete pipeline execution data

### Method Integration
In `src/core/pipeline.py`, the timeline generation is called as:
```python
def _generate_timeline(self, script_data: Dict[str, Any]) -> Dict[str, Any]:
    # Uses TimelineGenerator from src/timeline_generator/timeline_generator.py
    # Returns structured timeline data with entries and metadata
```

## Configuration Requirements

- **LLM Endpoint**: `http://localhost:8000/v1` (vLLM instance)
- **Model Name**: `qwen` (configured for Qwen LLM)
- **API Key**: Dummy key used with vLLM (not required for local deployment)

## Error Handling and Logging

- Comprehensive error handling for LLM communication failures
- Detailed logging for debugging and monitoring
- Graceful failure handling with appropriate error messages
- Validation error reporting for malformed data

## Testing and Validation

The timeline generator has comprehensive test coverage:
- Unit tests for TimelineEntry and AnimationTimeline models
- Integration tests for LLM communication
- End-to-end pipeline testing
- Error handling validation