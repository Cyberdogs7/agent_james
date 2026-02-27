import sys
import subprocess
import logging
import shutil
import os
import ctypes

class OSAgent:
    def __init__(self):
        self.platform = sys.platform
        self.logger = logging.getLogger("OSAgent")
        self.logger.setLevel(logging.INFO)

    def launch_app(self, app_name):
        """Launches an application."""
        self.logger.info(f"Launching app: {app_name}")
        try:
            if self.platform == "win32":
                # Use os.startfile for better safety than shell=True, if possible.
                try:
                    os.startfile(app_name)
                    return f"Launched {app_name}"
                except FileNotFoundError:
                    # Fallback to shell execution if not found directly
                    subprocess.Popen(f'start "" "{app_name}"', shell=True)
                    return f"Launched {app_name} (via shell)"
            elif self.platform == "darwin":
                subprocess.Popen(["open", "-a", app_name])
                return f"Launched {app_name}"
            elif self.platform == "linux":
                if shutil.which(app_name):
                    subprocess.Popen([app_name], start_new_session=True)
                    return f"Launched {app_name}"
                else:
                    subprocess.Popen(app_name, shell=True, start_new_session=True)
                    return f"Attempted to launch {app_name}"
            else:
                return "Platform not supported"
        except Exception as e:
            self.logger.error(f"Failed to launch {app_name}: {e}")
            return f"Failed to launch {app_name}: {str(e)}"

    def _windows_send_key(self, vk_code):
        """Sends a key press using ctypes user32.keybd_event or SendInput."""
        # Simple keybd_event approach (deprecated but reliable for simple media keys)
        # 0 = KeyDown, 2 = KeyUp
        user32 = ctypes.windll.user32
        user32.keybd_event(vk_code, 0, 0, 0)
        user32.keybd_event(vk_code, 0, 2, 0)

    def set_volume(self, level):
        """Sets volume (0-100)."""
        self.logger.info(f"Setting volume to: {level}")
        try:
            level = max(0, min(100, int(level)))
            if self.platform == "win32":
                # VK_VOLUME_MUTE = 0xAD
                # VK_VOLUME_DOWN = 0xAE
                # VK_VOLUME_UP = 0xAF

                # Reset to 0 (50 presses down)
                for _ in range(50):
                    self._windows_send_key(0xAE)

                # Set to level (steps of 2 typically)
                steps = int(level / 2)
                for _ in range(steps):
                    self._windows_send_key(0xAF)

                return f"Set volume to approx {level}%"

            elif self.platform == "darwin":
                subprocess.run(["osascript", "-e", f"set volume output volume {level}"])
                return f"Set volume to {level}%"
            elif self.platform == "linux":
                if shutil.which("pactl"):
                    subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{level}%"])
                    return f"Set volume to {level}%"
                elif shutil.which("amixer"):
                     subprocess.run(["amixer", "sset", "Master", f"{level}%"])
                     return f"Set volume to {level}%"
                return "No audio control utility found (pactl/amixer)"
        except Exception as e:
            return f"Error setting volume: {str(e)}"

    def _set_mute_state(self, muted: bool):
        """Sets the system mute state."""
        state_str = "Muted" if muted else "Unmuted"
        try:
            if self.platform == "win32":
                # VK_VOLUME_MUTE = 0xAD (Toggle) - Windows doesn't easily support absolute mute/unmute via keys
                # Best effort: Send toggle. Ideally we would check state first but that requires COM.
                self._windows_send_key(0xAD)
                return "Muted/Unmuted (Toggle)"
            elif self.platform == "darwin":
                val = "true" if muted else "false"
                subprocess.run(["osascript", "-e", f"set volume output muted {val}"])
                return state_str
            elif self.platform == "linux":
                val = "1" if muted else "0"
                amixer_val = "mute" if muted else "unmute"
                if shutil.which("pactl"):
                    subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", val])
                elif shutil.which("amixer"):
                    subprocess.run(["amixer", "sset", "Master", amixer_val])
                return state_str
        except Exception as e:
             return f"Error setting mute state: {str(e)}"

    def lock_screen(self):
        """Locks the screen."""
        self.logger.info("Locking screen")
        try:
            if self.platform == "win32":
                subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
                return "Screen locked"
            elif self.platform == "darwin":
                # MacOS High Sierra+
                subprocess.run(["pmset", "displaysleepnow"])
                return "Screen locked"
            elif self.platform == "linux":
                if shutil.which("xdg-screensaver"):
                    subprocess.run(["xdg-screensaver", "lock"])
                elif shutil.which("gnome-screensaver-command"):
                    subprocess.run(["gnome-screensaver-command", "-l"])
                else:
                     return "No lock command found"
                return "Screen locked"
        except Exception as e:
            return f"Error locking screen: {str(e)}"

    def sleep(self):
        """Puts the system to sleep."""
        self.logger.info("Sleeping system")
        try:
            if self.platform == "win32":
                # Hibernate=0 -> Sleep
                subprocess.run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
                return "System sleeping"
            elif self.platform == "darwin":
                subprocess.run(["pmset", "sleepnow"])
                return "System sleeping"
            elif self.platform == "linux":
                subprocess.run(["systemctl", "suspend"])
                return "System sleeping"
        except Exception as e:
            return f"Error sleeping: {str(e)}"

    def control(self, action, value=None):
        """Dispatches control actions to the appropriate method."""
        if action == "launch":
            return self.launch_app(value)
        elif action == "set_volume":
            return self.set_volume(value)
        elif action == "mute":
            return self._set_mute_state(True)
        elif action == "unmute":
            return self._set_mute_state(False)
        elif action == "lock_screen":
            return self.lock_screen()
        elif action == "sleep":
            return self.sleep()
        return "Unknown action."
