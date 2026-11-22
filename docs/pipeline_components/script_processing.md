# Script Processing Component

This document provides detailed information about the script processing component of the animation pipeline.

## Overview

The script processing component is responsible for parsing and preparing input script files for timeline generation. It extracts essential metadata and structures the content for downstream processing.

## Architecture

### Core Functionality

#### Script Processing Method
```python
def _process_script(self, script_file: str) -> Dict[str, Any]:
    """
    Process the input script file.
    
    Args:
        script_file (str): Path to script file
        
    Returns:
        Dict[str, Any]: Processed script data with metadata
    """
```

### Data Flow

The script processing component handles:
- Reading raw script content
- Parsing and structuring the text
- Extracting key metadata (title, author, version)
- Preparing data for timeline generation

## Implementation Details

### Input Handling
- Accepts path to script file as input
- Reads and processes the entire script content
- Handles various script formats and structures

### Metadata Extraction
- Extracts title information
- Identifies author information
- Captures version information
- Maintains original file reference

### Data Structure
The processed script data follows this structure:
```json
{
  "original_file": "path/to/script.txt",
  "processed_text": "Processed script content",
  "metadata": {
    "title": "Animation Script",
    "author": "AI Assistant",
    "version": "1.0"
  }
}
```

## Integration with Core Pipeline

### Pipeline Flow
1. **Stage 1**: Script Processing - Parses and prepares input script
2. **Stage 2**: Timeline Generation - Uses processed script data
3. **Stage 3**: Audio Coordination - Processes script for audio requirements
4. **Stage 4**: Asset Packaging - Packages script-related assets
5. **Stage 5**: Final Results - Returns complete pipeline execution data

### Method Integration
In `src/core/pipeline.py`, the script processing is called as:
```python
def _process_script(self, script_file: str) -> Dict[str, Any]:
    # Reads raw script content
    # Parses and structures the text
    # Extracts key metadata (title, author, version)
    # Returns processed script data with metadata
```

## Configuration Requirements

- **Input Directory**: `data/input` (default location for script files)
- **File Format**: Text-based scripts (support for various formats)
- **Metadata Handling**: Preserves original script metadata

## Error Handling and Logging

- Handles file reading errors gracefully
- Logs processing progress and completion
- Reports parsing errors and warnings
- Maintains audit trail of processing steps

## Testing and Validation

The script processing component is tested with:
- File I/O validation
- Metadata extraction verification
- Error condition handling
- Integration with timeline generation flow