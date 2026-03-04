import sys
import os
import asyncio
import unittest
from unittest.mock import MagicMock, patch

# Ensure backend can be imported
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# 1. Mock Heavy Dependencies & Agents *before* importing ada
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

sys.modules['dotenv'] = MagicMock()

try:
    import backend.time_utils
except ImportError:
    sys.modules['backend.time_utils'] = MagicMock()
    sys.modules['time_utils'] = MagicMock()

# Mock cv2 specifically
mock_cv2 = MagicMock()
sys.modules['cv2'] = mock_cv2
# Note: PIL might still be imported by other modules, but ada.py no longer uses it for vision.
# We mock it just in case.
sys.modules['PIL'] = MagicMock()
sys.modules['PIL.Image'] = MagicMock()
sys.modules['mss'] = MagicMock()
sys.modules['numpy'] = MagicMock()

# Import AudioLoop now that mocks are in place
from backend.ada import AudioLoop

# Test Class
class TestVisionPipeline(unittest.TestCase):
    def setUp(self):
        # Setup Mock Camera
        self.mock_cap = MagicMock()
        mock_cv2.VideoCapture.return_value = self.mock_cap

        # Fake frame
        self.fake_frame = MagicMock()
        self.fake_frame.shape = (100, 100, 3)
        self.mock_cap.read.return_value = (True, self.fake_frame)

        # Mock cv2.imencode
        mock_cv2.imencode.return_value = (True, b'fake_jpeg_bytes')

        # Mock cv2.resize
        mock_cv2.resize.return_value = self.fake_frame

        # Mock cv2 constants
        mock_cv2.INTER_AREA = 1
        mock_cv2.IMWRITE_JPEG_QUALITY = 1
        mock_cv2.COLOR_BGRA2BGR = 1

    def test_video_loop_updates_payload(self):
        async def run_test():
            # Init Loop
            loop = AudioLoop(video_mode="camera")
            loop.out_queue = asyncio.Queue()
            loop.paused = False

            # Start video_loop (renamed from get_frames in previous versions likely)
            task = asyncio.create_task(loop.video_loop())

            # Mock the read function of the returned VideoCapture to return a tuple
            mock_cap = mock_cv2.VideoCapture.return_value
            mock_cap.read.return_value = (True, MagicMock(shape=(100, 100, 3)))
            mock_cap.isOpened.return_value = True

            # Allow loop to run for > 1 second
            await asyncio.sleep(1.5)

            # Stop
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

            # 1. Verify VideoCapture called
            args, kwargs = mock_cv2.VideoCapture.call_args
            print(f"VideoCapture called with: {args}")
            self.assertEqual(args[0], 0)

            # 2. Verify _latest_image_payload is updated
            print(f"Latest Payload: {loop._latest_image_payload}")
            self.assertIsNotNone(loop._latest_image_payload)
            self.assertEqual(loop._latest_image_payload['mime_type'], "image/jpeg")

            # 3. Verify imencode was called
            self.assertTrue(mock_cv2.imencode.called)

            # 4. Verify Queue has frames
            q_size = loop.out_queue.qsize()
            print(f"Queue Size: {q_size}")
            self.assertTrue(q_size >= 1)

        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()
