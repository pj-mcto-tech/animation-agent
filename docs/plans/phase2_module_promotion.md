# Phase 2 - Promote prototypes into `src/` modules (PLANNED)

Goal: move the working lab prototypes into the package layout so the pipeline can call them
through stable interfaces.

## Steps

1. `src/audio_generator/`:
   - Backend interface (`generate_shot_audio(text, voice, output_path)`).
   - Kokoro-ONNX local backend (reuse `audio/tts_gateway.py` logic / `test_local_audio_suite.py`).
   - Optional ElevenLabs backend behind the same interface (`.env` key required).
   - Music/SFX placeholder generator promoted from `test_local_audio_suite.py`.
2. `src/asset_packager/`:
   - Real Cartoon Animator package: timeline JSON, storyboard frames (when available),
     per-shot audio, `manifest.json`, ZIP output to `data/output/` and the Windows-mapped
     shared storage directory.
3. Extract shared `mux_audio_and_video()` helper (currently duplicated in
   `orchestrator/combine_audio_and_video.py` and `orchestrator/test_orchestration.py`) into
   `src/core/media_utils.py` used by both paths.
4. Unit tests for each new module (no live services required).

## Acceptance criteria

- `main.py` Stage 3/4 produce real files on disk (wav + zip) with no hardcoded fake data.
- Prototype scripts under `audio/` and `orchestrator/` import the shared modules instead of
  duplicating logic.
