import httpx
import os
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
