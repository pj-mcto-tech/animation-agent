"""Stage 4 video coordination: turn animation timeline into real video clips."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from src.core.media_utils import concat_video_clips
from src.timeline_generator.timeline_generator import AnimationTimeline
from src.video_generator.base import VideoBackend
from src.video_generator.comfyui_backend import ComfyUIBackend
from src.video_generator.ltx_backend import LTXVideoBackend
from src.video_generator.synthetic_backend import SyntheticVideoBackend
from src.video_generator.wan_backend import WanVideoBackend

logger = logging.getLogger(__name__)

BACKEND_REGISTRY: Dict[str, type] = {
    "wan": WanVideoBackend,
    "wan22": WanVideoBackend,
    "ltx": LTXVideoBackend,
    "comfyui": ComfyUIBackend,
    "synthetic": SyntheticVideoBackend,
}


class VideoGenerator:
    """Coordinates video generation across timeline shots and builds master video."""

    def __init__(
        self,
        backend: str = "synthetic",
        device: str = "cuda",
        backend_override: Optional[VideoBackend] = None,
        allow_synthetic_fallback: bool = True,
        fps: int = 24,
        width: int = 832,
        height: int = 480,
    ):
        if backend_override is not None:
            self.backend: Optional[VideoBackend] = backend_override
        else:
            cls = BACKEND_REGISTRY.get(backend.lower())
            if cls is None:
                raise ValueError(
                    f"Unknown video backend {backend!r}; choose from {sorted(BACKEND_REGISTRY)}"
                )
            if backend.lower() in ("wan", "wan22", "ltx"):
                self.backend = cls(device=device)
            else:
                self.backend = cls()

        self.device = device
        self.allow_synthetic_fallback = allow_synthetic_fallback
        self.fps = fps
        self.width = width
        self.height = height

    def resolve_backend(self) -> VideoBackend:
        """Return configured backend if available, or fall back to synthetic."""
        if self.backend is not None and self.backend.is_available():
            return self.backend

        if self.allow_synthetic_fallback:
            logger.warning(
                "Requested video backend '%s' is unavailable on device '%s'. "
                "Falling back to synthetic video generator.",
                getattr(self.backend, "name", "unknown"),
                self.device,
            )
            fallback = SyntheticVideoBackend()
            self.backend = fallback
            return fallback

        raise RuntimeError(
            f"Video backend {getattr(self.backend, 'name', 'unknown')} is not available."
        )

    def generate_for_timeline(
        self,
        timeline: AnimationTimeline,
        output_dir: str,
        fps: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate video clip for each shot in timeline and concatenate into master_video.mp4."""
        os.makedirs(output_dir, exist_ok=True)
        backend = self.resolve_backend()
        target_fps = fps or self.fps
        target_width = width or self.width
        target_height = height or self.height

        shot_records: List[Dict[str, Any]] = []
        clip_paths: List[str] = []

        for index, entry in enumerate(timeline.entries, start=1):
            shot_id = f"shot_{index:03d}"
            clip_path = os.path.join(output_dir, f"{shot_id}.mp4")
            prompt = (
                getattr(entry, "visual_prompt", None)
                or entry.description
            )
            duration = max(entry.duration, 0.5)

            logger.info("Generating video for %s (%.2fs): %r", shot_id, duration, prompt[:50])
            backend.generate_video(
                prompt=prompt,
                duration=duration,
                output_path=clip_path,
                fps=target_fps,
                width=target_width,
                height=target_height,
            )

            shot_records.append(
                {
                    "shot_id": shot_id,
                    "timestamp": entry.timestamp,
                    "type": entry.type,
                    "duration": duration,
                    "visual_prompt": prompt,
                    "video_path": clip_path,
                    "fps": target_fps,
                }
            )
            clip_paths.append(clip_path)

        master_video_path = os.path.join(output_dir, "master_video.mp4")
        concat_video_clips(clip_paths, master_video_path)

        manifest = {
            "backend": backend.name,
            "device": getattr(backend, "device", self.device),
            "total_shots": len(shot_records),
            "master_video_path": master_video_path,
            "shots": shot_records,
        }
        logger.info(
            "Video generation complete: %d clips assembled into %s",
            len(shot_records),
            master_video_path,
        )
        return manifest
