import os
import sys
import torch
from dotenv import load_dotenv

# Allow running as a plain script from the orchestrator directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.media_utils import mux_audio_and_video  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer
from elevenlabs.client import ElevenLabs
from diffusers import WanPipeline
from diffusers.utils import export_to_video

# Load environment variables (such as ELEVENLABS_API_KEY)
load_dotenv()

def generate_script_with_qwen():
    print("--- Step 1: Generating scene script with Qwen LLM ---")
    model_name = "Qwen/Qwen2.5-3B-Instruct"
    
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16,
        device_map="auto"
    )
    
    prompt = "Write a short, vivid 1-sentence visual description of a magical cyber-elf wandering through a glowing crystal forest at night for an AI video generation prompt."
    messages = [{"role": "user", "content": prompt}]
    
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)
    
    generated_ids = model.generate(**model_inputs, max_new_tokens=100)
    generated_ids = [output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)]
    
    script_text = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
    print(f"Generated Script/Prompt: {script_text}\n")
    return script_text

def generate_voiceover(text_script):
    print("--- Step 2: Generating Voiceover via ElevenLabs API ---")
    client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
    
    audio = client.text_to_speech.convert(
        text=text_script,
        voice_id="JBFqnCBsd6RMkjVDRZzb",
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )
    
    output_audio_path = "voiceover_output.mp3"
    with open(output_audio_path, "wb") as f:
        for chunk in audio:
            f.write(chunk)
            
    print(f"Voiceover saved successfully to: {output_audio_path}\n")
    return output_audio_path

def get_audio_duration(mp3_path):
    """Calculates the duration of the MP3 file based on file size and standard 128kbps bitrate."""
    file_size_bytes = os.path.getsize(mp3_path)
    bitrate_bytes_per_sec = 128 * 1024 / 8
    duration = file_size_bytes / bitrate_bytes_per_sec
    print(f"Estimated Audio Duration: {duration:.2f} seconds")
    return max(3.0, duration)

def generate_wan_video(visual_prompt, audio_duration, fps=24):
    print(f"--- Step 3: Generating Video with Wan 2.2 on Intel Arc Pro B60 (XPU) ---")
    
    target_frames = int(audio_duration * fps)
    num_frames = max(81, ((target_frames - 1) // 4) * 4 + 1)
    print(f"Calculated target frames for Wan 2.2: {num_frames} (at {fps} FPS)")

    device = "xpu" if torch.xpu.is_available() else "cpu"
    print(f"Targeting compute device: {device}")

    model_id = "Wan-AI/Wan2.2-TI2V-5B-Diffusers"
    
    print(f"Loading Wan 2.2 model '{model_id}' onto B60...")
    pipe = WanPipeline.from_pretrained(
        model_id,
        dtype=torch.bfloat16
    )
    pipe.to(device)
    pipe.enable_attention_slicing()

    negative_prompt = "blurry, low quality, distorted, deformed, jittery"

    print("Rendering audio-synced video frames...")
    output = pipe(
        prompt=visual_prompt,
        negative_prompt=negative_prompt,
        height=480,
        width=832,
        num_frames=num_frames,
        num_inference_steps=25,
    )
    
    video_frames = output.frames[0]
    output_video_path = "wan_synced_output.mp4"
    export_to_video(video_frames, output_video_path, fps=fps)
    print(f"Synced video rendered successfully and saved to: {output_video_path}\n")
    return output_video_path


def main():
    print("=== Starting Audio-Synced Multi-Stage Animation Pipeline ===")
    
    # 1. Run Qwen script generation
    scene_prompt = generate_script_with_qwen()
    
    # 2. Run ElevenLabs audio generation & get MP3 path
    audio_path = generate_voiceover(scene_prompt)
    
    # 3. Extract duration from the generated audio file
    audio_duration = get_audio_duration(audio_path)
    
    # 4. Run Wan 2.2 video generation on the B60, matching the audio duration
    video_path = generate_wan_video(scene_prompt, audio_duration, fps=24)
    
    # 5. Mux audio and video together into the final master file
    mux_audio_and_video(video_path, audio_path)
    
    print("=== Pipeline Complete! Master animation file is ready. ===")

if __name__ == "__main__":
    main()