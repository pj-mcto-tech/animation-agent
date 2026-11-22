import os
import subprocess
import imageio_ffmpeg

def mux_audio_and_video(video_path, audio_path, output_filename="final_master_animation.mp4"):
    print(f"--- Muxing Audio ({audio_path}) and Video ({video_path}) ---")
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    
    cmd = [
        ffmpeg_exe, "-y",
        "-i", video_path,
        "-i", audio_path,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        output_filename
    ]
    
    print("Running command:", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("FFmpeg STDOUT:", result.stdout)
        print("FFmpeg STDERR:", result.stderr)
        raise RuntimeError("FFmpeg muxing failed.")
    print(f"Success! Master animation file created: {output_filename}")

if __name__ == "__main__":
    import sys
    video_arg = sys.argv[1] if len(sys.argv) > 1 else "wan_i2v_synced_output.mp4"
    audio_arg = sys.argv[2] if len(sys.argv) > 2 else "voiceover_output.mp3"
    output_arg = sys.argv[3] if len(sys.argv) > 3 else "final_master_animation.mp4"
    
    mux_audio_and_video(video_arg, audio_arg, output_arg)