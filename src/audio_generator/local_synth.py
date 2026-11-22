"""Deterministic local music/SFX synthesis (promoted from audio/test_local_audio_suite.py).

These are procedural placeholders so the pipeline can emit real, playable audio
assets before generative music models (e.g. AudioLDM on the 3060 Ti) are wired in.
"""

from __future__ import annotations

import logging
import os

import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)

SAMPLE_RATE = 44100


def _write(output_path: str, samples: np.ndarray, sample_rate: int = SAMPLE_RATE) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    sf.write(output_path, samples, sample_rate)
    logger.info(
        "Audio asset written: %s (%.2fs @ %d Hz)",
        output_path,
        len(samples) / sample_rate,
        sample_rate,
    )
    return output_path


def generate_music_track(
    prompt: str, duration: float = 10.0, output_path: str = "scene_music.wav"
) -> str:
    """Ambient synth chord bed with slow modulation (placeholder score)."""
    logger.info("Synthesizing background music for prompt: %r", prompt)
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration))
    audio = (
        0.15 * np.sin(2 * np.pi * 110 * t)
        + 0.10 * np.sin(2 * np.pi * 164.81 * t)
        + 0.10 * np.sin(2 * np.pi * 196.00 * t)
        + 0.05
        * np.sin(2 * np.pi * 220 * t * (1.0 + 0.05 * np.sin(2 * np.pi * 0.5 * t)))
    )
    audio *= np.linspace(0.0, 1.0, len(audio))
    return _write(output_path, audio)


def generate_sound_effect(
    prompt: str, duration: float = 3.0, output_path: str = "scene_sfx.wav"
) -> str:
    """Rising filtered sweep with exponential decay (placeholder SFX)."""
    logger.info("Synthesizing sound effect for prompt: %r", prompt)
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration))
    sweep_freq = np.linspace(200, 1200, len(t))
    audio = 0.3 * np.sin(2 * np.pi * sweep_freq * t) * np.exp(-t)
    return _write(output_path, audio)


def generate_silence(duration: float, output_path: str) -> str:
    """Silent placeholder used when no TTS backend is reachable."""
    samples = np.zeros(int(SAMPLE_RATE * max(0.1, duration)), dtype=np.float32)
    return _write(output_path, samples)


def pad_to_duration(audio_path: str, target_duration: float) -> float:
    """Extend an audio file with trailing silence so a shot stays on schedule.

    Returns the resulting duration. Files already at or over the target are
    left untouched (truncating speech is worse than a long shot).
    """
    samples, sample_rate = sf.read(audio_path)
    current = len(samples) / sample_rate
    if current >= target_duration:
        return current

    pad_samples = int((target_duration - current) * sample_rate)
    padded = np.concatenate([samples, np.zeros(pad_samples, dtype=samples.dtype)])
    _write(audio_path, padded, sample_rate)
    logger.info(
        "Padded %s from %.2fs to planned %.2fs to keep shot timing aligned.",
        audio_path,
        current,
        target_duration,
    )
    return len(padded) / sample_rate
