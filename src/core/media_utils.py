"""Shared media post-processing helpers (single source of truth for ffmpeg muxing).

Used by the core pipeline asset stage and by the lab orchestrator scripts, which
previously duplicated this logic.
"""

from __future__ import annotations

import logging
import os
import subprocess
from typing import List, Optional

import imageio_ffmpeg

logger = logging.getLogger(__name__)


def ffmpeg_executable() -> str:
    """Path to the ffmpeg binary bundled with imageio-ffmpeg."""
    return imageio_ffmpeg.get_ffmpeg_exe()


def mux_audio_and_video(
    video_path: str,
    audio_path: str,
    output_path: str = "final_master_animation.mp4",
    video_codec: str = "copy",
    audio_bitrate: str = "192k",
    extra_args: Optional[List[str]] = None,
) -> str:
    """Combine one video track and one audio track into `output_path`."""
    for label, path in (("video", video_path), ("audio", audio_path)):
        if not os.path.isfile(path):
            raise FileNotFoundError(f"{label} input not found: {path}")

    cmd = [
        ffmpeg_executable(),
        "-y",
        "-i",
        video_path,
        "-i",
        audio_path,
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        video_codec,
        "-c:a",
        "aac",
        "-b:a",
        audio_bitrate,
        "-shortest",
    ]
    cmd.extend(extra_args or [])
    cmd.append(output_path)

    logger.info("Muxing %s + %s -> %s", video_path, audio_path, output_path)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("ffmpeg stdout: %s", result.stdout)
        logger.error("ffmpeg stderr: %s", result.stderr)
        raise RuntimeError(f"FFmpeg muxing failed (exit {result.returncode}).")

    logger.info("Master animation written: %s", output_path)
    return output_path
