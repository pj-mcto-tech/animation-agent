import torch
from diffusers import DiffusionPipeline
from diffusers.utils import export_to_video

def main():
    # 1. Target your B60 Intel Arc XPU backend
    device = "xpu" if torch.xpu.is_available() else "cpu"
    print(f"Targeting compute device for Wan 2.2: {device}")

    # 2. Model repository ID for the 5B Diffusers variant
    model_id = "Wan-AI/Wan2.2-TI2V-5B-Diffusers"

    print(f"Loading Wan 2.2 model '{model_id}' onto B60...")
    
    # Load using standard DiffusionPipeline optimized for bfloat16
    pipe = DiffusionPipeline.from_pretrained(
        model_id,
        dtype=torch.bfloat16
    )
    pipe.to(device)

    # 3. Enable memory optimizations to fit comfortably within 24GB VRAM
    pipe.enable_attention_slicing()

    # 4. Define your animation prompt
    prompt = "A cinematic wide shot of a futuristic cyberpunk city at dusk, flying vehicles streaking through neon lights, highly detailed, smooth motion, 4k"
    negative_prompt = "blurry, low quality, distorted, deformed, jittery"

    print("Generating Wan 2.2 video sequence (utilizing B60 XPU)...")
    
    # Run text-to-video / video generation pass
    output = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt,
        height=480,   # Start at 480p for fast validation; scale up to 720p once verified
        width=832,
        num_frames=81,
        num_inference_steps=30,
    )
    
    video_frames = output.frames[0]

    # 5. Export output to mp4
    output_filename = "wan_output.mp4"
    export_to_video(video_frames, output_filename, fps=24)
    print(f"Success! Wan 2.2 video successfully rendered and saved to: {output_filename}")

if __name__ == "__main__":
    main()