import os
import uuid
import yaml
import subprocess
from typing import Literal, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="SDF-1Alpha RTX 3060 Ti Lip-Sync Worker")

BASE_DIR = "/home/pj-mcnerney/ai/animation-agent/lip-sync"
LATENTSYNC_DIR = os.path.join(BASE_DIR, "LatentSync")
MUSETALK_DIR = os.path.join(BASE_DIR, "MuseTalk")

LATENTSYNC_PYTHON = os.path.join(LATENTSYNC_DIR, ".venv/bin/python")
MUSETALK_PYTHON = os.path.join(MUSETALK_DIR, ".venv/bin/python")
OUTPUT_DIR = "/mnt/nvme_scratch/animation_pipeline/lipsync_out"

os.makedirs(OUTPUT_DIR, exist_ok=True)


class LipSyncRequest(BaseModel):
    engine: Literal["latentsync", "musetalk"] = "latentsync"
    video_path: str
    audio_path: str
    output_name: Optional[str] = None
    # LatentSync options
    inference_steps: int = 20
    guidance_scale: float = 1.5
    seed: int = 1247
    # MuseTalk options
    bbox_shift: int = 0
    musetalk_version: Literal["v15", "v1"] = "v15"


def latentsync_ready() -> bool:
    return (
        os.path.exists(LATENTSYNC_PYTHON)
        and os.path.exists(os.path.join(LATENTSYNC_DIR, "checkpoints/latentsync_unet.pt"))
    )


def musetalk_ready() -> bool:
    has_weights = (
        os.path.exists(os.path.join(MUSETALK_DIR, "models/musetalkV15/unet.pth"))
        or os.path.exists(os.path.join(MUSETALK_DIR, "models/musetalk/pytorch_model.bin"))
    )
    return os.path.exists(MUSETALK_PYTHON) and has_weights


@app.get("/health")
def health():
    return {
        "status": "ok",
        "latentsync_ready": latentsync_ready(),
        "latentsync_venv": os.path.exists(LATENTSYNC_PYTHON),
        "musetalk_ready": musetalk_ready(),
        "musetalk_venv": os.path.exists(MUSETALK_PYTHON),
    }


def run_musetalk(req: LipSyncRequest, job_id: str, out_mp4: str) -> None:
    if not os.path.exists(MUSETALK_PYTHON):
        raise HTTPException(
            status_code=500,
            detail=f"MuseTalk venv missing at {MUSETALK_PYTHON}",
        )
    if not musetalk_ready():
        raise HTTPException(
            status_code=400,
            detail="MuseTalk weights not found in MuseTalk/models/. Run download_weights.sh first.",
        )

    tmp_dir = os.path.join(OUTPUT_DIR, f"tmp_mt_{job_id}")
    os.makedirs(tmp_dir, exist_ok=True)

    task_yaml = os.path.join(tmp_dir, "task.yaml")
    with open(task_yaml, "w") as f:
        yaml.safe_dump(
            {
                "task_0": {
                    "video_path": req.video_path,
                    "audio_path": req.audio_path,
                    "bbox_shift": req.bbox_shift,
                }
            },
            f,
        )

    if req.musetalk_version == "v15":
        unet_path = "models/musetalkV15/unet.pth"
        unet_cfg = "models/musetalkV15/musetalk.json"
    else:
        unet_path = "models/musetalk/pytorch_model.bin"
        unet_cfg = "models/musetalk/musetalk.json"

    cmd = [
        MUSETALK_PYTHON,
        "-m",
        "scripts.inference",
        "--inference_config",
        task_yaml,
        "--result_dir",
        tmp_dir,
        "--unet_model_path",
        unet_path,
        "--unet_config",
        unet_cfg,
        "--version",
        req.musetalk_version,
        "--use_float16",
        "--batch_size",
        "1",
    ]

    env = os.environ.copy()
    env["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:128"

    res = subprocess.run(cmd, cwd=MUSETALK_DIR, env=env, capture_output=True, text=True)
    if res.returncode != 0:
        raise HTTPException(status_code=500, detail=f"MuseTalk failed: {res.stderr[-1500:]}")

    rendered = [
        os.path.join(root, fn)
        for root, _, files in os.walk(tmp_dir)
        for fn in files
        if fn.endswith(".mp4")
    ]
    if not rendered:
        raise HTTPException(status_code=500, detail="MuseTalk completed without producing an MP4")

    os.replace(rendered[0], out_mp4)


def run_latentsync(req: LipSyncRequest, out_mp4: str) -> None:
    if not os.path.exists(LATENTSYNC_PYTHON):
        raise HTTPException(
            status_code=500,
            detail=f"LatentSync venv missing at {LATENTSYNC_PYTHON}",
        )
    if not latentsync_ready():
        raise HTTPException(
            status_code=400,
            detail="LatentSync checkpoint not found at checkpoints/latentsync_unet.pt",
        )

    # Pin to stage2.yaml (256x256, <= 8 GB VRAM safe for RTX 3060 Ti)
    unet_cfg = os.path.join(LATENTSYNC_DIR, "configs/unet/stage2.yaml")
    ckpt_path = os.path.join(LATENTSYNC_DIR, "checkpoints/latentsync_unet.pt")

    cmd = [
        LATENTSYNC_PYTHON,
        "-m",
        "scripts.inference",
        "--unet_config_path",
        unet_cfg,
        "--inference_ckpt_path",
        ckpt_path,
        "--inference_steps",
        str(req.inference_steps),
        "--guidance_scale",
        str(req.guidance_scale),
        "--video_path",
        req.video_path,
        "--audio_path",
        req.audio_path,
        "--video_out_path",
        out_mp4,
        "--seed",
        str(req.seed),
    ]

    res = subprocess.run(cmd, cwd=LATENTSYNC_DIR, capture_output=True, text=True)
    if res.returncode != 0:
        raise HTTPException(status_code=500, detail=f"LatentSync failed: {res.stderr[-1500:]}")


@app.post("/v1/lipsync")
def generate_lipsync(req: LipSyncRequest):
    if not os.path.exists(req.video_path):
        raise HTTPException(status_code=400, detail=f"video_path not found: {req.video_path}")
    if not os.path.exists(req.audio_path):
        raise HTTPException(status_code=400, detail=f"audio_path not found: {req.audio_path}")

    job_id = req.output_name or f"{req.engine}_{uuid.uuid4().hex[:8]}"
    out_mp4 = os.path.join(OUTPUT_DIR, f"{job_id}.mp4")

    if req.engine == "musetalk":
        run_musetalk(req, job_id, out_mp4)
    else:
        run_latentsync(req, out_mp4)

    return {
        "status": "completed",
        "engine": req.engine,
        "output_path": out_mp4,
        "download_url": f"/v1/lipsync/download/{os.path.basename(out_mp4)}",
    }


@app.get("/v1/lipsync/download/{filename}")
def download_render(filename: str):
    path = os.path.join(OUTPUT_DIR, os.path.basename(filename))
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Rendered file not found")
    return FileResponse(path, media_type="video/mp4", filename=os.path.basename(path))
