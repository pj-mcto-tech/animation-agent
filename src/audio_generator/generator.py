"""Stage 3 audio coordination: turn a timeline into real on-disk audio assets."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import soundfile as sf

from src.audio_generator.base import DEFAULT_VOICE, TTSBackend
from src.audio_generator.elevenlabs_backend import (
    DEFAULT_ELEVENLABS_VOICE_ID,
    ElevenLabsTTSBackend,
)
from src.audio_generator.kokoro_backend import KokoroTTSBackend
from src.audio_generator.local_synth import (
    generate_music_track,
    generate_sound_effect,
    generate_silence,
    pad_to_duration,
)
from src.timeline_generator.timeline_generator import AnimationTimeline

logger = logging.getLogger(__name__)

BACKEND_REGISTRY: Dict[str, type] = {
    "kokoro": KokoroTTSBackend,
    "elevenlabs": ElevenLabsTTSBackend,
}


def measure_duration(audio_path: str) -> float:
    """Exact duration from the written file (no bitrate estimation)."""
    info = sf.info(audio_path)
    return info.duration


class AudioGenerator:
    """Selects an available TTS backend and emits per-shot audio plus beds."""

    def __init__(
        self,
        backend: str = "kokoro",
        voice: str = DEFAULT_VOICE,
        speed: float = 1.0,
        backend_override: Optional[TTSBackend] = None,
        allow_cloud_fallback: bool = False,
    ):
        if backend_override is not None:
            self.backend: Optional[TTSBackend] = backend_override
        else:
            cls = BACKEND_REGISTRY.get(backend)
            if cls is None:
                raise ValueError(
                    f"Unknown audio backend {backend!r}; choose from "
                    f"{sorted(BACKEND_REGISTRY)}"
                )
            self.backend = cls()
        self.voice = voice
        self.speed = speed
        # Cloud fallback is opt-in: it costs money and voice names are not
        # portable between local Kokoro and ElevenLabs voice IDs.
        self.allow_cloud_fallback = allow_cloud_fallback

    def resolve_backend(self) -> Optional[TTSBackend]:
        """Return the configured backend, optionally falling back to ElevenLabs.

        Local-first by design: the cloud fallback only runs when explicitly
        enabled via `allow_cloud_fallback`, so pipeline runs never make surprise
        paid API calls.
        """
        if self.backend is not None and self.backend.is_available():
            return self.backend
        if self.allow_cloud_fallback:
            fallback = ElevenLabsTTSBackend()
            if fallback.is_available():
                logger.warning(
                    "%s unavailable; falling back to cloud ElevenLabs TTS.",
                    getattr(self.backend, "name", "configured backend"),
                )
                self.backend = fallback
                # Kokoro voice names (e.g. af_heart) are not ElevenLabs voice IDs.
                if self.voice == DEFAULT_VOICE:
                    self.voice = DEFAULT_ELEVENLABS_VOICE_ID
                return fallback
        logger.warning(
            "No TTS backend available; voiceover shots will be silent padding."
        )
        return None

    def generate_for_timeline(
        self,
        timeline: AnimationTimeline,
        output_dir: str,
        music_prompt: str = "ambient underscore for animation sequence",
    ) -> Dict[str, Any]:
        """Generate voiceover per entry, plus one music bed and SFX for effects.

        Returns an audio manifest consumable by the asset packager.
        """
        os.makedirs(output_dir, exist_ok=True)
        backend = self.resolve_backend()

        shots: List[Dict[str, Any]] = []
        for index, entry in enumerate(timeline.entries, start=1):
            shot_id = f"shot_{index:03d}"
            audio_path = os.path.join(output_dir, f"{shot_id}.wav")
            audio_needed = getattr(entry, "audio_required", True)
            spoken_text = getattr(entry, "dialogue", None) or entry.description
            if backend is not None and audio_needed:
                backend.generate_voiceover(
                    text=spoken_text,
                    output_path=audio_path,
                    voice=self.voice,
                    speed=self.speed,
                )
                source = backend.name
            else:
                generate_silence(entry.duration, audio_path)
                source = "silence-padding"
            shots.append(
                {
                    "shot_id": shot_id,
                    "timestamp": entry.timestamp,
                    "type": entry.type,
                    "text": spoken_text,
                    "visual_prompt": getattr(entry, "visual_prompt", None) or entry.description,
                    "planned_duration": entry.duration,
                    "audio_path": audio_path,
                    "audio_duration": measure_duration(audio_path),
                    "source": source,
                }
            )

        music_path = generate_music_track(
            music_prompt,
            duration=max(timeline.total_duration, 2.0),
            output_path=os.path.join(output_dir, "scene_music.wav"),
        )
        sfx_paths = []
        for shot in shots:
            if shot["type"] == "effect":
                sfx_paths.append(
                    generate_sound_effect(
                        shot["text"],
                        duration=min(max(shot["planned_duration"], 1.0), 3.0),
                        output_path=os.path.join(output_dir, f"{shot['shot_id']}_sfx.wav"),
                    )
                )

        manifest = {
            "backend": backend.name if backend is not None else "silence-padding",
            "voice": self.voice,
            "shots": shots,
            "music": {
                "audio_path": music_path,
                "audio_duration": measure_duration(music_path),
            },
            "sfx": [
                {"audio_path": path, "audio_duration": measure_duration(path)}
                for path in sfx_paths
            ],
        }
        logger.info(
            "Audio stage complete: %d shot tracks, %d SFX, 1 music bed (backend=%s)",
            len(shots),
            len(sfx_paths),
            manifest["backend"],
        )
        return manifest
