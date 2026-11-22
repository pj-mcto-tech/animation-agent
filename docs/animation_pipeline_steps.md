# Animation Pipeline Steps

This document outlines the complete animation pipeline workflow, integrating the timeline generator with core pipeline components.

## Overview

The animation pipeline is a multi-stage workflow that transforms text scripts into animated content packages compatible with Cartoon Animator. The pipeline consists of five main stages:

1. **Script Processing**
2. **Timeline Generation** *(Integrated with Timeline Generator)*
3. **Audio Coordination**
4. **Asset Packaging**
5. **Final Results**

## Pipeline Stages

### 1. Script Processing
- **Location**: `src/core/pipeline.py`
- **Function**: `_process_script()`
- **Description**: Processes the input script file to extract and prepare content for timeline generation.
- **Input**: Path to script file
- **Output**: Processed script data with metadata
- **Data Flow**: 
  - Reads raw script content
  - Parses and structures the text
  - Extracts key metadata (title, author, version)
  - Passes to timeline generation stage

### 2. Timeline Generation *(Integrated with Timeline Generator)*
- **Location**: `src/core/pipeline.py` (calls `_generate_timeline()`), `src/timeline_generator/timeline_generator.py`
- **Function**: `_generate_timeline()` in pipeline, `TimelineGenerator.generate_timeline()` in timeline generator
- **Description**: Generates structured JSON timeline using local LLM service.
- **Integration Points**:
  - Uses `TimelineGenerator` class from `src/timeline_generator/timeline_generator.py`
  - Communicates with local LLM endpoint at `http://localhost:8000/v1`
  - Receives script data and generates structured timeline entries
- **Input**: Processed script data from stage 1
- **Output**: Structured timeline data with entries and metadata
- **Data Flow**:
  - Pipeline calls `TimelineGenerator().generate_timeline(script_data)`
  - Timeline generator processes script with LLM
  - Returns structured `AnimationTimeline` object
  - Contains list of `TimelineEntry` objects with timestamp, description, duration, and type
- **Key Features**:
  - Uses Pydantic models for data validation
  - Integrates with Qwen LLM via vLLM endpoint
  - Generates timestamps in HH:MM:SS format
  - Supports multiple element types (character, background, effect)

### 3. Audio Coordination
- **Location**: `src/core/pipeline.py`
- **Function**: `_coordinate_audio()`
- **Description**: Coordinates audio generation for the timeline elements.
- **Input**: Timeline data from stage 2
- **Output**: Audio coordination results with file references
- **Data Flow**:
  - Receives timeline data
  - Determines audio requirements based on timeline entries
  - Generates audio files for required elements
  - Returns audio metadata and file paths

### 4. Asset Packaging
- **Location**: `src/core/pipeline.py`
- **Function**: `_package_assets()`
- **Description**: Packages all assets for Cartoon Animator compatibility.
- **Input**: Timeline data and audio data from previous stages
- **Output**: Package results with asset paths
- **Data Flow**:
  - Combines timeline and audio data
  - Organizes assets in Cartoon Animator compatible structure
  - Creates ZIP package with all necessary files
  - Returns package path and asset list

### 5. Final Results
- **Location**: `src/core/pipeline.py`
- **Function**: `run_pipeline()`
- **Description**: Returns final pipeline execution results.
- **Output**: Complete pipeline results with status and data
- **Data Flow**:
  - Aggregates results from all stages
  - Returns success/failure status
  - Provides access to timeline, audio, and package data

## Integration Architecture

### Timeline Generator Integration
The timeline generator is integrated as a core component in the pipeline:

```
Pipeline Stage 1 → Timeline Generator → Pipeline Stage 3 → Pipeline Stage 4 → Final Package
    (Script Processing)   (Timeline Generation)   (Audio Coordination)   (Asset Packaging)
```

### Data Exchange Protocol
- **JSON Format**: All data exchanges use standardized JSON formats
- **Pydantic Validation**: Type safety enforced with Pydantic models
- **Error Handling**: Comprehensive error handling throughout the pipeline
- **Logging**: Detailed logging for debugging and monitoring

### API Contracts

#### Timeline Generator Interface
```python
class TimelineGenerator:
    def generate_timeline(self, script: str, context: Dict[str, Any] = None) -> AnimationTimeline
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

## Pipeline Execution Flow

1. **Initialization**: Pipeline loads configuration from `config.json`
2. **Stage 1**: Script Processing - Parse and prepare input script
3. **Stage 2**: Timeline Generation - Generate structured timeline using LLM
4. **Stage 3**: Audio Coordination - Generate audio for timeline elements
5. **Stage 4**: Asset Packaging - Package all assets for Cartoon Animator
6. **Stage 5**: Final Results - Return complete pipeline execution data

## Configuration Requirements

- **LLM Endpoint**: `http://localhost:8000/v1` (vLLM instance)
- **Storage Directories**: 
  - Input: `data/input`
  - Processed: `data/processed`  
  - Output: `data/output`
  - Shared Storage: `/mnt/shared_storage`

## Testing and Validation

The timeline generator has comprehensive test coverage:
- Unit tests for TimelineEntry and AnimationTimeline models
- Integration tests for LLM communication
- End-to-end pipeline testing
- Error handling validation

## Deployment Considerations

- Ensure LLM service is running at configured endpoint
- Verify storage directories are accessible
- Confirm proper permissions for shared storage
- Monitor pipeline execution logs for troubleshooting