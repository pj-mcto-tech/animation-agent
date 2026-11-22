"""Stage 4: build the Cartoon Animator-compatible asset package."""

from __future__ import annotations

import json
import logging
import os
import shutil
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

PACKAGE_NAME = "cartoon_animator_package.zip"
TIMELINE_NAME = "timeline.json"
MANIFEST_NAME = "manifest.json"


class AssetPackager:
    """Assembles timeline JSON + audio assets + manifest into a distributable ZIP.

    An optional `shared_storage_dir` mirrors the package to the Windows-mapped
    directory consumed by Cartoon Animator.
    """

    def __init__(self, output_dir: str, shared_storage_dir: Optional[str] = None):
        self.output_dir = output_dir
        self.shared_storage_dir = shared_storage_dir or None
        os.makedirs(self.output_dir, exist_ok=True)

    def build_package(
        self,
        timeline_data: Dict[str, Any],
        audio_manifest: Optional[Dict[str, Any]] = None,
        extra_files: Optional[List[str]] = None,
        package_name: str = PACKAGE_NAME,
    ) -> Dict[str, Any]:
        """Write timeline + manifest into a staging dir and zip them together."""
        staging_dir = os.path.join(self.output_dir, "staging")
        audio_dir = os.path.join(staging_dir, "audio")
        for dir_path in (staging_dir, audio_dir):
            os.makedirs(dir_path, exist_ok=True)

        timeline_path = os.path.join(staging_dir, TIMELINE_NAME)
        with open(timeline_path, "w", encoding="utf-8") as handle:
            json.dump(timeline_data, handle, indent=2)

        staged_audio: List[str] = []
        for source in self._iter_audio_files(audio_manifest, extra_files):
            target = os.path.join(audio_dir, os.path.basename(source))
            shutil.copy2(source, target)
            staged_audio.append(os.path.join("audio", os.path.basename(source)))

        manifest = {
            "package_format": "cartoon-animator-v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "timeline_file": TIMELINE_NAME,
            "shot_count": len(timeline_data.get("shots", [])),
            "total_duration": timeline_data.get("total_duration")
            or timeline_data.get("timeline_metadata", {}).get("total_duration"),
            "audio_backend": (audio_manifest or {}).get("backend"),
            "files": [TIMELINE_NAME, MANIFEST_NAME, *staged_audio],
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
            "Asset package built: %s (%d files, %d shots)",
            zip_path,
            len(archive_entries),
            manifest["shot_count"],
        )
        self._sync_shared_storage(zip_path, staging_dir, archive_entries)
        return {"package_path": zip_path, "manifest": manifest}

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
