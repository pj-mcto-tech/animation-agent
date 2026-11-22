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

from src.asset_packager.packager import AssetPackager
from src.audio_generator.generator import AudioGenerator
from src.core.media_utils import mux_audio_and_video
from src.lipsync.client import LipSyncClient
from src.timeline_generator.timeline_generator import (
    AnimationTimeline,
    TimelineEntry,
    TimelineGenerator,
)
from src.video_generator.generator import VideoGenerator

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "config", "default_config.json")
)


class AnimationPipeline:
    """Runs the full script -> timeline -> audio -> video -> lipsync -> package animation pipeline."""

    def __init__(
        self,
        config_path: Optional[str] = None,
        timeline_generator: Optional[TimelineGenerator] = None,
        audio_generator: Optional[AudioGenerator] = None,
        video_generator: Optional[VideoGenerator] = None,
        lipsync_client: Optional[LipSyncClient] = None,
    ):
        self.config = self._load_config(config_path)
        self.current_stage = "idle"
        self._timeline_generator = timeline_generator
        self._audio_generator = audio_generator
        self._video_generator = video_generator
        self._lipsync_client = lipsync_client
        logger.info(
            "AnimationPipeline initialized (llm=%s, audio=%s, video=%s on %s)",
            self.config["llm_model"],
            self.config["tts_backend"],
            self.config["video_backend"],
            self.config["video_device"],
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
        audio = raw.get("audio", {})
        video = raw.get("video", {})
        lipsync = raw.get("lipsync", {})
        storage = raw.get("storage", {})
        processed_dir = storage.get("processed", "./data/processed")
        config: Dict[str, Any] = {
            "project_name": pipeline.get("project_name", "animation-agent"),
            "llm_endpoint": os.getenv(
                "LLM_ENDPOINT", llm.get("endpoint", "http://localhost:8000/v1")
            ),
            "llm_model": os.getenv("LLM_MODEL", llm.get("model", "Qwen3-Coder-30B-A3B")),
            "llm_temperature": float(llm.get("temperature", 0.7)),
            # Normalize friendly names ("kokoro-onnx" -> "kokoro").
            "tts_backend": audio.get("tts_backend", "kokoro").replace("-onnx", ""),
            "voice": os.getenv("TTS_VOICE", audio.get("voice", "af_heart")),
            # Video generation settings (focus on NVIDIA RTX CUDA)
            "video_backend": os.getenv("VIDEO_BACKEND", video.get("backend", "synthetic")),
            "video_device": os.getenv("VIDEO_DEVICE", video.get("device", "cuda")),
            "video_fps": int(video.get("fps", 24)),
            "video_width": int(video.get("width", 832)),
            "video_height": int(video.get("height", 480)),
            # Lip-sync worker settings
            "lipsync_enabled": lipsync.get("enabled", True),
            "lipsync_endpoint": os.getenv("LIPSYNC_WORKER_URL", lipsync.get("endpoint", "http://localhost:8001")),
            "lipsync_engine": lipsync.get("engine", "latentsync"),
            # Storage
            "output_dir": storage.get("output", "./data/output"),
            "processed_dir": processed_dir,
            "audio_dir": os.path.join(processed_dir, "audio"),
            "video_dir": os.path.join(processed_dir, "video"),
            "timeline_output": storage.get("timeline", "./data/processed/timeline.json"),
            "shared_storage_dir": storage.get("mount_point")
            if storage.get("sync_enabled")
            else None,
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

        self.current_stage = "video_generation"
        logger.info("Stage 4: Generating video clips via %s on %s", self.config["video_backend"], self.config["video_device"])
        video_manifest = self._generate_video(timeline_data)
        results["video_manifest"] = video_manifest

        self.current_stage = "lipsync_stage"
        logger.info("Stage 5: Coordinating lip-sync on dialogue shots")
        lipsync_manifest = self._process_lipsync(video_manifest, audio_manifest)
        results["lipsync_manifest"] = lipsync_manifest

        self.current_stage = "master_mux"
        logger.info("Stage 6: Assembling and muxing final master animation")
        master_animation = self._mux_master_animation(lipsync_manifest or video_manifest, audio_manifest)
        results["master_animation_path"] = master_animation

        self.current_stage = "asset_packaging"
        logger.info("Stage 7: Packaging assets for Cartoon Animator")
        package_info = self._package_assets(
            timeline_data,
            audio_manifest=audio_manifest,
            video_manifest=lipsync_manifest or video_manifest,
            master_animation_path=master_animation,
        )
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
        """Generate real voiceover/music/SFX audio files for every timeline shot."""
        timeline = AnimationTimeline(
            entries=[TimelineEntry(**shot) for shot in timeline_data["shots"]],
            total_duration=timeline_data["timeline_metadata"]["total_duration"],
        )

        generator = self._audio_generator or AudioGenerator(
            backend=self.config["tts_backend"], voice=self.config["voice"]
        )
        manifest = generator.generate_for_timeline(
            timeline,
            output_dir=self.config["audio_dir"],
            music_prompt=f"background score for {timeline_data['timeline_metadata'].get('project', self.config['project_name'])}",
        )

        manifest_path = os.path.join(self.config["processed_dir"], "audio_manifest.json")
        self._write_json(manifest_path, manifest)
        manifest["manifest_path"] = manifest_path
        logger.info("Audio manifest written to %s", manifest_path)
        return manifest

    # ------------------------------------------------------------------ #
    # Stage 4: Video Generation
    # ------------------------------------------------------------------ #

    def _generate_video(self, timeline_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate video clips for each timeline shot and concatenate into master_video.mp4."""
        timeline = AnimationTimeline(
            entries=[TimelineEntry(**shot) for shot in timeline_data["shots"]],
            total_duration=timeline_data["timeline_metadata"]["total_duration"],
        )

        generator = self._video_generator or VideoGenerator(
            backend=self.config["video_backend"],
            device=self.config["video_device"],
            fps=self.config["video_fps"],
            width=self.config["video_width"],
            height=self.config["video_height"],
        )

        manifest = generator.generate_for_timeline(
            timeline=timeline,
            output_dir=self.config["video_dir"],
        )

        manifest_path = os.path.join(self.config["processed_dir"], "video_manifest.json")
        self._write_json(manifest_path, manifest)
        manifest["manifest_path"] = manifest_path
        logger.info("Video manifest written to %s", manifest_path)
        return manifest

    # ------------------------------------------------------------------ #
    # Stage 5: Lip-Sync Processing
    # ------------------------------------------------------------------ #

    def _process_lipsync(
        self, video_manifest: Dict[str, Any], audio_manifest: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply lip-sync via local worker on character dialogue shots."""
        client = self._lipsync_client or LipSyncClient(
            endpoint=self.config["lipsync_endpoint"],
            enabled=self.config["lipsync_enabled"],
            engine=self.config["lipsync_engine"],
        )

        synced_dir = os.path.join(self.config["processed_dir"], "lipsync")
        manifest = client.process_timeline(
            video_manifest=video_manifest,
            audio_manifest=audio_manifest,
            output_dir=synced_dir,
        )

        manifest_path = os.path.join(self.config["processed_dir"], "lipsync_manifest.json")
        self._write_json(manifest_path, manifest)
        manifest["manifest_path"] = manifest_path
        logger.info("Lip-sync manifest written to %s", manifest_path)
        return manifest

    # ------------------------------------------------------------------ #
    # Stage 6: Master Mux
    # ------------------------------------------------------------------ #

    def _mux_master_animation(
        self, video_manifest: Dict[str, Any], audio_manifest: Dict[str, Any]
    ) -> Optional[str]:
        """Mux assembled video with audio track to produce final master animation MP4."""
        master_video = video_manifest.get("master_video_path")
        if not master_video or not os.path.isfile(master_video):
            logger.warning("No master video found for muxing; skipping.")
            return None

        # Preferred audio track: background score or first available voiceover
        audio_path = audio_manifest.get("music", {}).get("audio_path")
        if not audio_path or not os.path.isfile(audio_path):
            shots = audio_manifest.get("shots", [])
            for shot in shots:
                candidate = shot.get("audio_path")
                if candidate and os.path.isfile(candidate):
                    audio_path = candidate
                    break

        if not audio_path or not os.path.isfile(audio_path):
            logger.warning("No valid audio track found for master mux; using raw video.")
            return master_video

        master_out = os.path.join(self.config["output_dir"], "final_master_animation.mp4")
        try:
            mux_audio_and_video(
                video_path=master_video,
                audio_path=audio_path,
                output_path=master_out,
                video_codec="libx264",
            )
            return master_out
        except Exception as exc:
            logger.warning("Master muxing failed (%s); returning master video path.", exc)
            return master_video

    # ------------------------------------------------------------------ #
    # Stage 7: Asset Packaging
    # ------------------------------------------------------------------ #

    def _package_assets(
        self,
        timeline_data: Dict[str, Any],
        audio_manifest: Optional[Dict[str, Any]] = None,
        video_manifest: Optional[Dict[str, Any]] = None,
        master_animation_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build Cartoon Animator ZIP (timeline + audio + video + manifest + final master)."""
        timeline_data = {
            **timeline_data,
            "timeline_metadata": {
                **timeline_data["timeline_metadata"],
                "project": self.config["project_name"],
            },
        }

        packager = AssetPackager(
            output_dir=self.config["output_dir"],
            shared_storage_dir=self.config.get("shared_storage_dir"),
        )
        package_info = packager.build_package(
            timeline_data=timeline_data,
            audio_manifest=audio_manifest,
            video_manifest=video_manifest,
            master_animation_path=master_animation_path,
        )
        if audio_manifest:
            package_info["audio_manifest_path"] = audio_manifest.get("manifest_path")
        if video_manifest:
            package_info["video_manifest_path"] = video_manifest.get("manifest_path")
        if master_animation_path:
            package_info["master_animation_path"] = master_animation_path
        return package_info

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
