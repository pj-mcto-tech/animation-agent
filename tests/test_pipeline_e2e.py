"""End-to-end integration tests for AnimationPipeline covering all 7 stages."""

import json
import os
import zipfile

from src.audio_generator.generator import AudioGenerator
from src.core.pipeline import AnimationPipeline
from src.lipsync.client import LipSyncClient
from src.timeline_generator.timeline_generator import (
    AnimationTimeline,
    TimelineEntry,
    TimelineGenerator,
)
from src.video_generator.generator import VideoGenerator


class DummyTimelineGenerator(TimelineGenerator):
    """Stub generator avoiding live LLM server calls."""

    def __init__(self):
        pass

    def generate_timeline(self, script: str, context=None) -> AnimationTimeline:
        return AnimationTimeline(
            entries=[
                TimelineEntry(
                    timestamp="00:00:00",
                    description="Opening landscape of sunset",
                    duration=1.0,
                    type="background",
                    visual_prompt="Epic sunset over digital grid landscape",
                    audio_required=False,
                ),
                TimelineEntry(
                    timestamp="00:00:01",
                    description="Hero says hello to the world",
                    duration=1.2,
                    type="character",
                    dialogue="Hello world, pipeline operational!",
                    visual_prompt="Close up anime hero speaking with enthusiasm",
                    audio_required=True,
                ),
            ],
            total_duration=2.2,
        )


def test_pipeline_e2e_execution(tmp_path):
    # Setup directories
    input_script = os.path.join(tmp_path, "script.txt")
    with open(input_script, "w", encoding="utf-8") as f:
        f.write("Title: Test Adventure\nAuthor: CineAgent\n\nA cybernetic journey begins.")

    config_path = os.path.join(tmp_path, "test_config.json")
    config_data = {
        "pipeline": {"project_name": "test-adventure"},
        "audio": {"tts_backend": "kokoro"},
        "video": {
            "backend": "synthetic",
            "device": "cuda",
            "fps": 12,
            "width": 320,
            "height": 240,
        },
        "lipsync": {
            "enabled": True,
            "endpoint": "http://127.0.0.1:9999",
        },
        "storage": {
            "processed": os.path.join(tmp_path, "processed"),
            "output": os.path.join(tmp_path, "output"),
            "timeline": os.path.join(tmp_path, "processed", "timeline.json"),
            "sync_enabled": False,
        },
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f)

    pipeline = AnimationPipeline(
        config_path=config_path,
        timeline_generator=DummyTimelineGenerator(),
        audio_generator=AudioGenerator(backend="kokoro"),
        video_generator=VideoGenerator(backend="synthetic", device="cuda", fps=12, width=320, height=240),
        lipsync_client=LipSyncClient(endpoint="http://127.0.0.1:9999", enabled=True),
    )

    results = pipeline.run_pipeline(input_script)

    assert results["project"] == "test-adventure"
    assert results["script"]["title"] == "Test Adventure"
    assert len(results["timeline"]["shots"]) == 2

    # Verify audio manifest
    audio_manifest = results["audio_manifest"]
    assert os.path.isfile(audio_manifest["manifest_path"])
    assert len(audio_manifest["shots"]) == 2

    # Verify video manifest
    video_manifest = results["video_manifest"]
    assert os.path.isfile(video_manifest["manifest_path"])
    assert os.path.isfile(video_manifest["master_video_path"])
    assert len(video_manifest["shots"]) == 2

    # Verify lipsync manifest
    lipsync_manifest = results["lipsync_manifest"]
    assert os.path.isfile(lipsync_manifest["manifest_path"])
    assert os.path.isfile(lipsync_manifest["master_video_path"])

    # Verify master animation output
    master_anim = results["master_animation_path"]
    assert os.path.isfile(master_anim)
    assert os.path.getsize(master_anim) > 1000

    # Verify asset package ZIP
    pkg_info = results["package"]
    zip_path = pkg_info["package_path"]
    assert os.path.isfile(zip_path)

    with zipfile.ZipFile(zip_path, "r") as archive:
        names = set(archive.namelist())
        assert "timeline.json" in names
        assert "manifest.json" in names
        assert "final_master_animation.mp4" in names
        assert any(n.startswith("audio/") for n in names)
        assert any(n.startswith("video/") for n in names)
