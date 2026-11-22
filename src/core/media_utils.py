"""Shared media post-processing helpers (single source of truth for ffmpeg operations).

Used by the core pipeline video/asset stages and by the lab orchestrator scripts.
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
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

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
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


def concat_video_clips(
    clip_paths: List[str],
    output_path: str = "master_video.mp4",
    reencode: bool = False,
) -> str:
    """Concatenate multiple video clips sequentially into output_path."""
    if not clip_paths:
        raise ValueError("Cannot concatenate empty list of video clips.")

    for path in clip_paths:
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Video clip not found: {path}")

    if len(clip_paths) == 1:
        import shutil
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        shutil.copy2(clip_paths[0], output_path)
        return output_path

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        for clip in clip_paths:
            abs_clip = os.path.abspath(clip)
            f.write(f"file '{abs_clip}'\n")
        concat_list_path = f.name

    try:
        codec_args = ["-c:v", "libx264", "-pix_fmt", "yuv420p"] if reencode else ["-c", "copy"]
        cmd = [
            ffmpeg_executable(),
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_list_path,
            *codec_args,
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0 and not reencode:
            # Fallback to re-encoding if stream copy fails
            logger.info("Stream copy concat failed, retrying with re-encode...")
            cmd_reencode = [
                ffmpeg_executable(),
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                concat_list_path,
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                output_path,
            ]
            result = subprocess.run(cmd_reencode, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error("ffmpeg concat stderr: %s", result.stderr)
            raise RuntimeError(f"FFmpeg concat failed (exit {result.returncode}).")

        logger.info("Concatenated %d video clips into %s", len(clip_paths), output_path)
        return output_path
    finally:
        if os.path.exists(concat_list_path):
            try:
                os.remove(concat_list_path)
            except OSError:
                pass


def generate_synthetic_video(
    prompt: str,
    duration: float = 3.0,
    output_path: str = "synthetic_video.mp4",
    fps: int = 24,
    width: int = 832,
    height: int = 480,
) -> str:
    """Generate a lightweight valid MP4 clip using ffmpeg testsrc (useful for tests/fallbacks)."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    duration = max(duration, 0.5)

    # Use ffmpeg lavfi testsrc
    cmd = [
        ffmpeg_executable(),
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"testsrc=duration={duration:.2f}:size={width}x{height}:rate={fps}",
        "-pix_fmt",
        "yuv420p",
        "-c:v",
        "libx264",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("ffmpeg synthetic generation failed: %s", result.stderr)
        raise RuntimeError(f"Failed to generate synthetic video: {result.stderr}")

    return output_path
