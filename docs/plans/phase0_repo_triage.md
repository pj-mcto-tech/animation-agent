# Phase 0 - Repo Triage (protect what exists)

Goal: stop the repository from accidentally absorbing 40+ GB of venvs, model weights, and media
artifacts; commit the proven prototypes so they are recoverable.

## Steps

- [x] Add a root `.gitignore` covering: virtualenvs, caches, model weights/checkpoints,
      third-party lip-sync clones (`LatentSync`, `MuseTalk`, `SadTalker`), generated media
      (`*.mp4`, `*.wav`, `*.mp3`, `*.onnx`, `*.bin`), data output dirs, and `.env`.
- [x] Delete junk artifacts created by unquoted pip commands:
      `lip-sync/LatentSync/=2.0.2` and `orchestrator/=12.0.0`.
- [x] Remove stray `__pycache__` directories.
- [x] Checkpoint commit of the working prototype code (audio gateway, lipsync worker,
      orchestrator scripts, video-generation tests, ComfyUI client + workflow, docs).
- [x] Push checkpoint to `origin/master`.

## Acceptance criteria

- `git status` is clean except intentionally ignored paths.
- No binary/media/venv path can be staged by a plain `git add .`.
- All prototype source files tracked and pushed.

## Status

Completed 2026-11-22. See commits in `git log` labeled `chore(repo)` / `feat(prototypes)`.
