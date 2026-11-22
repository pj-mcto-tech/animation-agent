"""Unit tests for Stage 3 audio generation (no live TTS services required)."""

import os
import sys
import unittest

import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.audio_generator.base import TTSBackend
from src.audio_generator.generator import AudioGenerator, measure_duration
from src.audio_generator.local_synth import (
    generate_music_track,
    generate_sound_effect,
    generate_silence,
)
from src.timeline_generator.timeline_generator import AnimationTimeline, TimelineEntry


class FakeTTSBackend(TTSBackend):
    """Deterministic 1-second tone backend used to exercise the generator."""

    name = "fake-tts"

    def __init__(self, available=True, fail_on_empty=True):
        self.available = available
        self.fail_on_empty = fail_on_empty
        self.calls = []

    def is_available(self):
        return self.available

    def generate_voiceover(self, text, output_path, voice="af_heart", speed=1.0):
        if not text.strip() and self.fail_on_empty:
            raise ValueError("empty text")
        self.calls.append({"text": text, "voice": voice, "speed": speed})
        t = np.linspace(0, 1.0, 44100)
        sf.write(output_path, 0.2 * np.sin(2 * np.pi * 440 * t), 44100)
        return output_path


def _timeline():
    return AnimationTimeline(
        entries=[
            TimelineEntry(timestamp="00:00:00", description="Robot waves", duration=2.0, type="character"),
            TimelineEntry(timestamp="00:00:02", description="Sparkle burst", duration=1.5, type="effect"),
        ],
        total_duration=3.5,
    )


class TestAudioGenerator(unittest.TestCase):
    def test_backend_selection_and_asset_generation(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            fake = FakeTTSBackend()
            generator = AudioGenerator(backend_override=fake, voice="ff_sky")
            manifest = generator.generate_for_timeline(_timeline(), output_dir=tmp)

            self.assertEqual(manifest["backend"], "fake-tts")
            self.assertEqual(len(manifest["shots"]), 2)
            self.assertEqual(len(fake.calls), 2)
            self.assertEqual(fake.calls[0]["voice"], "ff_sky")
            for shot in manifest["shots"]:
                self.assertTrue(os.path.isfile(shot["audio_path"]))
                self.assertGreater(measure_duration(shot["audio_path"]), 0.9)
            self.assertTrue(os.path.isfile(manifest["music"]["audio_path"]))
            self.assertEqual(len(manifest["sfx"]), 1)

    def test_falls_back_to_silence_when_no_backend_available(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            generator = AudioGenerator(backend_override=FakeTTSBackend(available=False))
            manifest = generator.generate_for_timeline(_timeline(), output_dir=tmp)
            self.assertEqual(manifest["backend"], "silence-padding")
            for shot in manifest["shots"]:
                self.assertAlmostEqual(
                    measure_duration(shot["audio_path"]),
                    shot["planned_duration"],
                    places=2,
                )

    def test_unknown_backend_raises(self):
        with self.assertRaises(ValueError):
            AudioGenerator(backend="not-a-backend")


class TestLocalSynth(unittest.TestCase):
    def test_music_sfx_and_silence_write_valid_wavs(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            music = generate_music_track("test bed", duration=2.0, output_path=os.path.join(tmp, "m.wav"))
            sfx = generate_sound_effect("test sweep", duration=1.0, output_path=os.path.join(tmp, "s.wav"))
            silence = generate_silence(3.0, output_path=os.path.join(tmp, "z.wav"))
            self.assertAlmostEqual(measure_duration(music), 2.0, places=1)
            self.assertAlmostEqual(measure_duration(sfx), 1.0, places=1)
            self.assertAlmostEqual(measure_duration(silence), 3.0, places=1)


if __name__ == "__main__":
    unittest.main()
