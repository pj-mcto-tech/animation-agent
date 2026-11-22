# Phase 3 - Wire media engines into the pipeline (PLANNED)

Goal: the pipeline gains real visual/video/lip-sync stages routed to the correct hardware
(Intel Arc Pro B60 via vLLM/diffusers-XPU for LLM + LLM-video; RTX 3060 Ti for image/audio/vision).

## Steps

1. New `src/video_generator/` module with pluggable backends:
   - `wan22` backend: Wan 2.2 TI2V-5B Diffusers on XPU (bf16, attention slicing), adapted from
     `video_generation/wan/wan_test.py` and `orchestrator/test_orchestration.py`.
   - `ltx` backend: LTX-Video, adapted from `video_generation/ltx/ltx_test.py`.
   - `comfyui` backend: still-frame generation through `comfy_api/comfy_util.py` workflows
     (SDXL on the 3060 Ti node).
2. Hardware router flag in config (`video.backend`, `device: auto|xpu|cuda|cpu`) so stages can be
   dispatched per worker node; keep each backend in its own extra requirements group.
3. Optional lip-sync stage: HTTP client for the `lip-sync/lipsync_worker.py` FastAPI service
   (`/v1/lipsync`, LatentSync stage2 256x256 profile) for dialogue shots with generated voiceover.
4. Extend `AnimationTimeline` / `TimelineEntry` so entries carry `visual_prompt`, `dialogue`,
   and `audio_required`, letting downstream stages consume them directly.
5. Mux final VO + lip-synced video into `final_master_animation.mp4` via the shared
   `media_utils.mux_audio_and_video()` helper.

## Acceptance criteria

- Pipeline run on a sample script yields: timeline JSON, per-shot voiceover wavs, one
  duration-matched video clip, and a muxed master MP4 inside the output package.
- No stage hard-crashes when an optional service (lipsync/ComfyUI) is down; it degrades with a
  logged warning.
