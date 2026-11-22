"""Animation Agent Stage 4: Video generation and diffusion backends."""

from src.video_generator.base import VideoBackend
from src.video_generator.comfyui_backend import ComfyUIBackend
from src.video_generator.generator import VideoGenerator
from src.video_generator.ltx_backend import LTXVideoBackend
from src.video_generator.synthetic_backend import SyntheticVideoBackend
from src.video_generator.wan_backend import WanVideoBackend

__all__ = [
    "ComfyUIBackend",
    "LTXVideoBackend",
    "SyntheticVideoBackend",
    "VideoBackend",
    "VideoGenerator",
    "WanVideoBackend",
]
