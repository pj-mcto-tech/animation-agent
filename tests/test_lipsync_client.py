"""Unit tests for Stage 5 lip-sync client and fallback behaviors."""

import os
import shutil

from src.core.media_utils import generate_synthetic_video
from src.lipsync.client import LipSyncClient


def test_lipsync_client_offline():
    client = LipSyncClient(endpoint="http://127.0.0.1:9999", enabled=True)
    assert client.is_available() is False


def test_lipsync_client_sync_shot_fallback(tmp_path):
    client = LipSyncClient(endpoint="http://127.0.0.1:9999", enabled=True)

    dummy_video = os.path.join(tmp_path, "orig_video.mp4")
    generate_synthetic_video("Shot", duration=0.8, output_path=dummy_video, fps=12, width=320, height=240)

    dummy_audio = os.path.join(tmp_path, "orig_audio.wav")
    with open(dummy_audio, "wb") as f:
        f.write(b"RIFF....WAVEfmt ....data....")

    synced_out = os.path.join(tmp_path, "synced_video.mp4")
    res = client.sync_shot(dummy_video, dummy_audio, synced_out)

    assert os.path.isfile(res)
    assert os.path.getsize(res) == os.path.getsize(dummy_video)


def test_lipsync_process_timeline(tmp_path):
    client = LipSyncClient(endpoint="http://127.0.0.1:9999", enabled=True)

    v1 = os.path.join(tmp_path, "shot_001.mp4")
    v2 = os.path.join(tmp_path, "shot_002.mp4")
    generate_synthetic_video("Shot 1", duration=0.8, output_path=v1, fps=12, width=320, height=240)
    generate_synthetic_video("Shot 2", duration=0.8, output_path=v2, fps=12, width=320, height=240)

    a1 = os.path.join(tmp_path, "shot_001.wav")
    with open(a1, "wb") as f:
        f.write(b"WAVEDATA")

    video_manifest = {
        "shots": [
            {"shot_id": "shot_001", "type": "character", "video_path": v1},
            {"shot_id": "shot_002", "type": "background", "video_path": v2},
        ]
    }
    audio_manifest = {
        "shots": [
            {"shot_id": "shot_001", "audio_path": a1},
            {"shot_id": "shot_002", "audio_path": ""},
        ]
    }

    out_dir = os.path.join(tmp_path, "lipsync_out")
    result = client.process_timeline(video_manifest, audio_manifest, output_dir=out_dir)

    assert os.path.isfile(result["master_video_path"])
    assert len(result["shots"]) == 2
    assert os.path.isfile(result["shots"][0]["synced_video_path"])
    assert os.path.isfile(result["shots"][1]["synced_video_path"])
