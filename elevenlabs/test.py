import os
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

# Load environment variables from .env file
load_dotenv()

# Initialize the ElevenLabs client using your API key
client = ElevenLabs(
    api_key=os.getenv("ELEVENLABS_API_KEY")
)

def generate_test_voice():
    print("Generating speech via ElevenLabs API...")
    
    # Request text-to-speech conversion using a standard voice model
    audio = client.text_to_speech.convert(
        text="System online. Local audio generation pipeline initialized successfully.",
        voice_id="JBFqnCBsd6RMkjVDRZzb",  # Standard default voice ID (or pick your preferred voice)
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )
    
    # Save the output to your local directory
    output_path = "test_output.mp3"
    with open(output_path, "wb") as f:
        for chunk in audio:
            f.write(chunk)
            
    print(f"Audio successfully generated and saved to: {output_path}")

if __name__ == "__main__":
    generate_test_voice()