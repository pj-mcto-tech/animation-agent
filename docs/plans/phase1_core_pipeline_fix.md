# Phase 1 - Fix the core pipeline

Goal: make `src/core/pipeline.py` importable, honest, and testable; wire Stage 2 to the real
`TimelineGenerator`; unify configuration; get the test suite runnable in the project venv.

## Steps

- [x] Restore the missing file header in `src/core/pipeline.py`: imports and
      `class AnimationPipeline` with `__init__`, logging-based stage orchestration.
- [x] Stage 1 (`_process_script`): real file reading, metadata parsing (`Title:` / `Author:` /
      `Version:` header lines, filename fallback). Raises `FileNotFoundError` for bad paths.
- [x] Stage 2 (`_generate_timeline`): call `TimelineGenerator` (vLLM OpenAI-compatible endpoint,
      model name from config) and convert the validated `AnimationTimeline` into the
      `shots` + `timeline_metadata` contract used by `main.py`. Generator is injectable for tests.
- [x] Stage 3 (`_coordinate_audio`): data-driven audio manifest derived from timeline entries
      (written to `data/processed/audio_manifest.json`); real TTS generation lands in Phase 2.
- [x] Stage 4 (`_package_assets`): write `timeline.json`, build a Cartoon Animator manifest and
      a real ZIP package in `data/output/`.
- [x] Config unification: single source `src/config/default_config.json` (nested pipeline/llm/
      audio/storage sections) flattened into the pipeline contract; `LLM_ENDPOINT` / `LLM_MODEL`
      environment overrides; endpoint defaults to `http://localhost:8000/v1`.
- [x] `TimelineGenerator` accepts a `model` parameter (no more hardcoded model in the request).
- [x] `main.py` switched to `logging`; tests updated (injected fake generator, end-to-end run,
      package verification); `run_tests.py` prefers the project venv interpreter.
- [x] `pytest` installed into the project venv; `python run_tests.py` passes.
- [x] Sample fixture `data/input/sample_script.txt` added (referenced by `main.py`).

## Acceptance criteria

- `venv/bin/python -c "import src.core.pipeline"` succeeds.
- `run_tests.py` exits 0 with all tests passing.
- Running `main.py` end-to-end with a live vLLM endpoint produces
  `data/output/cartoon_animator_package.zip`; without vLLM it fails cleanly at Stage 2.

## Status

Completed 2026-11-22. Live-vLLM end-to-end confirmation deferred to Phase 4 service checks.
