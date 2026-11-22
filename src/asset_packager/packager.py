"""Asset packaging stage: supports AniCraft, ArtCraft, and legacy Cartoon Animator targets."""

from __future__ import annotations

import json
import logging
import os
import shutil
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

PACKAGE_NAME = "animation_package.zip"
TIMELINE_NAME = "timeline.json"
MANIFEST_NAME = "manifest.json"
ANICRAFT_DOC_NAME = "project.anicraft"


class AssetPackager:
    """Assembles timeline JSON + audio assets + video assets + manifests into a distributable ZIP.

    Supports AniCraft (.anicraft document generation), ArtCraft asset sets, and legacy formats.
    An optional `shared_storage_dir` mirrors the package to a network/shared directory.
    """

    def __init__(
        self,
        output_dir: str,
        shared_storage_dir: Optional[str] = None,
        target_platform: str = "anicraft",
        anicraft_cli_path: Optional[str] = None,
    ):
        self.output_dir = output_dir
        self.shared_storage_dir = shared_storage_dir or None
        self.target_platform = target_platform
        self.anicraft_cli_path = anicraft_cli_path or "/home/pj-mcnerney/ai/anicraft/target/debug/anicraft-cli"
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_anicraft_document(
        self,
        timeline_data: Dict[str, Any],
        output_path: str,
        fps: float = 24.0,
        width: int = 832,
        height: int = 480,
    ) -> str:
        """Create a native .anicraft project file matching the timeline shots and layers."""
        shots = timeline_data.get("shots", [])
        total_duration = float(
            timeline_data.get("total_duration")
            or timeline_data.get("timeline_metadata", {}).get("total_duration")
            or 10.0
        )
        total_frames = max(1, int(total_duration * fps))

        layers = []
        layer_id = 1

        # Layer 1: Shots / Scene blocking
        shot_keyframes = []
        current_frame = 0
        for idx, shot in enumerate(shots):
            dur_sec = float(shot.get("duration", 2.0))
            shot_dur_frames = max(1, int(dur_sec * fps))
            shot_keyframes.append({
                "start": current_frame,
                "duration": shot_dur_frames,
                "elements": [],
                "tween": None,
                "label": f"Shot {idx + 1}: {shot.get('id', idx + 1)}"
            })
            current_frame += shot_dur_frames

        if not shot_keyframes:
            shot_keyframes.append({
                "start": 0,
                "duration": total_frames,
                "elements": [],
                "tween": None,
                "label": "Master"
            })

        layers.append({
            "id": layer_id,
            "name": "Shots",
            "kind": "Normal",
            "visible": True,
            "locked": False,
            "outline": False,
            "color": {"r": 0.31, "g": 0.64, "b": 1.0, "a": 1.0},
            "keyframes": shot_keyframes,
        })
        layer_id += 1

        # Layer 2: Audio & Dialogue markers
        audio_keyframes = []
        current_frame = 0
        for idx, shot in enumerate(shots):
            dur_sec = float(shot.get("duration", 2.0))
            shot_dur_frames = max(1, int(dur_sec * fps))
            dialogue = shot.get("dialogue") or shot.get("script") or ""
            audio_keyframes.append({
                "start": current_frame,
                "duration": shot_dur_frames,
                "elements": [],
                "tween": None,
                "label": dialogue[:30] if dialogue else "Audio"
            })
            current_frame += shot_dur_frames

        if not audio_keyframes:
            audio_keyframes.append({
                "start": 0,
                "duration": total_frames,
                "elements": [],
                "tween": None,
                "label": "Audio"
            })

        layers.append({
            "id": layer_id,
            "name": "Dialogue & Audio",
            "kind": "Normal",
            "visible": True,
            "locked": True,
            "outline": False,
            "color": {"r": 0.95, "g": 0.55, "b": 0.20, "a": 1.0},
            "keyframes": audio_keyframes,
        })
        layer_id += 1

        doc = {
            "format": "anicraft",
            "version": 3,
            "generator": "AniCraft Pipeline Agent",
            "paths": [],
            "document": {
                "stage": {
                    "width": width,
                    "height": height,
                    "fps": fps,
                    "background": {"r": 0.1, "g": 0.1, "b": 0.12, "a": 1.0},
                },
                "scenes": [
                    {
                        "name": timeline_data.get("timeline_metadata", {}).get("project", "Scene 1"),
                        "timeline": {
                            "layers": layers
                        }
                    }
                ],
                "library": [],
                "next_id": layer_id + 1
            }
        }

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(doc, handle, indent=2)

        logger.info("Generated native AniCraft project document at %s", output_path)
        return output_path

    def build_package(
        self,
        timeline_data: Dict[str, Any],
        audio_manifest: Optional[Dict[str, Any]] = None,
        video_manifest: Optional[Dict[str, Any]] = None,
        master_animation_path: Optional[str] = None,
        extra_files: Optional[List[str]] = None,
        package_name: str = PACKAGE_NAME,
    ) -> Dict[str, Any]:
        """Write timeline + manifest + audio + video into staging dir and zip them."""
        staging_dir = os.path.join(self.output_dir, "staging")
        audio_dir = os.path.join(staging_dir, "audio")
        video_dir = os.path.join(staging_dir, "video")
        for dir_path in (staging_dir, audio_dir, video_dir):
            os.makedirs(dir_path, exist_ok=True)

        timeline_path = os.path.join(staging_dir, TIMELINE_NAME)
        with open(timeline_path, "w", encoding="utf-8") as handle:
            json.dump(timeline_data, handle, indent=2)

        staged_audio: List[str] = []
        for source in self._iter_audio_files(audio_manifest, extra_files):
            target = os.path.join(audio_dir, os.path.basename(source))
            shutil.copy2(source, target)
            staged_audio.append(os.path.join("audio", os.path.basename(source)))

        staged_video: List[str] = []
        if video_manifest:
            for shot in video_manifest.get("shots", []):
                vid_path = shot.get("synced_video_path") or shot.get("video_path")
                if vid_path and os.path.isfile(vid_path):
                    target = os.path.join(video_dir, os.path.basename(vid_path))
                    shutil.copy2(vid_path, target)
                    staged_video.append(os.path.join("video", os.path.basename(vid_path)))
            master_vid = video_manifest.get("master_video_path")
            if master_vid and os.path.isfile(master_vid):
                target = os.path.join(video_dir, os.path.basename(master_vid))
                shutil.copy2(master_vid, target)
                staged_video.append(os.path.join("video", os.path.basename(master_vid)))

        staged_master: List[str] = []
        if master_animation_path and os.path.isfile(master_animation_path):
            target = os.path.join(staging_dir, os.path.basename(master_animation_path))
            shutil.copy2(master_animation_path, target)
            staged_master.append(os.path.basename(master_animation_path))

        # Generate AniCraft document for AniCraft/ArtCraft targets
        anicraft_doc_rel = None
        if self.target_platform in ("anicraft", "artcraft"):
            anicraft_file_path = os.path.join(staging_dir, ANICRAFT_DOC_NAME)
            self.generate_anicraft_document(
                timeline_data=timeline_data,
                output_path=anicraft_file_path,
                fps=float(timeline_data.get("fps", 24.0)),
            )
            anicraft_doc_rel = ANICRAFT_DOC_NAME

        staged_extra = [anicraft_doc_rel] if anicraft_doc_rel else []

        manifest = {
            "package_format": f"{self.target_platform}-v1",
            "target_platform": self.target_platform,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "timeline_file": TIMELINE_NAME,
            "anicraft_file": anicraft_doc_rel,
            "shot_count": len(timeline_data.get("shots", [])),
            "total_duration": timeline_data.get("total_duration")
            or timeline_data.get("timeline_metadata", {}).get("total_duration"),
            "audio_backend": (audio_manifest or {}).get("backend"),
            "video_backend": (video_manifest or {}).get("backend"),
            "files": [TIMELINE_NAME, MANIFEST_NAME, *staged_extra, *staged_master, *staged_audio, *staged_video],
        }
        manifest_path = os.path.join(staging_dir, MANIFEST_NAME)
        with open(manifest_path, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2)

        zip_path = os.path.join(self.output_dir, package_name)
        archive_entries = manifest["files"]
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for entry in archive_entries:
                archive.write(os.path.join(staging_dir, entry), arcname=entry)

        logger.info(
            "Asset package built (%s target): %s (%d files, %d shots)",
            self.target_platform,
            zip_path,
            len(archive_entries),
            manifest["shot_count"],
        )
        self._sync_shared_storage(zip_path, staging_dir, archive_entries)
        return {"package_path": zip_path, "manifest": manifest, "anicraft_path": os.path.join(staging_dir, ANICRAFT_DOC_NAME) if anicraft_doc_rel else None}

    @staticmethod
    def _iter_audio_files(
        audio_manifest: Optional[Dict[str, Any]], extra_files: Optional[List[str]]
    ) -> List[str]:
        paths: List[str] = []
        if audio_manifest:
            for shot in audio_manifest.get("shots", []):
                paths.append(shot["audio_path"])
            music = audio_manifest.get("music", {}).get("audio_path")
            if music:
                paths.append(music)
            for sfx in audio_manifest.get("sfx", []):
                paths.append(sfx["audio_path"])
        paths.extend(extra_files or [])
        existing = []
        for path in paths:
            if path and os.path.isfile(path):
                existing.append(path)
            else:
                logger.warning("Skipping missing asset for packaging: %s", path)
        return existing

    def _sync_shared_storage(
        self, zip_path: str, staging_dir: str, entries: List[str]
    ) -> None:
        if not self.shared_storage_dir:
            return
        if os.path.abspath(self.shared_storage_dir) == os.path.abspath(self.output_dir):
            return
        try:
            os.makedirs(self.shared_storage_dir, exist_ok=True)
            shutil.copy2(zip_path, os.path.join(self.shared_storage_dir, PACKAGE_NAME))
            for entry in entries:
                target_dir = os.path.dirname(
                    os.path.join(self.shared_storage_dir, entry)
                ) or self.shared_storage_dir
                os.makedirs(target_dir, exist_ok=True)
                shutil.copy2(
                    os.path.join(staging_dir, entry),
                    os.path.join(self.shared_storage_dir, entry),
                )
            logger.info(
                "Package mirrored to shared storage: %s", self.shared_storage_dir
            )
        except OSError as exc:
            logger.warning(
                "Could not mirror package to %s (%s); local package still valid.",
                self.shared_storage_dir,
                exc,
            )
