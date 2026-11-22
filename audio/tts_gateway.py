import io
import soundfile as sf
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from kokoro_onnx import Kokoro

app = FastAPI(title="SDF-1Alpha Local TTS Gateway")

MODEL_PATH = "/home/pj-mcnerney/ai/animation-agent/audio/kokoro-v1.0.onnx"
VOICES_PATH = "/home/pj-mcnerney/ai/animation-agent/audio/voices-v1.0.bin"

kokoro = Kokoro(MODEL_PATH, VOICES_PATH)

class SpeechRequest(BaseModel):
    model: str = "kokoro-v1"
    input: str
    voice: str = "af_heart"
    speed: float = 1.0
    response_format: str = "wav"

@app.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": [{"id": "kokoro-v1", "object": "model", "owned_by": "sdf-1alpha"}],
    }

@app.get("/v1/audio/voices")
def list_voices():
    return {"voices": sorted(list(kokoro.get_voices()))}

@app.post("/v1/audio/speech")
def create_speech(req: SpeechRequest):
    if not req.input.strip():
        raise HTTPException(status_code=400, detail="Input text cannot be empty")
    try:
        samples, sample_rate = kokoro.create(
            req.input,
            voice=req.voice,
            speed=req.speed,
            lang="en-us",
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    buf = io.BytesIO()
    fmt = "FLAC" if req.response_format.lower() == "flac" else "WAV"
    media_type = "audio/flac" if fmt == "FLAC" else "audio/wav"
    sf.write(buf, samples, sample_rate, format=fmt)
    return Response(content=buf.getvalue(), media_type=media_type)
