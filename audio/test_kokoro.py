import os
from kokoro_onnx import Kokoro
import soundfile as sf

def test_kokoro_tts():
    print("Testing Kokoro-onnx local voice generation...")
    # Kokoro-onnx requires a model file (kokoro-v0_19.onnx) and voices.json
    # We can check or set up a clean interface for local voice generation.
    print("Kokoro-onnx package is installed successfully.")

if __name__ == "__main__":
    test_kokoro_tts()