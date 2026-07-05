import asyncio
import os

try:
    from backend.github_client import GitHubClient
except ImportError:
    from github_client import GitHubClient

class GitAgent:
    def __init__(self, project_manager):
        self.project_manager = project_manager

    def _get_repo_path(self, repo_name=None):
        if repo_name:
            return self.project_manager.get_project_path(repo_name)
        return self.project_manager.get_current_project_path()

    async def _run_git(self, args, cwd):
        """Helper to run git commands asynchronously."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", *args,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            return proc.returncode, stdout.decode().strip(), stderr.decode().strip()
        except Exception as e:
            return -1, "", str(e)

    async def init_git_repo(self, repo_path):
        """Initializes a git repository if one doesn't exist."""
        git_dir = os.path.join(repo_path, ".git")
        if not os.path.exists(git_dir):
            code, out, err = await self._run_git(["init"], cwd=repo_path)
            if code == 0:
                return True, f"Initialized git repo: {out}"
            return False, f"Git init failed: {err}"
        return True, "Git repo already initialized."

    async def stage_all(self, repo_path):
        """Stages all changes in the repo."""
        code, out, err = await self._run_git(["add", "."], cwd=repo_path)
        if code == 0:
            return True, "Staged all changes."
        return False, f"Git add failed: {err}"

    async def get_current_branch(self, repo_path):
        code, out, err = await self._run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path)
        if code == 0:
            return out
        return None

    async def get_branches_list(self, repo_path):
        code, out, err = await self._run_git(["branch", "--format=%(refname:short)"], cwd=repo_path)
        if code == 0:
            return out.split('\n') if out else []
        return []

    async def get_status_raw(self, repo_path):
        code, out, err = await self._run_git(["status", "--short"], cwd=repo_path)
        if code == 0:
            return out
        return "Failed to get status."

    async def get_last_commit_info(self, repo_path):
        # Format: hash|author|date|message
        code, out, err = await self._run_git(["log", "-1", "--format=%h|%an|%ar|%s"], cwd=repo_path)
        if code == 0 and out:
            parts = out.split('|', 3)
            if len(parts) == 4:
                return {
                    "hash": parts[0],
                    "author": parts[1],
                    "date": parts[2],
                    "message": parts[3]
                }
        return None

    async def commit_changes(self, repo_path, message):
        # -a to stage modified/deleted files
        code, out, err = await self._run_git(["commit", "-a", "-m", message], cwd=repo_path)
        if code == 0:
            return True, f"Committed changes: {out}"
        return False, f"Commit failed:\n{err}"

    async def push_changes(self, repo_path):
        code, out, err = await self._run_git(["push"], cwd=repo_path)
        if code == 0:
            return True, f"Successfully pushed changes.\n{out}"
        return False, f"Push failed:\n{err}"

    async def pull_changes(self, repo_path):
        code, out, err = await self._run_git(["pull"], cwd=repo_path)
        if code == 0:
            return True, f"Successfully pulled changes.\n{out}"
        return False, f"Pull failed:\n{err}"

    async def merge_branch_local(self, repo_path, branch_name):
        # Check if source branch exists
        branches = await self.get_branches_list(repo_path)
        if branch_name not in branches:
            return False, f"Branch '{branch_name}' does not exist."

        code, out, err = await self._run_git(["merge", branch_name], cwd=repo_path)
        if code == 0:
            return True, f"Successfully merged '{branch_name}'.\n{out}"
        return False, f"Merge failed:\n{err}"

    # --- Tool Facing Methods ---

    async def commit(self, message, repo_name=None):
        path = self._get_repo_path(repo_name)
        success, msg = await self.commit_changes(path, message)
        return msg

    async def push(self, repo_name=None):
        path = self._get_repo_path(repo_name)
        success, msg = await self.push_changes(path)
        return msg

    async def pull(self, repo_name=None):
        path = self._get_repo_path(repo_name)
        success, msg = await self.pull_changes(path)
        return msg

    async def status(self, repo_name=None):
        path = self._get_repo_path(repo_name)

        current_branch = await self.get_current_branch(path)
        status = await self.get_status_raw(path)
        last_commit = await self.get_last_commit_info(path)

        result_str = f"Status for '{path.name}':\n"
        result_str += f"Branch: {current_branch or 'Unknown'}\n"
        result_str += f"State: {'Dirty' if status else 'Clean'}\n"
        if status:
            result_str += f"Changes:\n{status}\n"
        if last_commit:
            result_str += f"Last Commit: {last_commit['hash']} - {last_commit['message']} ({last_commit['author']}, {last_commit['date']})"
        return result_str

    async def merge(self, branch_name, repo_name=None):
        path = self._get_repo_path(repo_name)
        fleet = self.project_manager.load_fleet()

        target_repo = None
        if repo_name:
            target_repo = next((r for r in fleet if r['name'] == repo_name or f"{r['owner']}/{r['name']}" == repo_name), None)
        else:
            target_repo = next((r for r in fleet if r['name'] == path.name), None)

        auto_merge_enabled = target_repo.get('auto_merge_enabled', False) if target_repo else False

        if auto_merge_enabled:
            token = self.project_manager.get_github_token()
            if token and target_repo:
                client = GitHubClient(token)
                details = await client.get_repo_details(target_repo['owner'], target_repo['name'])
                target_branch = details.get('default_branch', 'main') if details else 'main'

                result = await client.merge_branch(target_repo['owner'], target_repo['name'], target_branch, branch_name)
                if result:
                    return f"Merged {branch_name} into {target_branch} remotely using GitHub token."
                else:
                    return f"Remote merge failed for {branch_name} into {target_branch}."
            else:
                return "Auto-merge is enabled, but GitHub token is missing or repository info not found."

        if path.exists():
            success, msg = await self.merge_branch_local(path, branch_name)
            return msg
        else:
            return "Auto-merge is disabled for this repository. Cannot perform remote merge, and local repository not found."

    async def list_repos(self):
        repos = self.project_manager.list_git_projects()
        return f"Available Git Repositories: {', '.join(repos)}" if repos else "No git repositories found."

    async def list_branches(self, repo_name=None):
        """Tool-facing method that returns a formatted string."""
        path = self._get_repo_path(repo_name)
        branches = await self.get_branches_list(path)
        return f"Branches in '{path.name}': {', '.join(branches)}" if branches else f"No branches found or failed to list branches for '{path.name}'."

    async def fleet_status(self):
        repos = self.project_manager.list_git_projects()
        if not repos:
            return "No git repositories found."

        result_str = "Fleet Status Report:\n"
        for repo in repos:
            repo_path = self.project_manager.get_project_path(repo)
            current_branch = await self.get_current_branch(repo_path)
            status = await self.get_status_raw(repo_path)
            last_commit = await self.get_last_commit_info(repo_path)

            result_str += f"--- {repo} ---\n"
            result_str += f"Branch: {current_branch or 'Unknown'}\n"
            result_str += f"Status: {'Dirty' if status else 'Clean'}\n"
            if last_commit:
                result_str += f"Commit: {last_commit['message'][:50]}... ({last_commit['date']})\n"
            result_str += "\n"
        return result_str

    async def sync_fleet(self, sources):
        return "Fleet sync is no longer available."

    async def merge_pull_request(self, owner, repo, pull_number, merge_method="merge"):
        token = self.project_manager.get_github_token()
        if not token:
            return "GitHub token not found. Please add it to your settings."

        client = GitHubClient(token)
        result = await client.merge_pull_request(owner, repo, pull_number, merge_method)

        if result and result.get("merged"):
            return f"Successfully merged PR #{pull_number}."
        elif result:
             msg = result.get("message", "Unknown error")
             return f"Failed to merge PR: {msg}"
        else:
            return "Failed to merge PR: Network or API error."
