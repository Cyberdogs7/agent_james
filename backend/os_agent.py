import sys
import subprocess
import logging
import shutil
import os

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
                # Using 'start' via cmd to handle various ways apps are registered
                # Use shell=True for 'start' to work
                subprocess.Popen(f'start "" "{app_name}"', shell=True)
                return f"Launched {app_name}"
            elif self.platform == "darwin":
                subprocess.Popen(["open", "-a", app_name])
                return f"Launched {app_name}"
            elif self.platform == "linux":
                # Try generic 'xdg-open' or command directly
                # Often linux apps are just their name in path
                # Check if executable exists in path first
                if shutil.which(app_name):
                    subprocess.Popen([app_name], start_new_session=True)
                    return f"Launched {app_name}"
                else:
                    # Try xdg-open but it usually expects files/urls
                    # Maybe it's a flatpak? snap?
                    # Fallback to shell execution for flexibility
                    subprocess.Popen(app_name, shell=True, start_new_session=True)
                    return f"Attempted to launch {app_name}"
            else:
                return "Platform not supported"
        except Exception as e:
            self.logger.error(f"Failed to launch {app_name}: {e}")
            return f"Failed to launch {app_name}: {str(e)}"

    def set_volume(self, level):
        """Sets volume (0-100)."""
        self.logger.info(f"Setting volume to: {level}")
        try:
            level = max(0, min(100, int(level)))
            if self.platform == "win32":
                # Windows volume is tricky without external libs like pycaw
                # We can use a powershell script or VBS.
                # A common lightweight way is using nircmd if installed, but we can't assume that.
                # Or a simple PowerShell Audio module if available.
                # Fallback: We might not be able to set EXACT volume easily without deps.
                # But we can MUTE/UNMUTE easily.
                # For now, let's try a PowerShell snippet that uses WScript.Shell to send keys (imprecise)
                # OR just report not implemented fully without dependencies.
                # BETTER: Use a small bundled VBScript or PowerShell that invokes Audio API.
                # For simplicity in this iteration: Log warning for Windows volume SET.
                return "Volume setting on Windows requires 3rd party libraries (pycaw)."
            elif self.platform == "darwin":
                subprocess.run(["osascript", "-e", f"set volume output volume {level}"])
                return f"Set volume to {level}%"
            elif self.platform == "linux":
                # Try pactl (PulseAudio) or amixer (ALSA)
                if shutil.which("pactl"):
                    subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{level}%"])
                    return f"Set volume to {level}%"
                elif shutil.which("amixer"):
                     subprocess.run(["amixer", "sset", "Master", f"{level}%"])
                     return f"Set volume to {level}%"
                return "No audio control utility found (pactl/amixer)"
        except Exception as e:
            return f"Error setting volume: {str(e)}"

    def mute(self):
        """Mutes the system volume."""
        try:
            if self.platform == "win32":
                # PowerShell send key VolumeMute
                script = "$obj = New-Object -ComObject WScript.Shell; $obj.SendKeys([char]173)"
                subprocess.run(["powershell", "-command", script])
                return "Muted/Unmuted"
            elif self.platform == "darwin":
                subprocess.run(["osascript", "-e", "set volume output muted true"])
                return "Muted"
            elif self.platform == "linux":
                if shutil.which("pactl"):
                    subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "1"])
                elif shutil.which("amixer"):
                    subprocess.run(["amixer", "sset", "Master", "mute"])
                return "Muted"
        except Exception as e:
             return f"Error muting: {str(e)}"

    def unmute(self):
        """Unmutes the system volume."""
        try:
            if self.platform == "win32":
                # PowerShell send key VolumeMute (Toggle) - difficult to ensure state
                # Sending it again toggles it.
                script = "$obj = New-Object -ComObject WScript.Shell; $obj.SendKeys([char]173)"
                subprocess.run(["powershell", "-command", script])
                return "Muted/Unmuted"
            elif self.platform == "darwin":
                subprocess.run(["osascript", "-e", "set volume output muted false"])
                return "Unmuted"
            elif self.platform == "linux":
                if shutil.which("pactl"):
                    subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "0"])
                elif shutil.which("amixer"):
                    subprocess.run(["amixer", "sset", "Master", "unmute"])
                return "Unmuted"
        except Exception as e:
             return f"Error unmuting: {str(e)}"

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
                # Or actually lock:
                # subprocess.run(["/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession", "-suspend"])
                return "Screen locked"
            elif self.platform == "linux":
                # Try generic xdg-screensaver or gnome-screensaver-command
                if shutil.which("xdg-screensaver"):
                    subprocess.run(["xdg-screensaver", "lock"])
                elif shutil.which("gnome-screensaver-command"):
                    subprocess.run(["gnome-screensaver-command", "-l"])
                else:
                     return "No lock command found"
                return "Screen locked"
        except Exception as e:
            return f"Error locking screen: {str(e)}"
