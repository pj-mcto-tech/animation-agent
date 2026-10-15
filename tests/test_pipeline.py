import unittest
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.pipeline import AnimationPipeline

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
        config = self.pipeline._load_config()
        self.assertIn("input_dir", config)
        self.assertIn("processed_dir", config)
        self.assertIn("output_dir", config)
        self.assertIn("shared_storage", config)
        self.assertIn("llm_model", config)
        self.assertIn("audio_engine", config)

if __name__ == '__main__':
    unittest.main()