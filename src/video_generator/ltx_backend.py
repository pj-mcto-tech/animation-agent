"""LTX-Video Diffusers backend targeting NVIDIA RTX CUDA acceleration."""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from src.video_generator.base import VideoBackend

logger = logging.getLogger(__name__)

DEFAULT_LTX_MODEL = "Lightricks/LTX-Video"
DEFAULT_NEGATIVE_PROMPT = "low quality, worst quality, deformed, distorted, blurry, watermark"


class LTXVideoBackend(VideoBackend):
    """LTX-Video generation using HuggingFace Diffusers.

    Optimized for NVIDIA RTX cards with attention slicing and dynamic frame calculation.
    LTX requires frame counts that conform to (8k + 1).
    """

    name = "ltx"

    def __init__(
        self,
        model_id: str = DEFAULT_LTX_MODEL,
        device: str = "cuda",
        torch_dtype: Optional[str] = None,
        num_inference_steps: int = 30,
    ):
        self.model_id = model_id
        self.device = device
        self._custom_dtype = torch_dtype
        self.num_inference_steps = num_inference_steps
        self._pipe = None

    def is_available(self) -> bool:
        """Check if torch and diffusers LTXPipeline are importable and device ready."""
        try:
            import torch
            from diffusers import LTXPipeline  # noqa: F401

            if self.device == "cuda":
                return torch.cuda.is_available()
            if self.device == "xpu":
                return hasattr(torch, "xpu") and torch.xpu.is_available()
            return True
        except ImportError:
            return False

    def _resolve_dtype(self, torch_mod):
        if self._custom_dtype:
            return getattr(torch_mod, self._custom_dtype)
        if self.device in ("cuda", "xpu"):
            return torch_mod.bfloat16
        return torch_mod.float32

    def _ensure_pipeline(self):
        if self._pipe is None:
            import torch
            from diffusers import LTXPipeline

            target_device = self.device
            if target_device == "cuda" and not torch.cuda.is_available():
                logger.warning("CUDA requested for LTX-Video but not available; using CPU.")
                target_device = "cpu"

            dtype = self._resolve_dtype(torch)
            logger.info(
                "Loading LTX-Video model '%s' onto device '%s' (dtype=%s)...",
                self.model_id,
                target_device,
                dtype,
            )
            pipe = LTXPipeline.from_pretrained(self.model_id, torch_dtype=dtype)

            if hasattr(pipe, "enable_attention_slicing"):
                pipe.enable_attention_slicing()
            if hasattr(pipe, "enable_model_cpu_offload") and target_device == "cuda":
                try:
                    pipe.enable_model_cpu_offload()
                    logger.info("Enabled model CPU offload for LTX-Video.")
                except Exception as exc:
                    logger.warning("Could not enable CPU offload: %s", exc)
                    pipe.to(target_device)
            else:
                pipe.to(target_device)

            self._pipe = pipe
        return self._pipe

    def generate_video(
        self,
        prompt: str,
        duration: float,
        output_path: str,
        fps: int = 24,
        width: int = 768,
        height: int = 448,
        negative_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Run LTX-Video generation pass and export to MP4."""
        from diffusers.utils import export_to_video

        pipe = self._ensure_pipeline()
        raw_frames = int(duration * fps)
        # LTX requires 8k + 1 frames
        num_frames = max(25, (raw_frames // 8) * 8 + 1)
        steps = kwargs.get("num_inference_steps", self.num_inference_steps)
        neg_prompt = negative_prompt or DEFAULT_NEGATIVE_PROMPT

        logger.info(
            "Generating LTX-Video (%df, %dx%d, %d steps) for prompt: %r",
            num_frames,
            width,
            height,
            steps,
            prompt[:60],
        )

        output = pipe(
            prompt=prompt,
            negative_prompt=neg_prompt,
            width=width,
            height=height,
            num_frames=num_frames,
            num_inference_steps=steps,
        )

        video_frames = output.frames[0]
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        export_to_video(video_frames, output_path, fps=fps)
        logger.info("LTX-Video successfully exported to %s", output_path)
        return output_path
