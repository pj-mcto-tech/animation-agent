"""Wan 2.2 TI2V-5B Diffusers video backend targeting NVIDIA RTX CUDA acceleration."""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from src.video_generator.base import VideoBackend

logger = logging.getLogger(__name__)

DEFAULT_WAN_MODEL = "Wan-AI/Wan2.2-TI2V-5B-Diffusers"
DEFAULT_NEGATIVE_PROMPT = "blurry, low quality, distorted, deformed, jittery, watermark"


class WanVideoBackend(VideoBackend):
    """Wan 2.2 Text/Image-to-Video generation using HuggingFace Diffusers.

    Tailored for NVIDIA RTX GPUs (e.g. RTX 3060 Ti 8GB) using float16/bfloat16,
    attention slicing, and optimized frame counts.
    """

    name = "wan22"

    def __init__(
        self,
        model_id: str = DEFAULT_WAN_MODEL,
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
        """Check if torch and diffusers are available and device is supported."""
        try:
            import torch
            import diffusers  # noqa: F401

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
        if self.device == "cuda":
            # RTX 3060 Ti Ampere architecture supports both float16 and bfloat16
            return torch_mod.float16
        if self.device == "xpu":
            return torch_mod.bfloat16
        return torch_mod.float32

    def _ensure_pipeline(self):
        if self._pipe is None:
            import torch
            from diffusers import DiffusionPipeline

            target_device = self.device
            if target_device == "cuda" and not torch.cuda.is_available():
                logger.warning("CUDA requested for Wan 2.2 but not available; using CPU.")
                target_device = "cpu"

            dtype = self._resolve_dtype(torch)
            logger.info(
                "Loading Wan 2.2 model '%s' onto device '%s' (dtype=%s)...",
                self.model_id,
                target_device,
                dtype,
            )
            pipe = DiffusionPipeline.from_pretrained(self.model_id, torch_dtype=dtype)

            # Apply memory optimizations for 8GB VRAM cards (RTX 3060 Ti)
            if hasattr(pipe, "enable_attention_slicing"):
                pipe.enable_attention_slicing()
            if hasattr(pipe, "enable_model_cpu_offload") and target_device == "cuda":
                try:
                    pipe.enable_model_cpu_offload()
                    logger.info("Enabled model CPU offload for Wan 2.2 to fit in 8GB VRAM.")
                except Exception as exc:
                    logger.warning("Could not enable model CPU offload: %s", exc)
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
        width: int = 832,
        height: int = 480,
        negative_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Run Wan 2.2 video generation pass and export to MP4."""
        from diffusers.utils import export_to_video

        pipe = self._ensure_pipeline()
        num_frames = max(17, int(duration * fps))
        # Keep frame count reasonable for fast generation
        steps = kwargs.get("num_inference_steps", self.num_inference_steps)
        neg_prompt = negative_prompt or DEFAULT_NEGATIVE_PROMPT

        logger.info(
            "Generating Wan 2.2 video (%df, %dx%d, %d steps) for prompt: %r",
            num_frames,
            width,
            height,
            steps,
            prompt[:60],
        )

        output = pipe(
            prompt=prompt,
            negative_prompt=neg_prompt,
            height=height,
            width=width,
            num_frames=num_frames,
            num_inference_steps=steps,
        )

        video_frames = output.frames[0]
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        export_to_video(video_frames, output_path, fps=fps)
        logger.info("Wan 2.2 video successfully exported to %s", output_path)
        return output_path
