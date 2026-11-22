# Animation Agent - Execution Plan Index

Derived from the repository audit on 2026-11-22. Individual phase files live alongside this index.

| Phase | File | Scope | Status |
|---|---|---|---|
| 0 | `phase0_repo_triage.md` | .gitignore, junk removal, checkpoint commit of working prototypes | COMPLETE |
| 1 | `phase1_core_pipeline_fix.md` | Repair `src/core/pipeline.py`, wire real LLM timeline generation, config unification, tests green | COMPLETE |
| 2 | `phase2_module_promotion.md` | Promote TTS/audio prototypes into `src/audio_generator` + `src/asset_packager` | PLANNED |
| 3 | `phase3_media_engine_integration.md` | Wire Wan 2.2 / LTX / ComfyUI / lip-sync services into the pipeline as stages | PLANNED |
| 4 | `phase4_operationalization.md` | Requirements split, `.env.example`, README quick-start, service-ready CI tests | PLANNED |

## Key audit findings driving this plan

1. `src/core/pipeline.py` was missing its file header (imports + `class AnimationPipeline`), so the
   core package raised `IndentationError` on import, even at the last commit.
2. Every pipeline stage was a hardcoded stub; the working `TimelineGenerator` was never called.
3. Real, working prototypes exist OUTSIDE `src/`: Kokoro TTS gateway, ElevenLabs client,
   LatentSync/MuseTalk lipsync worker, Wan 2.2 (XPU/B60) and LTX-Video tests, ffmpeg muxing,
   ComfyUI headless client.
4. No `.gitignore`: 14 GB `venv/` and 28 GB `lip-sync/` (incl. third-party clones and model
   weights) sat unprotected inside the repo; junk files (`=2.0.2`, `=12.0.0`) from broken pip
   commands were present.
5. `requirements.txt` was stale and the project venv lacked `pytest`, so `run_tests.py` could not run.
