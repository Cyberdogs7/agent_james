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
            # Get the project root (one level up from backend)
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                cwd=project_root
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            self._log(f"[UPDATE_AGENT] Error running git command {command}: {e}")
            self._log(f"[UPDATE_AGENT] Stderr: {e.stderr}")
            return None

    async def check_for_updates(self):
        """Checks for updates from the GitHub repository."""
        self._log("[UPDATE_AGENT] Fetching remote updates...")
        fetch_result = await asyncio.to_thread(self._run_git_command, ["git", "fetch", "--all"])
        
        if fetch_result is None:
             return "Unable to fetch updates from the remote repository."

        self._log("[UPDATE_AGENT] Checking for differences...")
        
        # Get current branch name
        current_branch = await asyncio.to_thread(self._run_git_command, ["git", "rev-parse", "--abbrev-ref", "HEAD"])
        if not current_branch:
            return "Unable to determine current branch."

        local_hash = await asyncio.to_thread(self._run_git_command, ["git", "rev-parse", "HEAD"])
        
        # Try to find the upstream branch
        remote_branch = await asyncio.to_thread(self._run_git_command, ["git", "rev-parse", "--abbrev-ref", "@{u}"])
        
        remote_hash = None
        if not remote_branch:
            # Fallback to origin/master or origin/main if upstream is not set
            self._log(f"[UPDATE_AGENT] Upstream not set for branch {current_branch}, trying defaults...")
            for fallback in ["origin/master", "origin/main"]:
                remote_hash = await asyncio.to_thread(self._run_git_command, ["git", "rev-parse", fallback])
                if remote_hash:
                    remote_branch = fallback
                    break
        else:
            remote_hash = await asyncio.to_thread(self._run_git_command, ["git", "rev-parse", remote_branch])

        if not remote_hash:
            return "Unable to determine remote version."

        if local_hash == remote_hash:
            return "You are already on the latest version."
        else:
            return f"A new version is available on {remote_branch}. You can apply the update now."

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
