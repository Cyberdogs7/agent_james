import sys
import os
import asyncio
import unittest
from unittest.mock import MagicMock, patch

# Ensure backend can be imported
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# 1. Mock Heavy Dependencies & Agents *before* importing ada
# This prevents AudioLoop from trying to init real agents that might require API keys or hardware.

sys.modules['google'] = MagicMock()
sys.modules['google.genai'] = MagicMock()
sys.modules['google.genai.types'] = MagicMock()
sys.modules['pyaudio'] = MagicMock()
sys.modules['httpx'] = MagicMock()

# Mock Agents
sys.modules['backend.cad_agent'] = MagicMock()
sys.modules['cad_agent'] = MagicMock()

sys.modules['backend.web_agent'] = MagicMock()
sys.modules['web_agent'] = MagicMock()

sys.modules['backend.kasa_agent'] = MagicMock()
sys.modules['kasa_agent'] = MagicMock()

sys.modules['backend.printer_agent'] = MagicMock()
sys.modules['printer_agent'] = MagicMock()

sys.modules['backend.trello_agent'] = MagicMock()
sys.modules['trello_agent'] = MagicMock()

sys.modules['backend.jules_agent'] = MagicMock()
sys.modules['jules_agent'] = MagicMock()

sys.modules['backend.timer_agent'] = MagicMock()
sys.modules['timer_agent'] = MagicMock()

sys.modules['backend.update_agent'] = MagicMock()
sys.modules['update_agent'] = MagicMock()

sys.modules['backend.search_agent'] = MagicMock()
sys.modules['search_agent'] = MagicMock()

sys.modules['backend.scraper_agent'] = MagicMock()
sys.modules['scraper_agent'] = MagicMock()

sys.modules['backend.proactive_agent'] = MagicMock()
sys.modules['proactive_agent'] = MagicMock()

sys.modules['backend.git_ops'] = MagicMock()
sys.modules['git_ops'] = MagicMock()

sys.modules['backend.os_agent'] = MagicMock()
sys.modules['os_agent'] = MagicMock()

sys.modules['backend.task_manager'] = MagicMock()
sys.modules['task_manager'] = MagicMock()

sys.modules['backend.project_manager'] = MagicMock()
sys.modules['project_manager'] = MagicMock()

sys.modules['backend.giphy_client'] = MagicMock()
sys.modules['giphy_client'] = MagicMock()
sys.modules['giphy_client.apis.default_api'] = MagicMock()
sys.modules['giphy_client.api_client'] = MagicMock()

# Mock dotenv
sys.modules['dotenv'] = MagicMock()

# Mock time_utils if needed (it might be imported by ada)
# ada.py does: from time_utils import set_time_format_tool...
# If time_utils exists and doesn't have side effects, we might not need to mock it.
# But let's check if it exists.
try:
    import backend.time_utils
except ImportError:
    # If not found or fails, mock it
    sys.modules['backend.time_utils'] = MagicMock()
    sys.modules['time_utils'] = MagicMock()

# Mock cv2 specifically
mock_cv2 = MagicMock()
sys.modules['cv2'] = mock_cv2
sys.modules['PIL'] = MagicMock()
sys.modules['PIL.Image'] = MagicMock()
sys.modules['mss'] = MagicMock()

# Import AudioLoop now that mocks are in place
from backend.ada import AudioLoop

# Test Class
class TestVisionPipeline(unittest.TestCase):
    def setUp(self):
        # Setup Mock Camera
        self.mock_cap = MagicMock()
        mock_cv2.VideoCapture.return_value = self.mock_cap

        # Fake frame: 100x100 RGB
        self.fake_frame_data = b'fake_image_data'
        self.mock_cap.read.return_value = (True, "fake_frame_object")

        # Mock PIL Image processing
        mock_pil_image = MagicMock()
        sys.modules['PIL.Image'].fromarray.return_value = mock_pil_image

        # Mock saving to bytes
        def save_side_effect(fp, format):
            fp.write(self.fake_frame_data)
        mock_pil_image.save.side_effect = save_side_effect

    def test_get_frames_updates_payload(self):
        async def run_test():
            # Init Loop
            loop = AudioLoop(video_mode="camera")
            loop.out_queue = asyncio.Queue()
            loop.paused = False

            # Start get_frames
            task = asyncio.create_task(loop.get_frames())

            # Allow loop to run for > 1 second (get_frames sleeps for 1s)
            # We need at least 2 iterations to be sure
            await asyncio.sleep(1.5)

            # Stop
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

            # 1. Verify VideoCapture called with 0 (not CAP_AVFOUNDATION)
            args, kwargs = mock_cv2.VideoCapture.call_args
            print(f"VideoCapture called with: {args}")
            # Should be (0,) or (0, something) if I missed something, but I changed it to (0).
            self.assertEqual(args[0], 0)

            # 2. Verify _latest_image_payload is updated
            print(f"Latest Payload: {loop._latest_image_payload}")
            self.assertIsNotNone(loop._latest_image_payload)
            self.assertEqual(loop._latest_image_payload['mime_type'], "image/jpeg")

            # 3. Verify Queue has frames
            q_size = loop.out_queue.qsize()
            print(f"Queue Size: {q_size}")
            self.assertTrue(q_size >= 1)

        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()
