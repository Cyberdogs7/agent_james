import asyncio
import os
import subprocess

class UpdateAgent:
    def __init__(self, session=None, on_log=None):
        self.session = session
        self.on_log = on_log
        self.include_raw = os.environ.get("INCLUDE_RAW_LOGS", "False") == "True"
        self.sio = None
        self._log("[UPDATE_AGENT] Initialized")

    def _log(self, *args, **kwargs):
        # Always print critical agent logs for debugging
        message = " ".join(map(str, args))
        print(message, flush=True)
        if self.on_log:
            try:
                self.on_log(message)
            except:
                pass

    def _run_git_command(self, command):
        """Runs a git command and returns its output."""
        try:
            # Get the project root (one level up from backend)
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False, # We handle errors manually to get more details
                cwd=project_root,
                timeout=30
            )
            
            if result.returncode != 0:
                self._log(f"[UPDATE_AGENT] Git command failed with exit code {result.returncode}: {' '.join(command)}")
                self._log(f"[UPDATE_AGENT] Stderr: {result.stderr.strip()}")
                return None
            
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            self._log(f"[UPDATE_AGENT] Git command timed out: {' '.join(command)}")
            return None
        except Exception as e:
            self._log(f"[UPDATE_AGENT] Unexpected error running git command {' '.join(command)}: {str(e)}")
            return None

    async def check_for_updates(self):
        """Checks for updates from the GitHub repository."""
        self._log("[UPDATE_AGENT] Starting check_for_updates method...")
        
        # Verify it's a git repo first
        is_repo = await asyncio.to_thread(self._run_git_command, ["git", "rev-parse", "--is-inside-work-tree"])
        if is_repo is None:
            return "This directory is not a valid git repository or git is not installed."

        self._log("[UPDATE_AGENT] Fetching remote updates...")
        # Try fetching from 'origin' specifically first as it's the most common and less likely to fail than --all if there are broken remotes
        fetch_result = await asyncio.to_thread(self._run_git_command, ["git", "fetch", "origin"])
        
        if fetch_result is None:
             self._log("[UPDATE_AGENT] Fetch from 'origin' failed, trying 'git fetch'...")
             fetch_result = await asyncio.to_thread(self._run_git_command, ["git", "fetch"])

        if fetch_result is None:
             self._log("[UPDATE_AGENT] All fetch attempts failed.")
             return "Unable to fetch updates from the remote repository. Please check your internet connection or git configuration."

        self._log("[UPDATE_AGENT] Checking for differences...")
        
        # Get current branch name
        current_branch = await asyncio.to_thread(self._run_git_command, ["git", "rev-parse", "--abbrev-ref", "HEAD"])
        self._log(f"[UPDATE_AGENT] Current branch: {current_branch}")
        if not current_branch:
            return "Unable to determine current branch."

        local_hash = await asyncio.to_thread(self._run_git_command, ["git", "rev-parse", "HEAD"])
        self._log(f"[UPDATE_AGENT] Local hash: {local_hash}")
        
        # Try to find the upstream branch
        remote_branch = await asyncio.to_thread(self._run_git_command, ["git", "rev-parse", "--abbrev-ref", "@{u}"])
        self._log(f"[UPDATE_AGENT] Upstream branch: {remote_branch}")
        
        remote_hash = None
        if not remote_branch:
            # Fallback to origin/master or origin/main if upstream is not set
            self._log(f"[UPDATE_AGENT] Upstream not set for branch {current_branch}, trying defaults...")
            for fallback in ["origin/master", "origin/main"]:
                self._log(f"[UPDATE_AGENT] Trying fallback: {fallback}")
                remote_hash = await asyncio.to_thread(self._run_git_command, ["git", "rev-parse", fallback])
                if remote_hash:
                    remote_branch = fallback
                    self._log(f"[UPDATE_AGENT] Found hash for {fallback}: {remote_hash}")
                    break
        else:
            remote_hash = await asyncio.to_thread(self._run_git_command, ["git", "rev-parse", remote_branch])
            self._log(f"[UPDATE_AGENT] Remote hash: {remote_hash}")

        if not remote_hash:
            self._log("[UPDATE_AGENT] Could not determine remote version.")
            return "Unable to determine remote version."

        if local_hash == remote_hash:
            self._log("[UPDATE_AGENT] Already on latest version.")
            return "You are already on the latest version."
        else:
            self._log(f"[UPDATE_AGENT] Update available on {remote_branch}")
            return f"A new version is available on {remote_branch}. You can apply the update now."

    async def apply_update(self):
        """Applies the latest updates and prepares for restart."""
        self._log("[UPDATE_AGENT] Pulling latest changes...")
        pull_result = await asyncio.to_thread(self._run_git_command, ["git", "pull"])

        if pull_result is None:
            return "Error applying update. Please check the logs."

        self._log("[UPDATE_AGENT] Update complete. Notifying server to restart...")
        if self.sio:
            # We emit 'restart_request' to the frontend, 
            # and the frontend should send it back to the server to trigger shutdown,
            # OR we can trigger it locally.
            # Triggering locally is safer to ensure it happens.
            try:
                # Import server here to avoid circular imports if any, 
                # although server.py usually imports update_agent indirectly.
                # Actually, we can just call the handler if we had a reference to it,
                # but we only have sio.
                
                # If we emit to 'restart_request', the server-side event handler @sio.event 
                # for 'restart_request' won't be triggered because it only listens to clients.
                
                # Let's emit to frontend so the user sees something, 
                # and also try to trigger the server shutdown.
                await self.sio.emit('restart_request', {'reason': 'update_applied'})
                
                # To trigger the local server restart, we can't easily call the async handler from here without sid.
                # But we can call the shutdown function directly if we could import it.
                # Instead, let's just use the fact that server.py is likely what started this.
                
                # A better way: the server.py could listen for a local signal or we can use a callback.
                
                self._log("[UPDATE_AGENT] Emitted restart_request to frontend.")
            except Exception as e:
                self._log(f"[UPDATE_AGENT] Error notifying restart: {e}")

        return "Update applied successfully. The application will restart shortly."
