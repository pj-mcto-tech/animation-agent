import argparse
import torch
from diffusers import LTXPipeline
from diffusers.utils import export_to_video
    
def main(output_filename="animation_output.mp4"):
    # 1. Verify XPU availability for the B60
    device = "xpu" if torch.xpu.is_available() else "cpu"
    print(f"Targeting compute device: {device}")

    # 2. Load the LTX-Video model
    model_id = "Lightricks/LTX-Video"
    
    print(f"Loading model '{model_id}' onto Intel Arc Pro B60...")
    pipe = LTXPipeline.from_pretrained(
        model_id, 
        dtype=torch.bfloat16  # using updated 'dtype' parameter
    )
    pipe.to(device)

    # 3. Enable memory optimizations for 24GB VRAM
    pipe.enable_attention_slicing()

    # 4. Define your animation prompt
    prompt = "Camera push forward move through a vibrant neon-lit cyber city street, cinematic lighting"
    negative_prompt = "low quality, worst quality, deformed, distorted, blurry"

    print("Generating video frames on your B60 XPU...")
    
    # Corrected pipeline call (fps is handled in export_to_video, not pipe())
    video_frames = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt,
        width=1920,
        height=1024,
        num_frames=120,       # Required LTX frame block structure
        num_inference_steps=30,
    ).frames[0]

    # 5. Export output to mp4 with fps specified here
    export_to_video(video_frames, output_filename, fps=24)
    print(f"Success! Video rendered and saved to: {output_filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a video using LTX-Video model.")
    parser.add_argument("--output", type=str, default="animation_output.mp4", help="Output video filename (default: animation_output.mp4)")
    args = parser.parse_args()

    main(output_filename=args.output)