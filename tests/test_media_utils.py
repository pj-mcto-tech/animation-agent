"""Unit tests for the shared ffmpeg mux helper in src.core.media_utils."""

import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.core.media_utils import ffmpeg_executable, mux_audio_and_video


def _make_test_inputs(tmp):
    """Generate a tiny silent video and a sine-wave audio track with ffmpeg itself."""
    ffmpeg = ffmpeg_executable()
    video_path = os.path.join(tmp, "clip.mp4")
    audio_path = os.path.join(tmp, "voice.wav")
    subprocess.run(
        [ffmpeg, "-y", "-f", "lavfi", "-i", "testsrc=duration=2:size=128x128:rate=10",
         "-pix_fmt", "yuv420p", video_path],
        check=True, capture_output=True,
    )
    subprocess.run(
        [ffmpeg, "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=3", audio_path],
        check=True, capture_output=True,
    )
    return video_path, audio_path


class TestMediaUtils(unittest.TestCase):
    def test_mux_produces_video_with_audio_stream(self):
        with tempfile.TemporaryDirectory() as tmp:
            video_path, audio_path = _make_test_inputs(tmp)
            out_path = mux_audio_and_video(video_path, audio_path, os.path.join(tmp, "master.mp4"))
            self.assertTrue(os.path.isfile(out_path))
            self.assertGreater(os.path.getsize(out_path), 0)

            probe = subprocess.run(
                [ffmpeg_executable(), "-i", out_path], capture_output=True, text=True
            )
            self.assertIn("Video:", probe.stderr)
            self.assertIn("Audio:", probe.stderr)

    def test_missing_input_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                mux_audio_and_video(os.path.join(tmp, "nope.mp4"), os.path.join(tmp, "nope.wav"))


if __name__ == "__main__":
    unittest.main()
