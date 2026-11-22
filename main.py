#!/usr/bin/env python3
"""
Main entry point for the Animation Agent Pipeline.
"""

import logging
import os
import sys

from src.core.pipeline import AnimationPipeline


def main() -> int:
    """Run the animation pipeline end to end and report results."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger = logging.getLogger("animation_agent.main")

    project_root = os.path.dirname(os.path.abspath(__file__))
    sample_script = os.path.join(project_root, "data", "input", "sample_script.txt")

    logger.info("Starting Animation Agent Pipeline...")
    pipeline = AnimationPipeline()

    try:
        result = pipeline.run_pipeline(sample_script)
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        logger.error("Pipeline failed during stage '%s': %s", pipeline.current_stage, exc)
        return 1

    timeline = result["timeline"]
    package = result["package"]
    logger.info("Pipeline completed successfully.")
    logger.info("Shots generated: %d", timeline["timeline_metadata"]["total_shots"])
    logger.info("Total duration: %.2fs", timeline["timeline_metadata"]["total_duration"])
    if result.get("master_animation_path"):
        logger.info("Master animation video: %s", result["master_animation_path"])
    logger.info("Cartoon Animator package: %s", package["package_path"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
