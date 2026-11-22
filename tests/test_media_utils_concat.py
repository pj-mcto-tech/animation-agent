"""Unit tests for video concatenation and synthetic generation in media_utils."""

import os
from src.core.media_utils import concat_video_clips, generate_synthetic_video


def test_generate_synthetic_video(tmp_path):
    output = os.path.join(tmp_path, "test_synth.mp4")
    res = generate_synthetic_video(
        prompt="Test prompt",
        duration=1.0,
        output_path=output,
        fps=12,
        width=320,
        height=240,
    )
    assert os.path.isfile(res)
    assert os.path.getsize(res) > 500


def test_concat_video_clips(tmp_path):
    clip1 = os.path.join(tmp_path, "c1.mp4")
    clip2 = os.path.join(tmp_path, "c2.mp4")
    generate_synthetic_video("Clip 1", duration=0.8, output_path=clip1, fps=12, width=320, height=240)
    generate_synthetic_video("Clip 2", duration=0.8, output_path=clip2, fps=12, width=320, height=240)

    master = os.path.join(tmp_path, "master.mp4")
    res = concat_video_clips([clip1, clip2], output_path=master)
    assert os.path.isfile(res)
    assert os.path.getsize(res) > 1000
