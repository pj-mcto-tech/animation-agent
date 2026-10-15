#!/usr/bin/env python3
"""
Main entry point for the Animation Agent Pipeline.
"""

import sys
import os
from src.core.pipeline import AnimationPipeline

def main():
    """Main function to run the animation pipeline."""
    print("Starting Animation Agent Pipeline...")
    
    # Create pipeline instance
    pipeline = AnimationPipeline()
    
    # For demo purposes, we'll use a sample script file
    sample_script = "data/input/sample_script.txt"
    
    # Run the pipeline
    result = pipeline.run_pipeline(sample_script)
    
    # Display results
    print("\nPipeline Execution Results:")
    print(f"Status: {result['status']}")
    print(f"Current Stage: {result['stage']}")
    
    if result['status'] == 'success':
        print(f"Timeline generated with {result['timeline']['timeline_metadata']['total_shots']} shots")
        print(f"Audio files generated: {result['audio']['metadata']['total_audio_files']}")
        print(f"Package created: {result['package']['package_path']}")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()