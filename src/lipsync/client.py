"""HTTP client for local LatentSync / MuseTalk lip-sync worker on the RTX 3060 Ti."""

from __future__ import annotations

import json
import logging
import os
import shutil
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from src.core.media_utils import concat_video_clips

logger = logging.getLogger(__name__)

DEFAULT_LIPSYNC_URL = "http://localhost:8001"


class LipSyncClient:
    """Client for the RTX 3060 Ti lip-sync FastAPI daemon."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        enabled: bool = True,
        engine: str = "latentsync",
        timeout: float = 120.0,
    ):
        self.endpoint = (
            endpoint
            or os.getenv("LIPSYNC_WORKER_URL")
            or DEFAULT_LIPSYNC_URL
        ).rstrip("/")
        self.enabled = enabled
        self.engine = engine
        self.timeout = timeout
        self._checked_availability = False
        self._is_available = False

    def is_available(self) -> bool:
        """Probe the worker health endpoint with a short timeout."""
        if not self.enabled:
            return False
        try:
            req = urllib.request.Request(f"{self.endpoint}/health")
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    # Ready if at least one engine is ready or service is up
                    self._is_available = data.get("status") == "ok"
                    return self._is_available
        except Exception:
            self._is_available = False
            return False
        return False

    def sync_shot(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        engine: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Send video + audio to lip-sync worker and save result to output_path."""
        if not self.is_available():
            logger.warning(
                "Lip-sync worker at %s unavailable; passing through original video %s",
                self.endpoint,
                video_path,
            )
            shutil.copy2(video_path, output_path)
            return output_path

        payload = {
            "engine": engine or self.engine,
            "video_path": os.path.abspath(video_path),
            "audio_path": os.path.abspath(audio_path),
            **kwargs,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.endpoint}/v1/lipsync",
            data=data,
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                remote_out = result.get("output_path")
                if remote_out and os.path.isfile(remote_out):
                    shutil.copy2(remote_out, output_path)
                elif result.get("download_url"):
                    download_url = f"{self.endpoint}{result['download_url']}"
                    with urllib.request.urlopen(download_url, timeout=60) as dl_resp:
                        with open(output_path, "wb") as out_f:
                            out_f.write(dl_resp.read())
                else:
                    logger.warning("Lip-sync response missing output, using original video.")
                    shutil.copy2(video_path, output_path)
            logger.info("Lip-synced shot written: %s", output_path)
            return output_path
        except Exception as exc:
            logger.warning("Lip-sync failed (%s); falling back to original video.", exc)
            shutil.copy2(video_path, output_path)
            return output_path

    def process_timeline(
        self,
        video_manifest: Dict[str, Any],
        audio_manifest: Dict[str, Any],
        output_dir: str,
    ) -> Dict[str, Any]:
        """Apply lip-sync to character shots with dialogue and compile final video."""
        os.makedirs(output_dir, exist_ok=True)
        synced_clips: List[str] = []
        shot_records: List[Dict[str, Any]] = []

        audio_by_id = {
            shot["shot_id"]: shot for shot in audio_manifest.get("shots", [])
        }

        for video_shot in video_manifest.get("shots", []):
            shot_id = video_shot["shot_id"]
            video_path = video_shot["video_path"]
            audio_info = audio_by_id.get(shot_id)
            out_clip = os.path.join(output_dir, f"{shot_id}_synced.mp4")

            if (
                self.enabled
                and video_shot.get("type") == "character"
                and audio_info
                and os.path.isfile(audio_info.get("audio_path", ""))
            ):
                logger.info("Applying lip-sync to character shot: %s", shot_id)
                self.sync_shot(
                    video_path=video_path,
                    audio_path=audio_info["audio_path"],
                    output_path=out_clip,
                )
            else:
                shutil.copy2(video_path, out_clip)

            synced_clips.append(out_clip)
            shot_records.append(
                {
                    **video_shot,
                    "synced_video_path": out_clip,
                }
            )

        synced_master = os.path.join(output_dir, "master_video_synced.mp4")
        concat_video_clips(synced_clips, synced_master)

        return {
            "master_video_path": synced_master,
            "shots": shot_records,
            "lipsync_enabled": self.enabled,
        }
