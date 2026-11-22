"""Local Kokoro-ONNX text-to-speech backend (runs on the RTX 3060 Ti worker)."""

from __future__ import annotations

import logging
import os
from typing import Optional

import soundfile as sf

from src.audio_generator.base import DEFAULT_VOICE, TTSBackend

logger = logging.getLogger(__name__)

REPO_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
DEFAULT_MODEL_PATH = os.path.join(REPO_ROOT, "audio", "kokoro-v1.0.onnx")
DEFAULT_VOICES_PATH = os.path.join(REPO_ROOT, "audio", "voices-v1.0.bin")


class KokoroTTSBackend(TTSBackend):
    """Lazy-loading Kokoro-ONNX backend.

    Model loading (~340 MB ONNX) is deferred to first use so pipeline import
    and unit tests stay cheap. Missing weights degrade to unavailable rather
    than raising.
    """

    name = "kokoro-onnx"

    def __init__(
        self,
        model_path: str = DEFAULT_MODEL_PATH,
        voices_path: str = DEFAULT_VOICES_PATH,
        language: str = "en-us",
    ):
        self.model_path = model_path
        self.voices_path = voices_path
        self.language = language
        self._engine = None
        self._weights_missing_logged = False

    def weights_present(self) -> bool:
        return os.path.isfile(self.model_path) and os.path.isfile(self.voices_path)

    def is_available(self) -> bool:
        if not self.weights_present():
            if not self._weights_missing_logged:
                logger.warning(
                    "Kokoro weights missing (expected %s and %s); voiceover will "
                    "fall back to silence padding.",
                    self.model_path,
                    self.voices_path,
                )
                self._weights_missing_logged = True
            return False
        return True

    def _ensure_engine(self):
        if self._engine is None:
            from kokoro_onnx import Kokoro

            logger.info("Loading Kokoro-ONNX engine from %s", self.model_path)
            self._engine = Kokoro(self.model_path, self.voices_path)
        return self._engine

    def list_voices(self) -> list:
        engine = self._ensure_engine()
        return sorted(engine.get_voices())

    def generate_voiceover(
        self,
        text: str,
        output_path: str,
        voice: str = DEFAULT_VOICE,
        speed: float = 1.0,
    ) -> str:
        if not text or not text.strip():
            raise ValueError("Voiceover text cannot be empty")
        engine = self._ensure_engine()
        samples, sample_rate = engine.create(
            text=text, voice=voice, speed=speed, lang=self.language
        )
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        sf.write(output_path, samples, sample_rate)
        logger.info(
            "Kokoro voiceover written: %s (%.2fs @ %d Hz, voice=%s)",
            output_path,
            len(samples) / sample_rate,
            sample_rate,
            voice,
        )
        return output_path
