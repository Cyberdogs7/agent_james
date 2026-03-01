import unittest
import shutil
import tempfile
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys

# Ensure backend can be imported
sys.path.append(str(Path(__file__).parent.parent))

from backend.memory_manager import MemoryManager

class TestMemoryManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.manager = MemoryManager(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_add_memory_no_embedding(self):
        # Force client to be None
        self.manager.client = None

        success, msg = self.manager.add_memory("Use httpx", ["python"])
        self.assertTrue(success)

        # Verify file
        with open(self.manager.memory_file, "r") as f:
            data = json.load(f)
            self.assertEqual(data["content"], "Use httpx")
            self.assertEqual(data["tags"], ["python"])
            self.assertIsNone(data["embedding"])

    def test_search_memory_fallback(self):
        self.manager.client = None
        # Add memories manually
        self.manager.add_memory("Use httpx for requests", ["net"])
        self.manager.add_memory("Always assume linux", ["os"])

        # Search for "httpx"
        # Since client is None (or mocked to fail), it should use keyword fallback
        self.manager.client = None
        results = self.manager.search_memory("httpx")
        self.assertIn("Use httpx for requests", results)
        self.assertNotIn("Always assume linux", results)

    def test_cosine_similarity(self):
        vec1 = [1, 0, 0]
        vec2 = [1, 0, 0]
        self.assertAlmostEqual(self.manager._cosine_similarity(vec1, vec2), 1.0)

        vec3 = [0, 1, 0]
        self.assertAlmostEqual(self.manager._cosine_similarity(vec1, vec3), 0.0)

        vec4 = [1, 1, 0]
        # dot = 1, mag1 = 1, mag4 = sqrt(2) -> 1/sqrt(2) approx 0.707
        self.assertAlmostEqual(self.manager._cosine_similarity(vec1, vec4), 0.70710678)

    def test_add_memory_with_mock_embedding(self):
        # Setup mock
        mock_client = MagicMock()
        mock_embedding_result = MagicMock()
        mock_embedding_result.embeddings = [MagicMock(values=[0.1, 0.2, 0.3])]
        mock_client.models.embed_content.return_value = mock_embedding_result

        # Inject mock client
        self.manager.client = mock_client

        success, msg = self.manager.add_memory("Test embedding")
        self.assertTrue(success)

        with open(self.manager.memory_file, "r") as f:
            data = json.load(f)
            self.assertEqual(data["embedding"], [0.1, 0.2, 0.3])

if __name__ == '__main__':
    unittest.main()
