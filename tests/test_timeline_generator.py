"""
Test suite for Timeline Generator
"""

import json
import pytest
from src.timeline_generator.timeline_generator import (
    TimelineGenerator, 
    AnimationTimeline, 
    TimelineEntry
)

def test_timeline_entry_creation():
    """Test creating a timeline entry"""
    entry = TimelineEntry(
        timestamp="00:00:05",
        description="Character appears on screen",
        duration=2.0,
        type="character"
    )
    
    assert entry.timestamp == "00:00:05"
    assert entry.description == "Character appears on screen"
    assert entry.duration == 2.0
    assert entry.type == "character"

def test_animation_timeline_creation():
    """Test creating an animation timeline"""
    entry1 = TimelineEntry(
        timestamp="00:00:05",
        description="Character appears on screen",
        duration=2.0,
        type="character"
    )
    
    entry2 = TimelineEntry(
        timestamp="00:00:07",
        description="Character walks right",
        duration=3.0,
        type="character"
    )
    
    timeline = AnimationTimeline(
        entries=[entry1, entry2],
        total_duration=5.0
    )
    
    assert len(timeline.entries) == 2
    assert timeline.total_duration == 5.0

def test_timeline_generator_initialization():
    """Test timeline generator initialization"""
    generator = TimelineGenerator("http://localhost:8000/v1")
    
    assert generator.api_base_url == "http://localhost:8000/v1"

if __name__ == "__main__":
    # Run tests manually if needed
    test_timeline_entry_creation()
    test_animation_timeline_creation()
    test_timeline_generator_initialization()
    print("All tests passed!")