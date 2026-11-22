"""Unit tests for Stage 4 asset packaging."""

import json
import os
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.asset_packager.packager import AssetPackager

TIMELINE_DATA = {
    "shots": [
        {"timestamp": "00:00:00", "description": "Robot waves", "duration": 2.0, "type": "character"},
    ],
    "timeline_metadata": {"total_shots": 1, "total_duration": 2.0, "project": "unit-test"},
}


class TestAssetPackager(unittest.TestCase):
    def test_package_contains_timeline_manifest_and_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = os.path.join(tmp, "out")
            audio_path = os.path.join(tmp, "shot_001.wav")
            with open(audio_path, "wb") as fh:
                fh.write(b"RIFFfake-wav")

            packager = AssetPackager(output_dir=out_dir)
            result = packager.build_package(
                timeline_data=TIMELINE_DATA,
                audio_manifest={
                    "backend": "fake-tts",
                    "shots": [{"audio_path": audio_path}],
                    "music": {},
                    "sfx": [],
                },
            )

            zip_path = result["package_path"]
            self.assertTrue(os.path.isfile(zip_path))
            with zipfile.ZipFile(zip_path) as archive:
                names = archive.namelist()
                self.assertIn("timeline.json", names)
                self.assertIn("manifest.json", names)
                self.assertIn("audio/shot_001.wav", names)
                manifest = json.loads(archive.read("manifest.json"))
                self.assertEqual(manifest["package_format"], "cartoon-animator-v1")
                self.assertEqual(manifest["shot_count"], 1)
                self.assertEqual(manifest["audio_backend"], "fake-tts")
                # The manifest must list every file it claims, including itself.
                self.assertEqual(sorted(manifest["files"]), sorted(names))
                timeline = json.loads(archive.read("timeline.json"))
                self.assertEqual(timeline["timeline_metadata"]["project"], "unit-test")

    def test_missing_audio_is_skipped_not_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            packager = AssetPackager(output_dir=os.path.join(tmp, "out"))
            result = packager.build_package(
                timeline_data=TIMELINE_DATA,
                audio_manifest={"backend": "none", "shots": [{"audio_path": "/nope/missing.wav"}]},
            )
            with zipfile.ZipFile(result["package_path"]) as archive:
                self.assertNotIn("audio/missing.wav", archive.namelist())

    def test_shared_storage_mirror_failure_is_non_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            packager = AssetPackager(
                output_dir=os.path.join(tmp, "out"),
                shared_storage_dir="/proc/definitely_not_writable/shared",
            )
            result = packager.build_package(timeline_data=TIMELINE_DATA)
            self.assertTrue(os.path.isfile(result["package_path"]))


if __name__ == "__main__":
    unittest.main()
