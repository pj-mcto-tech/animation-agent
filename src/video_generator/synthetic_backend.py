"""Synthetic test video backend (zero-GPU fallback for offline development & tests)."""

from __future__ import annotations

import logging
from typing import Any, Optional

from src.core.media_utils import generate_synthetic_video
from src.video_generator.base import VideoBackend

logger = logging.getLogger(__name__)


class SyntheticVideoBackend(VideoBackend):
    """Generates valid, lightweight MP4 video clips using ffmpeg filters."""

    name = "synthetic"
    device = "cpu"

    def is_available(self) -> bool:
        return True

    def generate_video(
        self,
        prompt: str,
        duration: float,
        output_path: str,
        fps: int = 24,
        width: int = 832,
        height: int = 480,
        negative_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        logger.info(
            "Generating synthetic video clip: duration=%.2fs, size=%dx%d, prompt=%r",
            duration,
            width,
            height,
            prompt[:40] if prompt else "",
        )
        return generate_synthetic_video(
            prompt=prompt,
            duration=duration,
            output_path=output_path,
            fps=fps,
            width=width,
            height=height,
        )
