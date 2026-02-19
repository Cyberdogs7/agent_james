import asyncio
from backend.git_ops import GitOps
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

    async def commit(self, message, repo_name=None):
        path = self._get_repo_path(repo_name)
        def _do_commit():
            success, msg = GitOps.commit_changes(path, message)
            return msg
        return await asyncio.to_thread(_do_commit)

    async def push(self, repo_name=None):
        path = self._get_repo_path(repo_name)
        def _do_push():
            success, msg = GitOps.push_changes(path)
            return msg
        return await asyncio.to_thread(_do_push)

    async def pull(self, repo_name=None):
        path = self._get_repo_path(repo_name)
        def _do_pull():
            success, msg = GitOps.pull_changes(path)
            return msg
        return await asyncio.to_thread(_do_pull)

    async def status(self, repo_name=None):
        path = self._get_repo_path(repo_name)
        def _do_status():
            current_branch = GitOps.get_current_branch(path)
            status = GitOps.get_status(path)
            last_commit = GitOps.get_last_commit_info(path)

            result_str = f"Status for '{path.name}':\n"
            result_str += f"Branch: {current_branch or 'Unknown'}\n"
            result_str += f"State: {'Dirty' if status else 'Clean'}\n"
            if status:
                result_str += f"Changes:\n{status}\n"
            if last_commit:
                result_str += f"Last Commit: {last_commit['hash']} - {last_commit['message']} ({last_commit['author']}, {last_commit['date']})"
            return result_str
        return await asyncio.to_thread(_do_status)

    async def merge(self, branch_name, repo_name=None):
        path = self._get_repo_path(repo_name)

        # Check if local repo exists
        if path.exists():
            def _do_local_merge():
                success, msg = GitOps.merge_branch(path, branch_name)
                return msg
            return await asyncio.to_thread(_do_local_merge)
        else:
            # Attempt Remote Merge
            token = self.project_manager.get_github_token()
            if token and repo_name:
                fleet = self.project_manager.load_fleet()
                target_repo = next((r for r in fleet if r['name'] == repo_name or f"{r['owner']}/{r['name']}" == repo_name), None)

                if target_repo:
                    client = GitHubClient(token)
                    # Fetch default branch
                    details = await client.get_repo_details(target_repo['owner'], target_repo['name'])
                    target_branch = details.get('default_branch', 'main') if details else 'main'

                    result = await client.merge_branch(target_repo['owner'], target_repo['name'], target_branch, branch_name)
                    if result:
                        return f"Merged {branch_name} into {target_branch} remotely."
                    else:
                        return "Remote merge failed."
                else:
                    return f"Repository '{repo_name}' not found locally or in fleet config."
            else:
                return "Repository path does not exist and no GitHub token available for remote merge."

    async def list_repos(self):
        def _do_list():
            repos = self.project_manager.list_git_projects()
            return f"Available Git Repositories: {', '.join(repos)}" if repos else "No git repositories found."
        return await asyncio.to_thread(_do_list)

    async def list_branches(self, repo_name=None):
        path = self._get_repo_path(repo_name)
        def _do_list():
            branches = GitOps.list_branches(path)
            return f"Branches in '{path.name}': {', '.join(branches)}" if branches else f"No branches found or failed to list branches for '{path.name}'."
        return await asyncio.to_thread(_do_list)

    async def fleet_status(self):
        def _do_fleet_status():
            repos = self.project_manager.list_git_projects()
            if not repos:
                return "No git repositories found."

            result_str = "Fleet Status Report:\n"
            for repo in repos:
                repo_path = self.project_manager.get_project_path(repo)
                current_branch = GitOps.get_current_branch(repo_path)
                status = GitOps.get_status(repo_path)
                last_commit = GitOps.get_last_commit_info(repo_path)

                result_str += f"--- {repo} ---\n"
                result_str += f"Branch: {current_branch or 'Unknown'}\n"
                result_str += f"Status: {'Dirty' if status else 'Clean'}\n"
                if last_commit:
                    result_str += f"Commit: {last_commit['message'][:50]}... ({last_commit['date']})\n"
                result_str += "\n"
            return result_str
        return await asyncio.to_thread(_do_fleet_status)

    async def sync_fleet(self, sources):
        def _do_sync():
            results, status = self.project_manager.sync_jules_repos(sources)
            if status == "AUTH_REQUIRED":
                return "GitHub Authentication Required."
            summary = ", ".join(results) if results else "All up to date."
            return f"Sync Complete: {summary}"

        return await asyncio.to_thread(_do_sync)

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
