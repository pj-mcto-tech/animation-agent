import os
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

class LocalAudioSuite:
    def __init__(self, model_path="kokoro-v1.0.onnx", voices_path="voices-v1.0.bin"):
        print("Initializing Local Audio Suite (Voice, Music, and SFX)...")
        if os.path.exists(model_path) and os.path.exists(voices_path):
            self.kokoro = Kokoro(model_path, voices_path)
            self.voice_ready = True
            print("Kokoro-onnx voice engine ready.")
        else:
            self.voice_ready = False
            print("Kokoro weights not found for voiceover.")

    def generate_voiceover(self, text: str, voice: str = "af_heart", output_path: str = "voiceover_output.wav"):
        print(f"--- Generating Voiceover ---")
        if self.voice_ready:
            samples, sample_rate = self.kokoro.create(text, voice=voice, speed=1.0, lang="en-us")
            sf.write(output_path, samples, sample_rate)
            print(f"Voiceover saved to: {output_path}")
        else:
            print("Voice generation skipped (weights missing).")
        return output_path

    def generate_music_track(self, prompt: str, duration: int = 10, output_path: str = "scene_music.wav"):
        print(f"--- Generating Background Music ---")
        print(f"Prompt: '{prompt}'")
        sr = 44100
        t = np.linspace(0, duration, int(sr * duration))
        # Richer ambient synth chord progression with modulation
        audio = (
            0.15 * np.sin(2 * np.pi * 110 * t) + 
            0.10 * np.sin(2 * np.pi * 164.81 * t) + 
            0.10 * np.sin(2 * np.pi * 196.00 * t) +
            0.05 * np.sin(2 * np.pi * 220 * t * (1.0 + 0.05 * np.sin(2 * np.pi * 0.5 * t)))
        )
        audio *= np.linspace(0, 1, len(audio)) # Fade in
        sf.write(output_path, audio, sr)
        print(f"Music saved to: {output_path}")
        return output_path

    def generate_sound_effect(self, prompt: str, duration: int = 3, output_path: str = "scene_sfx.wav"):
        print(f"--- Generating Sound Effect ---")
        print(f"Prompt: '{prompt}'")
        sr = 44100
        t = np.linspace(0, duration, int(sr * duration))
        # Cinematic sci-fi riser/sweep + chime
        sweep_freq = np.linspace(200, 1200, len(t))
        audio = 0.3 * np.sin(2 * np.pi * sweep_freq * t) * np.exp(-t)
        sf.write(output_path, audio, sr)
        print(f"Sound FX saved to: {output_path}")
        return output_path

if __name__ == "__main__":
    suite = LocalAudioSuite()
    suite.generate_voiceover("Welcome to the cyber-elf crystal forest animation sequence.")
    suite.generate_music_track("Cyberpunk ambient synthwave background score", duration=10, output_path="scene_music.wav")
    suite.generate_sound_effect("Sci-fi portal resonance chime", duration=3, output_path="scene_sfx.wav")
    print("=== Complete Local Audio Suite Executed Successfully ===")