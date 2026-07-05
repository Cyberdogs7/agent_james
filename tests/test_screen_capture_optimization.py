import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import asyncio

# Ensure backend can be imported
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Mock dependencies
sys.modules['google'] = MagicMock()
sys.modules['google.genai'] = MagicMock()
sys.modules['google.genai.types'] = MagicMock()
sys.modules['pyaudio'] = MagicMock()
sys.modules['httpx'] = MagicMock()

# Mock Agents
for module in ['cad_agent', 'web_agent', 'kasa_agent', 'printer_agent', 'trello_agent',
               'timer_agent', 'update_agent', 'search_agent',
               'scraper_agent', 'proactive_agent', 'git_ops', 'os_agent',
               'task_manager', 'project_manager', 'giphy_client',
               'giphy_client.apis.default_api', 'giphy_client.api_client',
               'dotenv', 'time_utils']:
    sys.modules[f'backend.{module}'] = MagicMock()
    sys.modules[module] = MagicMock()

# Mock mss
mock_mss_module = MagicMock()
sys.modules['mss'] = mock_mss_module

# Mock cv2 and numpy
mock_cv2 = MagicMock()
sys.modules['cv2'] = mock_cv2
sys.modules['numpy'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['PIL.Image'] = MagicMock()

from backend.ada import AudioLoop

class TestScreenCaptureOptimization(unittest.TestCase):
    def setUp(self):
        # Setup mss mock
        self.mock_sct_instance = MagicMock()
        self.mock_sct_instance.__enter__.return_value = self.mock_sct_instance
        self.mock_sct_instance.__exit__.return_value = None
        self.mock_sct_instance.monitors = [{'top': 0, 'left': 0, 'width': 1920, 'height': 1080}, {'top': 0, 'left': 0, 'width': 1920, 'height': 1080}]
        self.mock_sct_instance.grab.return_value = MagicMock()
        mock_mss_module.mss.return_value = self.mock_sct_instance

        # Setup cv2 mock
        mock_frame = MagicMock()
        mock_frame.shape = (1080, 1920, 3)
        mock_cv2.cvtColor.return_value = mock_frame
        mock_cv2.resize.return_value = mock_frame
        mock_cv2.imencode.return_value = (True, b'fake_data')

        # Reset call count
        mock_mss_module.mss.reset_mock()

    def test_mss_initialization_frequency(self):
        loop = AudioLoop(video_mode="screen")
        loop.project_manager = MagicMock()

        for _ in range(5):
            loop._get_screen_sync()

        # Verify optimized behavior: mss() called 1 time
        print(f"mss.mss() called {mock_mss_module.mss.call_count} times")
        self.assertEqual(mock_mss_module.mss.call_count, 1)

    def test_close_cleans_up_mss(self):
        loop = AudioLoop(video_mode="screen")
        loop.project_manager = MagicMock()

        # Initialize sct
        loop._get_screen_sync()
        self.assertIsNotNone(loop.sct)

        # Call close
        loop.close()

        # Verify sct.close() was called
        self.mock_sct_instance.close.assert_called_once()
        self.assertIsNone(loop.sct)

if __name__ == '__main__':
    unittest.main()
