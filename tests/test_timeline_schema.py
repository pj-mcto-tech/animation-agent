"""Unit tests for the extended TimelineEntry and AnimationTimeline schema."""

from src.timeline_generator.timeline_generator import AnimationTimeline, TimelineEntry


def test_timeline_entry_defaults():
    """Ensure older timeline payloads without new fields load with expected defaults."""
    entry = TimelineEntry(
        timestamp="00:00:00",
        description="Character waves hello",
        duration=3.0,
        type="character",
    )
    assert entry.visual_prompt is None
    assert entry.dialogue is None
    assert entry.audio_required is True
    assert entry.camera_movement is None


def test_timeline_entry_with_visual_prompt_and_dialogue():
    """Ensure extended fields are retained and validated properly."""
    entry = TimelineEntry(
        timestamp="00:00:03",
        description="Hero speaks",
        duration=4.5,
        type="character",
        visual_prompt="Cinematic close-up of hero speaking, anime style, 8k",
        dialogue="Welcome to the future of animation!",
        audio_required=True,
        camera_movement="push-in",
    )
    assert entry.visual_prompt == "Cinematic close-up of hero speaking, anime style, 8k"
    assert entry.dialogue == "Welcome to the future of animation!"
    assert entry.audio_required is True
    assert entry.camera_movement == "push-in"


def test_animation_timeline_validation():
    """Verify AnimationTimeline validates list of entries with extended fields."""
    entries = [
        TimelineEntry(
            timestamp="00:00:00",
            description="Shot 1",
            duration=2.0,
            type="background",
            visual_prompt="Scenic sunset over mountains",
            audio_required=False,
        ),
        TimelineEntry(
            timestamp="00:00:02",
            description="Shot 2",
            duration=3.0,
            type="character",
            dialogue="Look at that view!",
            visual_prompt="Character admiring sunset",
        ),
    ]
    timeline = AnimationTimeline(entries=entries, total_duration=5.0)
    assert len(timeline.entries) == 2
    assert timeline.total_duration == 5.0
    dumped = timeline.model_dump()
    assert dumped["entries"][0]["visual_prompt"] == "Scenic sunset over mountains"
    assert dumped["entries"][0]["audio_required"] is False
    assert dumped["entries"][1]["dialogue"] == "Look at that view!"
