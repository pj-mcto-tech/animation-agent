"""Animation Agent Stage 3: text-to-speech backends and local audio synthesis."""

from src.audio_generator.base import TTSBackend
from src.audio_generator.generator import AudioGenerator, measure_duration

__all__ = ["AudioGenerator", "TTSBackend", "measure_duration"]
