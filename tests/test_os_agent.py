import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Ensure backend can be imported
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.os_agent import OSAgent

class TestOSAgent(unittest.TestCase):
    def setUp(self):
        self.agent = OSAgent()

    @patch('backend.os_agent.sys.platform', 'darwin')
    @patch('subprocess.Popen')
    def test_launch_app_mac(self, mock_popen):
        self.agent.platform = 'darwin'
        result = self.agent.launch_app("Calculator")
        mock_popen.assert_called_with(["open", "-a", "Calculator"])
        self.assertIn("Launched Calculator", result)

    @patch('backend.os_agent.sys.platform', 'win32')
    @patch('subprocess.Popen')
    def test_launch_app_windows(self, mock_popen):
        self.agent.platform = 'win32'
        result = self.agent.launch_app("Notepad")
        mock_popen.assert_called_with('start "" "Notepad"', shell=True)
        self.assertIn("Launched Notepad", result)

    @patch('backend.os_agent.sys.platform', 'darwin')
    @patch('subprocess.run')
    def test_set_volume_mac(self, mock_run):
        self.agent.platform = 'darwin'
        self.agent.set_volume(50)
        mock_run.assert_called_with(["osascript", "-e", "set volume output volume 50"])

    @patch('backend.os_agent.sys.platform', 'darwin')
    @patch('subprocess.run')
    def test_mute_mac(self, mock_run):
        self.agent.platform = 'darwin'
        self.agent.mute()
        mock_run.assert_called_with(["osascript", "-e", "set volume output muted true"])

    @patch('backend.os_agent.sys.platform', 'darwin')
    @patch('subprocess.run')
    def test_lock_screen_mac(self, mock_run):
        self.agent.platform = 'darwin'
        self.agent.lock_screen()
        mock_run.assert_called_with(["pmset", "displaysleepnow"])

if __name__ == '__main__':
    unittest.main()
