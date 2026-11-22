"""Abstract base interface for Animation Agent video backends."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class VideoBackend(ABC):
    """Common interface every video generation backend must implement.

    Implementations must be lazy (no large weights loaded during __init__)
    and check availability cleanly.
    """

    name: str = "base"
    device: str = "cuda"

    @abstractmethod
    def is_available(self) -> bool:
        """Return True when this backend is ready and its compute device is available."""

    @abstractmethod
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
        """Generate a video clip of specified duration for prompt into output_path."""
