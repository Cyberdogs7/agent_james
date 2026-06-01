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

    @patch('backend.os_agent.shutil.which', return_value=None)
    @patch('backend.os_agent.sys.platform', 'linux')
    @patch('subprocess.Popen')
    def test_launch_app_linux_secure(self, mock_popen, mock_which):
        self.agent.platform = 'linux'
        result = self.agent.launch_app("gedit --new-window file.txt; rm -rf /")
        mock_popen.assert_called_with(["gedit", "--new-window", "file.txt;", "rm", "-rf", "/"], start_new_session=True)
        self.assertIn("Attempted to launch", result)

    @patch('backend.os_agent.sys.platform', 'win32')
    def test_launch_app_windows(self):
        # We need to manually mock os.startfile because it doesn't exist on linux
        with patch('backend.os_agent.os') as mock_os:
            self.agent.platform = 'win32'
            # Setup mock to simulate success
            mock_os.startfile = MagicMock()

            result = self.agent.launch_app("Notepad")

            mock_os.startfile.assert_called_with("Notepad")
            self.assertIn("Launched Notepad", result)

    @patch('backend.os_agent.sys.platform', 'win32')
    @patch('subprocess.Popen')
    def test_launch_app_windows_fallback(self, mock_popen):
        with patch('backend.os_agent.os') as mock_os:
            self.agent.platform = 'win32'
            # Setup mock to raise FileNotFoundError
            mock_os.startfile = MagicMock(side_effect=FileNotFoundError)

            result = self.agent.launch_app('Notepad "evil.exe"')

            mock_popen.assert_called_with(['cmd.exe', '/c', 'start', '""', 'Notepad "evil.exe"'])
            self.assertIn("Launched Notepad \"evil.exe\" (via shell)", result)

    @patch('backend.os_agent.sys.platform', 'linux')
    @patch('subprocess.Popen')
    def test_launch_app_linux_which(self, mock_popen):
        with patch('backend.os_agent.shutil.which', return_value="/usr/bin/calculator"):
            self.agent.platform = 'linux'
            result = self.agent.launch_app("calculator")
            mock_popen.assert_called_with(["calculator"], start_new_session=True)
            self.assertIn("Launched calculator", result)

    @patch('backend.os_agent.sys.platform', 'linux')
    @patch('subprocess.Popen')
    def test_launch_app_linux_fallback(self, mock_popen):
        with patch('backend.os_agent.shutil.which', return_value=None):
            self.agent.platform = 'linux'
            result = self.agent.launch_app('calculator --display "abc def"')
            mock_popen.assert_called_with(['calculator', '--display', 'abc def'], start_new_session=True)
            self.assertIn("Attempted to launch calculator --display \"abc def\"", result)

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
        self.agent._set_mute_state(True)
        mock_run.assert_called_with(["osascript", "-e", "set volume output muted true"])

    @patch('backend.os_agent.sys.platform', 'darwin')
    @patch('subprocess.run')
    def test_lock_screen_mac(self, mock_run):
        self.agent.platform = 'darwin'
        self.agent.lock_screen()
        mock_run.assert_called_with(["pmset", "displaysleepnow"])

    @patch('backend.os_agent.sys.platform', 'darwin')
    @patch('subprocess.run')
    def test_sleep_mac(self, mock_run):
        self.agent.platform = 'darwin'
        self.agent.sleep()
        mock_run.assert_called_with(["pmset", "sleepnow"])

if __name__ == '__main__':
    unittest.main()
