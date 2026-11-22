# Phase 4 - Operationalize (PLANNED)

Goal: make the pipeline reproducible on a fresh machine and safe to run as a set of services.

## Steps

1. Requirements split:
   - `requirements.txt` (core: openai, pydantic, pyyaml, python-dotenv, pytest, coverage,
     black, flake8, isort)
   - `requirements-tts.txt` (fastapi, uvicorn, kokoro-onnx, soundfile)
   - `requirements-video.txt` (diffusers, accelerate, imageio-ffmpeg, torch, websocket-client)
   - `requirements-lipsync.txt` (pointers to per-clone `.venv` setups instead of the main env)
2. `.env.example`: `ELEVENLABS_API_KEY`, `LLM_ENDPOINT` (default `http://localhost:8000/v1`,
   e.g. `http://192.168.0.72:8000/v1` on the inference node), `LLM_MODEL`, shared storage path.
3. README quick-start documenting startup order:
   vLLM (B60) -> Kokoro TTS gateway -> lipsync worker (3060 Ti) -> pipeline run.
4. Test strategy: unit tests always runnable; integration tests marked `@pytest.mark.live`
   and skipped when services are unreachable; wire into `run_tests.py`.
5. Repoint the git remote / GitHub repo to a clean state: large clones and weights fetched by
   helper scripts (`download_weights.sh` already exists in the MuseTalk clone), documented in
   README rather than committed.

## Acceptance criteria

- Fresh clone + `./venv/bin/pip install -r requirements.txt` + `python run_tests.py` passes
  without any live service.
- README lets a new operator reproduce one end-to-end animation on the B60/3060 Ti split.
