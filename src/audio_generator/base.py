"""Shared interfaces for the Animation Agent audio generation stage."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

DEFAULT_VOICE = "af_heart"


class TTSBackend(ABC):
    """Common interface every text-to-speech backend must implement.

    Implementations must be cheap to construct (no model loading in __init__)
    and expose availability so the pipeline can degrade gracefully.
    """

    name: str = "base"

    @abstractmethod
    def is_available(self) -> bool:
        """Return True when this backend can actually synthesize audio here."""

    @abstractmethod
    def generate_voiceover(
        self,
        text: str,
        output_path: str,
        voice: str = DEFAULT_VOICE,
        speed: float = 1.0,
    ) -> str:
        """Synthesize `text` and write an audio file to `output_path`.

        Returns the written output path.
        """
