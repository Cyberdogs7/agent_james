import httpx
import json

class GitHubClient:
    def __init__(self, token):
        self.token = token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

    async def _request(self, method, endpoint, **kwargs):
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method,
                    f"{self.base_url}{endpoint}",
                    headers=self.headers,
                    **kwargs
                )
                response.raise_for_status()
                if response.status_code == 204:
                    return True
                return response.json()
            except httpx.HTTPStatusError as e:
                print(f"[GitHubClient] HTTP Error {e.response.status_code}: {e.response.text}")
                return None
            except Exception as e:
                print(f"[GitHubClient] Request Error: {e}")
                return None

    async def get_repo_details(self, owner, repo):
        return await self._request("GET", f"/repos/{owner}/{repo}")

    async def get_branches(self, owner, repo):
        # Returns list of dicts: {name: "", commit: {sha: "", url: ""}}
        return await self._request("GET", f"/repos/{owner}/{repo}/branches")

    async def compare_commits(self, owner, repo, base, head):
        # Returns {status: "ahead|behind", ahead_by: N, behind_by: N, ...}
        return await self._request("GET", f"/repos/{owner}/{repo}/compare/{base}...{head}")

    async def merge_branch(self, owner, repo, base, head, message=None):
        data = {
            "base": base,
            "head": head,
            "commit_message": message or f"Merge {head} into {base}"
        }
        return await self._request("POST", f"/repos/{owner}/{repo}/merges", json=data)

    async def get_commit(self, owner, repo, sha):
        return await self._request("GET", f"/repos/{owner}/{repo}/commits/{sha}")

    async def delete_branch(self, owner, repo, branch_name):
        return await self._request("DELETE", f"/repos/{owner}/{repo}/git/refs/heads/{branch_name}")

    async def list_pull_requests(self, owner, repo, state="open"):
        return await self._request("GET", f"/repos/{owner}/{repo}/pulls", params={"state": state})

    async def merge_pull_request(self, owner, repo, pull_number, merge_method="merge"):
        # merge_method can be "merge", "squash", or "rebase"
        data = {"merge_method": merge_method}
        return await self._request("PUT", f"/repos/{owner}/{repo}/pulls/{pull_number}/merge", json=data)

    async def get_pull_request(self, owner, repo, pull_number):
        return await self._request("GET", f"/repos/{owner}/{repo}/pulls/{pull_number}")

    async def get_check_runs(self, owner, repo, ref):
        # Returns check runs for a specific commit ref
        return await self._request("GET", f"/repos/{owner}/{repo}/commits/{ref}/check-runs")

    async def get_commit_status(self, owner, repo, ref):
        # Returns the combined status for a specific ref
        return await self._request("GET", f"/repos/{owner}/{repo}/commits/{ref}/status")
