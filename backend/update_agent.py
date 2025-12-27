import asyncio
import os
import subprocess

class UpdateAgent:
    def __init__(self, session=None):
        self.session = session
        self.include_raw = os.environ.get("INCLUDE_RAW_LOGS", "False") == "True"
        self.sio = None

    def _log(self, *args, **kwargs):
        if self.include_raw:
            print(*args, **kwargs)

    def _run_git_command(self, command):
        """Runs a git command and returns its output."""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            self._log(f"[UPDATE_AGENT] Error running git command: {e}")
            self._log(f"[UPDATE_AGENT] Stderr: {e.stderr}")
            return None

    async def check_for_updates(self):
        """Checks for updates from the GitHub repository."""
        self._log("[UPDATE_AGENT] Fetching remote updates...")
        await asyncio.to_thread(self._run_git_command, ["git", "fetch"])

        self._log("[UPDATE_AGENT] Checking for differences...")
        local_hash = await asyncio.to_thread(self._run_git_command, ["git", "rev-parse", "HEAD"])
        remote_hash = await asyncio.to_thread(self._run_git_command, ["git", "rev-parse", "origin/main"])

        if local_hash == remote_hash:
            return "You are already on the latest version."
        else:
            return "A new version is available. You can apply the update now."

    async def apply_update(self):
        """Applies the latest updates and prepares for restart."""
        self._log("[UPDATE_AGENT] Pulling latest changes...")
        pull_result = await asyncio.to_thread(self._run_git_command, ["git", "pull"])

        if pull_result is None:
            return "Error applying update. Please check the logs."

        self._log("[UPDATE_AGENT] Update complete. Notifying server to restart...")
        if self.sio:
            await self.sio.emit('restart_request')

        return "Update applied successfully. The application will restart shortly."
