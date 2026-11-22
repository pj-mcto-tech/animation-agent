import os
import torch
from audiocraft.models import MusicGen, AudioGen
from audiocraft.data.audio import audio_write

class LocalAudioOrchestrator:
    def __init__(self, device="cpu"):
        self.device = device
        print(f"Initializing Local Audio Orchestrator on device: {self.device}")

    def generate_music(self, prompt: str, duration: int = 15, output_name: str = "scene_music"):
        print(f"--- Generating Music via MusicGen ---")
        print(f"Prompt: {prompt}")
        model = MusicGen.get_pretrained('facebook/musicgen-small')
        model.set_generation_parameters(duration=duration)
        
        wav = model.generate([prompt])
        output_path = audio_write(
            output_name,
            wav[0].cpu(),
            model.sample_rate,
            strategy="loudness",
            loudness_compress=True
        )
        print(f"Music saved to: {output_path}\n")
        return output_path

    def generate_sfx(self, prompt: str, duration: int = 5, output_name: str = "scene_sfx"):
        print(f"--- Generating Sound FX via AudioGen ---")
        print(f"Prompt: {prompt}")
        model = AudioGen.get_pretrained('facebook/audiogen-medium')
        model.set_generation_parameters(duration=duration)
        
        wav = model.generate([prompt])
        output_path = audio_write(
            output_name,
            wav[0].cpu(),
            model.sample_rate,
            strategy="loudness",
            loudness_compress=True
        )
        print(f"Sound FX saved to: {output_path}\n")
        return output_path

if __name__ == "__main__":
    orchestrator = LocalAudioOrchestrator()
    # Test generation
    orchestrator.generate_music("Cinematic synthwave background track with pulsing bass", duration=10, output_name="test_music")
    orchestrator.generate_sfx("Sci-fi door opening with pneumatic hiss", duration=4, output_name="test_sfx")
    print("Local audio test script ready.")