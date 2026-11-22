import os
import sys

# Allow running as a plain script from the orchestrator directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.media_utils import mux_audio_and_video  # noqa: E402

if __name__ == "__main__":
    video_arg = sys.argv[1] if len(sys.argv) > 1 else "wan_i2v_synced_output.mp4"
    audio_arg = sys.argv[2] if len(sys.argv) > 2 else "voiceover_output.mp3"
    output_arg = sys.argv[3] if len(sys.argv) > 3 else "final_master_animation.mp4"

    mux_audio_and_video(video_arg, audio_arg, output_arg)
