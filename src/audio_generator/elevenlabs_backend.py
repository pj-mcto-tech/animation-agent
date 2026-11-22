"""Optional cloud ElevenLabs backend (fallback when local Kokoro is unavailable)."""

from __future__ import annotations

import logging
import os

from src.audio_generator.base import DEFAULT_VOICE, TTSBackend

logger = logging.getLogger(__name__)

DEFAULT_ELEVENLABS_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
DEFAULT_MODEL_ID = "eleven_multilingual_v2"
DEFAULT_OUTPUT_FORMAT = "mp3_44100_128"


class ElevenLabsTTSBackend(TTSBackend):
    """Cloud TTS backend gated on the ELEVENLABS_API_KEY environment variable.

    `voice` maps to an ElevenLabs voice_id for this backend, so the pipeline
    contract stays identical across local and cloud backends.
    """

    name = "elevenlabs"

    def __init__(
        self,
        api_key: str | None = None,
        model_id: str = DEFAULT_MODEL_ID,
        output_format: str = DEFAULT_OUTPUT_FORMAT,
    ):
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        self.model_id = model_id
        self.output_format = output_format
        self._client = None

    def is_available(self) -> bool:
        if not self.api_key:
            logger.info("ELEVENLABS_API_KEY not set; cloud TTS disabled.")
            return False
        return True

    def _ensure_client(self):
        if self._client is None:
            from elevenlabs.client import ElevenLabs

            self._client = ElevenLabs(api_key=self.api_key)
        return self._client

    def generate_voiceover(
        self,
        text: str,
        output_path: str,
        voice: str = DEFAULT_VOICE,
        speed: float = 1.0,
    ) -> str:
        if not text or not text.strip():
            raise ValueError("Voiceover text cannot be empty")
        client = self._ensure_client()
        audio = client.text_to_speech.convert(
            text=text,
            voice_id=voice,
            model_id=self.model_id,
            output_format=self.output_format,
        )
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "wb") as handle:
            for chunk in audio:
                handle.write(chunk)
        logger.info("ElevenLabs voiceover written: %s", output_path)
        return output_path
