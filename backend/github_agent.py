import json
try:
    from backend.github_client import GitHubClient
except ImportError:
    from github_client import GitHubClient

class GitHubAgent:
    def __init__(self, project_manager):
        self.project_manager = project_manager

    def _get_client(self):
        token = self.project_manager.get_github_token()
        if not token:
            return None
        return GitHubClient(token)

    async def get_repo_details(self, owner, repo):
        client = self._get_client()
        if not client:
            return "GitHub token not found. Please add it to your settings."
        res = await client.get_repo_details(owner, repo)
        if not res:
            return f"Failed to retrieve repository details for '{owner}/{repo}'."
        return f"Repository: {res.get('full_name')}\nDescription: {res.get('description')}\nStars: {res.get('stargazers_count')}\nDefault Branch: {res.get('default_branch')}\nURL: {res.get('html_url')}"

    async def list_branches(self, owner, repo):
        client = self._get_client()
        if not client:
            return "GitHub token not found. Please add it to your settings."
        res = await client.get_branches(owner, repo)
        if not res:
            return f"Failed to retrieve branches for '{owner}/{repo}'."
        branches = [b.get("name") for b in res]
        return f"Branches in '{owner}/{repo}': " + ", ".join(branches)

    async def compare_commits(self, owner, repo, base, head):
        client = self._get_client()
        if not client:
            return "GitHub token not found. Please add it to your settings."
        res = await client.compare_commits(owner, repo, base, head)
        if not res:
            return f"Failed to compare commits {base}...{head}."
        return f"Status: {res.get('status')}\nAhead by: {res.get('ahead_by')}\nBehind by: {res.get('behind_by')}\nTotal Commits: {res.get('total_commits')}"

    async def merge_branch(self, owner, repo, base, head, message=None):
        client = self._get_client()
        if not client:
            return "GitHub token not found. Please add it to your settings."
        res = await client.merge_branch(owner, repo, base, head, message)
        if not res:
            return f"Failed to merge '{head}' into '{base}'."
        return f"Merged successfully. Commit SHA: {res.get('sha')}\nMessage: {res.get('commit', {}).get('message', '')}"

    async def get_commit(self, owner, repo, sha):
        client = self._get_client()
        if not client:
            return "GitHub token not found. Please add it to your settings."
        res = await client.get_commit(owner, repo, sha)
        if not res:
            return f"Failed to retrieve commit '{sha}'."
        commit_info = res.get("commit", {})
        author = commit_info.get("author", {})
        return f"Commit: {res.get('sha')}\nAuthor: {author.get('name')} <{author.get('email')}>\nDate: {author.get('date')}\nMessage: {commit_info.get('message')}"

    async def delete_branch(self, owner, repo, branch_name):
        client = self._get_client()
        if not client:
            return "GitHub token not found. Please add it to your settings."
        res = await client.delete_branch(owner, repo, branch_name)
        if res:
            return f"Successfully deleted branch '{branch_name}'."
        return f"Failed to delete branch '{branch_name}'."

    async def list_pull_requests(self, owner, repo, state="open"):
        client = self._get_client()
        if not client:
            return "GitHub token not found. Please add it to your settings."
        res = await client.list_pull_requests(owner, repo, state)
        if res is None:
            return f"Failed to list pull requests for '{owner}/{repo}'."
        if not res:
            return f"No {state} pull requests found for '{owner}/{repo}'."
        
        lines = []
        for pr in res:
            lines.append(f"PR #{pr.get('number')}: {pr.get('title')} by {pr.get('user', {}).get('login')} (State: {pr.get('state')}) - {pr.get('html_url')}")
        return f"Pull Requests ({state}):\n" + "\n".join(lines)

    async def get_pull_request(self, owner, repo, pull_number):
        client = self._get_client()
        if not client:
            return "GitHub token not found. Please add it to your settings."
        res = await client.get_pull_request(owner, repo, pull_number)
        if not res:
            return f"Failed to retrieve Pull Request #{pull_number}."
        
        return (f"PR #{res.get('number')}: {res.get('title')}\n"
                f"State: {res.get('state')} (Merged: {res.get('merged')})\n"
                f"Author: {res.get('user', {}).get('login')}\n"
                f"Base Branch: {res.get('base', {}).get('ref')}\n"
                f"Head Branch: {res.get('head', {}).get('ref')}\n"
                f"Body: {res.get('body') or 'No description'}\n"
                f"URL: {res.get('html_url')}")

    async def merge_pull_request(self, owner, repo, pull_number, merge_method="merge"):
        client = self._get_client()
        if not client:
            return "GitHub token not found. Please add it to your settings."
        res = await client.merge_pull_request(owner, repo, pull_number, merge_method)
        if res and res.get("merged"):
            return f"Successfully merged PR #{pull_number}."
        elif res:
            msg = res.get("message", "Unknown error")
            return f"Failed to merge PR #{pull_number}: {msg}"
        return f"Failed to merge PR #{pull_number}: Network or API error."

    async def get_check_runs(self, owner, repo, ref):
        client = self._get_client()
        if not client:
            return "GitHub token not found. Please add it to your settings."
        res = await client.get_check_runs(owner, repo, ref)
        if not res:
            return f"Failed to retrieve check runs for ref '{ref}'."
        
        runs = res.get("check_runs", [])
        if not runs:
            return f"No check runs found for ref '{ref}'."
        
        lines = []
        for run in runs:
            lines.append(f"- {run.get('name')}: {run.get('status')} / {run.get('conclusion')} ({run.get('html_url')})")
        return f"Check Runs for {ref}:\n" + "\n".join(lines)

    async def get_commit_status(self, owner, repo, ref):
        client = self._get_client()
        if not client:
            return "GitHub token not found. Please add it to your settings."
        res = await client.get_commit_status(owner, repo, ref)
        if not res:
            return f"Failed to retrieve commit status for ref '{ref}'."
        
        state = res.get("state", "unknown")
        statuses = res.get("statuses", [])
        lines = [f"Combined State: {state}"]
        for st in statuses:
            lines.append(f"- {st.get('context')}: {st.get('state')} ({st.get('description')})")
        return f"Commit Status for {ref}:\n" + "\n".join(lines)

    async def create_pull_request(self, owner, repo, title, head, base, body=None, draft=False):
        client = self._get_client()
        if not client:
            return "GitHub token not found. Please add it to your settings."
        res = await client.create_pull_request(owner, repo, title, head, base, body, draft)
        if not res:
            return f"Failed to create Pull Request '{title}'."
        if "number" in res:
            return f"Successfully created PR #{res.get('number')}: {res.get('title')}\nURL: {res.get('html_url')}"
        msg = res.get("message", "Unknown error")
        return f"Failed to create Pull Request: {msg}"

    async def list_issues(self, owner, repo, state="open", assignee=None, creator=None, mentioned=None, labels=None):
        client = self._get_client()
        if not client:
            return "GitHub token not found. Please add it to your settings."
        res = await client.list_issues(owner, repo, state, assignee, creator, mentioned, labels)
        if res is None:
            return f"Failed to list issues for '{owner}/{repo}'."
        if not res:
            return f"No {state} issues found for '{owner}/{repo}'."
        
        lines = []
        for issue in res:
            # GitHub issues endpoint can also return PRs. Let's filter out if needed, or specify
            is_pr = "pull_request" in issue
            type_str = "PR" if is_pr else "Issue"
            lines.append(f"{type_str} #{issue.get('number')}: {issue.get('title')} by {issue.get('user', {}).get('login')} (State: {issue.get('state')}) - {issue.get('html_url')}")
        return f"Issues/PRs ({state}):\n" + "\n".join(lines)

    async def get_issue(self, owner, repo, issue_number):
        client = self._get_client()
        if not client:
            return "GitHub token not found. Please add it to your settings."
        res = await client.get_issue(owner, repo, issue_number)
        if not res:
            return f"Failed to retrieve Issue #{issue_number}."
        
        return (f"Issue #{res.get('number')}: {res.get('title')}\n"
                f"State: {res.get('state')}\n"
                f"Author: {res.get('user', {}).get('login')}\n"
                f"Labels: {', '.join([l.get('name') for l in res.get('labels', [])]) or 'None'}\n"
                f"Body: {res.get('body') or 'No description'}\n"
                f"URL: {res.get('html_url')}")

    async def create_issue(self, owner, repo, title, body=None, assignees=None, labels=None):
        client = self._get_client()
        if not client:
            return "GitHub token not found. Please add it to your settings."
        res = await client.create_issue(owner, repo, title, body, assignees, labels)
        if not res:
            return f"Failed to create Issue '{title}'."
        if "number" in res:
            return f"Successfully created Issue #{res.get('number')}: {res.get('title')}\nURL: {res.get('html_url')}"
        msg = res.get("message", "Unknown error")
        return f"Failed to create Issue: {msg}"

    async def create_issue_comment(self, owner, repo, issue_number, body):
        client = self._get_client()
        if not client:
            return "GitHub token not found. Please add it to your settings."
        res = await client.create_issue_comment(owner, repo, issue_number, body)
        if not res:
            return f"Failed to comment on Issue #{issue_number}."
        if "id" in res:
            return f"Successfully added comment on Issue #{issue_number} (Comment ID: {res.get('id')})."
        msg = res.get("message", "Unknown error")
        return f"Failed to comment on Issue: {msg}"
