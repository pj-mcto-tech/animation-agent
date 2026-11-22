import unittest
import sys
import os
import tempfile

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.pipeline import AnimationPipeline
from src.timeline_generator.timeline_generator import AnimationTimeline, TimelineEntry


class FakeTimelineGenerator:
    """Stand-in for TimelineGenerator that never touches the network."""

    def __init__(self, timeline):
        self._timeline = timeline
        self.calls = []

    def generate_timeline(self, script, context=None):
        self.calls.append({"script": script, "context": context})
        return self._timeline


def _sample_timeline():
    return AnimationTimeline(
        entries=[
            TimelineEntry(timestamp="00:00:00", description="Robot picks up brush", duration=3.0, type="character"),
            TimelineEntry(timestamp="00:00:03", description="Paint stroke effect", duration=2.0, type="effect"),
            TimelineEntry(timestamp="00:00:05", description="Workshop background", duration=4.0, type="background"),
        ],
        total_duration=9.0,
    )


class TestAnimationPipeline(unittest.TestCase):
    """Test cases for the Animation Pipeline."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.pipeline = AnimationPipeline()

    def test_pipeline_initialization(self):
        """Test that the pipeline initializes correctly."""
        self.assertIsNotNone(self.pipeline)
        self.assertEqual(self.pipeline.current_stage, "idle")

    def test_config_loading(self):
        """Test that the pipeline loads configuration correctly."""
        config = self.pipeline._load_config(None)
        self.assertIn("project_name", config)
        self.assertIn("llm_endpoint", config)
        self.assertIn("llm_model", config)
        self.assertIn("tts_backend", config)
        self.assertIn("output_dir", config)
        self.assertIn("processed_dir", config)
        self.assertIn("timeline_output", config)

    def test_process_script_missing_file(self):
        """Stage 1 should raise FileNotFoundError for a bad path."""
        with self.assertRaises(FileNotFoundError):
            self.pipeline._process_script("data/input/does_not_exist.txt")

    def test_run_pipeline_with_fake_generator(self):
        """End-to-end run using an injected generator writes a package to disk."""
        fake = FakeTimelineGenerator(_sample_timeline())
        with tempfile.TemporaryDirectory() as tmp:
            pipeline = AnimationPipeline(timeline_generator=fake)
            pipeline.config["output_dir"] = os.path.join(tmp, "output")
            pipeline.config["processed_dir"] = os.path.join(tmp, "processed")
            pipeline.config["timeline_output"] = os.path.join(tmp, "processed", "timeline.json")

            script_path = os.path.join(tmp, "script.txt")
            with open(script_path, "w", encoding="utf-8") as fh:
                fh.write("Title: Test\nAuthor: Tester\nA robot paints a canvas.\n")

            result = pipeline.run_pipeline(script_path)

            self.assertEqual(pipeline.current_stage, "completed")
            self.assertEqual(result["timeline"]["timeline_metadata"]["total_shots"], 3)
            self.assertEqual(len(fake.calls), 1)
            self.assertTrue(os.path.exists(result["package"]["package_path"]))
            self.assertTrue(os.path.exists(os.path.join(tmp, "processed", "audio_manifest.json")))


if __name__ == '__main__':
    unittest.main()
