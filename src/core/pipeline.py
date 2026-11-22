#!/usr/bin/env python3
"""
Core orchestration for the Animation Agent pipeline.

Stages:
    1. Script Processing
    2. Timeline Generation (local LLM via an OpenAI-compatible vLLM endpoint)
    3. Audio Coordination
    4. Asset Packaging (Cartoon Animator compatible)
    5. Final Results
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from src.timeline_generator.timeline_generator import (
    AnimationTimeline,
    TimelineGenerator,
)

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "config", "default_config.json")
)


class AnimationPipeline:
    """Runs the full script -> timeline -> audio -> package animation pipeline."""

    def __init__(
        self,
        config_path: Optional[str] = None,
        timeline_generator: Optional[TimelineGenerator] = None,
    ):
        self.config = self._load_config(config_path)
        self.current_stage = "idle"
        self._timeline_generator = timeline_generator
        logger.info(
            "AnimationPipeline initialized (llm_endpoint=%s, llm_model=%s)",
            self.config["llm_endpoint"],
            self.config["llm_model"],
        )

    @staticmethod
    def _load_config(config_path: Optional[str]) -> Dict[str, Any]:
        """Load pipeline config, flattening the nested JSON and applying env overrides."""
        path = config_path or DEFAULT_CONFIG_PATH
        raw: Dict[str, Any] = {}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    raw = json.load(fh)
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("Could not read config at %s: %s", path, exc)
        else:
            logger.warning("Config file not found at %s; using defaults.", path)

        pipeline = raw.get("pipeline", {})
        llm = raw.get("llm", {})
        storage = raw.get("storage", {})
        config: Dict[str, Any] = {
            "project_name": pipeline.get("project_name", "animation-agent"),
            "llm_endpoint": os.getenv(
                "LLM_ENDPOINT", llm.get("endpoint", "http://localhost:8000/v1")
            ),
            "llm_model": os.getenv("LLM_MODEL", llm.get("model", "Qwen3-Coder-30B-A3B")),
            "llm_temperature": float(llm.get("temperature", 0.7)),
            "tts_backend": raw.get("audio", {}).get("tts_backend", "kokoro-onnx"),
            "output_dir": storage.get("output", "./data/output"),
            "processed_dir": storage.get("processed", "./data/processed"),
            "timeline_output": storage.get("timeline", "./data/processed/timeline.json"),
        }
        return config

    # ------------------------------------------------------------------ #
    # Orchestration
    # ------------------------------------------------------------------ #

    def run_pipeline(self, input_script_path: str) -> Dict[str, Any]:
        """Execute all pipeline stages and return the final results summary."""
        results: Dict[str, Any] = {"project": self.config["project_name"]}

        self.current_stage = "script_processing"
        logger.info("Stage 1: Processing script at %s", input_script_path)
        script_data = self._process_script(input_script_path)
        results["script"] = script_data

        self.current_stage = "timeline_generation"
        logger.info("Stage 2: Generating animation timeline via LLM")
        timeline_data = self._generate_timeline(script_data)
        results["timeline"] = timeline_data

        self.current_stage = "audio_coordination"
        logger.info("Stage 3: Coordinating audio requirements")
        audio_manifest = self._coordinate_audio(timeline_data)
        results["audio_manifest"] = audio_manifest

        self.current_stage = "asset_packaging"
        logger.info("Stage 4: Packaging assets for Cartoon Animator")
        package_info = self._package_assets(timeline_data, audio_manifest)
        results["package"] = package_info

        self.current_stage = "completed"
        logger.info("Pipeline completed successfully")
        return results

    # ------------------------------------------------------------------ #
    # Stage 1: Script Processing
    # ------------------------------------------------------------------ #

    def _process_script(self, input_script_path: str) -> Dict[str, Any]:
        """Read the script file and extract simple header metadata."""
        if not os.path.exists(input_script_path):
            raise FileNotFoundError(f"Input script not found: {input_script_path}")

        with open(input_script_path, "r", encoding="utf-8") as fh:
            content = fh.read().strip()

        metadata: Dict[str, str] = {}
        body_lines: List[str] = []
        for line in content.splitlines():
            stripped = line.strip()
            if ":" in stripped and stripped.split(":", 1)[0].strip().isalpha():
                key, value = stripped.split(":", 1)
                key = key.strip().lower()
                if key in {"title", "author", "version"}:
                    metadata[key] = value.strip()
                    continue
            body_lines.append(line)

        body = "\n".join(body_lines).strip()
        word_count = len(body.split())
        estimated_duration = round(word_count / 150 * 60, 2)  # ~150 wpm narration

        return {
            "title": metadata.get("title") or os.path.splitext(os.path.basename(input_script_path))[0],
            "author": metadata.get("author", "unknown"),
            "version": metadata.get("version", "1.0"),
            "content": body,
            "word_count": word_count,
            "estimated_duration": estimated_duration,
        }

    # ------------------------------------------------------------------ #
    # Stage 2: Timeline Generation
    # ------------------------------------------------------------------ #

    def _generate_timeline(self, script_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a validated animation timeline from the processed script."""
        generator = self._timeline_generator or TimelineGenerator(
            api_base_url=self.config["llm_endpoint"],
            model=self.config["llm_model"],
        )
        timeline: AnimationTimeline = generator.generate_timeline(
            script=script_data["content"],
            context={"title": script_data["title"], "estimated_duration": script_data["estimated_duration"]},
        )

        self._write_json(self.config["timeline_output"], timeline.model_dump())

        shots = [entry.model_dump() for entry in timeline.entries]
        logger.info("Timeline generated: %d shots, %.2fs total", len(shots), timeline.total_duration)
        return {
            "shots": shots,
            "timeline_metadata": {
                "total_shots": len(shots),
                "total_duration": timeline.total_duration,
                "timeline_output": self.config["timeline_output"],
            },
        }

    # ------------------------------------------------------------------ #
    # Stage 3: Audio Coordination
    # ------------------------------------------------------------------ #

    def _coordinate_audio(self, timeline_data: Dict[str, Any]) -> Dict[str, Any]:
        """Derive an audio manifest from timeline shots (real TTS synthesis in Phase 2)."""
        shots = timeline_data["shots"]
        audio_requirements: List[Dict[str, Any]] = []
        for index, shot in enumerate(shots):
            audio_requirements.append(
                {
                    "shot_id": index,
                    "type": shot.get("type", "background"),
                    "duration": shot.get("duration", 0.0),
                    "requires_voiceover": shot.get("type") == "character",
                    "requires_sfx": shot.get("type") == "effect",
                    "tts_backend": self.config["tts_backend"],
                }
            )

        manifest = {
            "total_duration": timeline_data["timeline_metadata"]["total_duration"],
            "audio_requirements": audio_requirements,
            "music_track": {"required": True, "style": "background", "backend": self.config["tts_backend"]},
        }
        manifest_path = os.path.join(self.config["processed_dir"], "audio_manifest.json")
        self._write_json(manifest_path, manifest)
        manifest["manifest_path"] = manifest_path
        logger.info("Audio manifest written to %s", manifest_path)
        return manifest

    # ------------------------------------------------------------------ #
    # Stage 4: Asset Packaging
    # ------------------------------------------------------------------ #

    def _package_assets(
        self, timeline_data: Dict[str, Any], audio_manifest: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Write the timeline and build a Cartoon Animator-compatible ZIP package."""
        import zipfile

        output_dir = self.config["output_dir"]
        os.makedirs(output_dir, exist_ok=True)

        timeline_path = os.path.join(output_dir, "timeline.json")
        self._write_json(timeline_path, timeline_data)

        manifest = {
            "project": self.config["project_name"],
            "version": "1.0",
            "shot_count": timeline_data["timeline_metadata"]["total_shots"],
            "total_duration": timeline_data["timeline_metadata"]["total_duration"],
            "assets": {
                "timeline": "timeline.json",
                "audio_manifest": audio_manifest.get("manifest_path"),
            },
        }
        manifest_path = os.path.join(output_dir, "manifest.json")
        self._write_json(manifest_path, manifest)

        zip_path = os.path.join(output_dir, "cartoon_animator_package.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.write(timeline_path, "timeline.json")
            archive.write(manifest_path, "manifest.json")
            if audio_manifest.get("manifest_path") and os.path.exists(audio_manifest["manifest_path"]):
                archive.write(audio_manifest["manifest_path"], "audio_manifest.json")

        logger.info("Cartoon Animator package written to %s", zip_path)
        return {
            "package_path": zip_path,
            "timeline_path": timeline_path,
            "manifest_path": manifest_path,
            "shot_count": timeline_data["timeline_metadata"]["total_shots"],
        }

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _write_json(path: str, payload: Any) -> None:
        """Write a JSON payload to disk, creating parent directories as needed."""
        parent = os.path.dirname(os.path.abspath(path))
        os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
