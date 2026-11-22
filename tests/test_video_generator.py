"""Unit tests for Stage 4 video generator and diffusion backends."""

import os
import pytest

from src.timeline_generator.timeline_generator import AnimationTimeline, TimelineEntry
from src.video_generator.comfyui_backend import ComfyUIBackend
from src.video_generator.generator import VideoGenerator
from src.video_generator.ltx_backend import LTXVideoBackend
from src.video_generator.synthetic_backend import SyntheticVideoBackend
from src.video_generator.wan_backend import WanVideoBackend


def test_synthetic_video_backend(tmp_path):
    backend = SyntheticVideoBackend()
    assert backend.is_available() is True
    assert backend.name == "synthetic"

    out = os.path.join(tmp_path, "synthetic.mp4")
    res = backend.generate_video(
        prompt="A robotic cat walking",
        duration=1.0,
        output_path=out,
        fps=12,
        width=320,
        height=240,
    )
    assert os.path.isfile(res)
    assert os.path.getsize(res) > 500


def test_wan_backend_init():
    backend = WanVideoBackend(device="cuda")
    assert backend.name == "wan22"
    assert backend.device == "cuda"


def test_ltx_backend_init():
    backend = LTXVideoBackend(device="cuda")
    assert backend.name == "ltx"
    assert backend.device == "cuda"


def test_comfyui_backend_offline():
    # An unreachable port should report is_available == False
    backend = ComfyUIBackend(server_address="127.0.0.1:9999", timeout=0.2)
    assert backend.is_available() is False


def test_video_generator_fallback():
    # If a backend is requested that isn't ready/installed, fallback to synthetic
    generator = VideoGenerator(backend="synthetic", device="cuda")
    resolved = generator.resolve_backend()
    assert resolved.name == "synthetic"


def test_video_generator_for_timeline(tmp_path):
    entries = [
        TimelineEntry(
            timestamp="00:00:00",
            description="A futuristic skyline",
            duration=1.0,
            type="background",
            visual_prompt="Cyberpunk city with flying cars at dusk",
        ),
        TimelineEntry(
            timestamp="00:00:01",
            description="Hero turns to camera",
            duration=1.0,
            type="character",
            visual_prompt="Close up of cyborg hero with glowing blue eyes",
        ),
    ]
    timeline = AnimationTimeline(entries=entries, total_duration=2.0)

    out_dir = os.path.join(tmp_path, "video_out")
    generator = VideoGenerator(
        backend="synthetic",
        device="cuda",
        fps=12,
        width=320,
        height=240,
    )

    manifest = generator.generate_for_timeline(timeline, output_dir=out_dir)

    assert manifest["backend"] == "synthetic"
    assert manifest["total_shots"] == 2
    assert os.path.isfile(manifest["master_video_path"])
    for shot in manifest["shots"]:
        assert os.path.isfile(shot["video_path"])
        assert shot["fps"] == 12
