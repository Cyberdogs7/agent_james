import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from backend.github_client import GitHubClient

import httpx

@pytest.fixture
def github_client():
    return GitHubClient("test_token")

def test_init(github_client):
    assert github_client.token == "test_token"
    assert github_client.base_url == "https://api.github.com"
    assert github_client.headers["Authorization"] == "Bearer test_token"
    assert github_client.headers["Accept"] == "application/vnd.github.v3+json"
    assert github_client.headers["X-GitHub-Api-Version"] == "2022-11-28"

@pytest.mark.asyncio
async def test_request_success(github_client):
    with patch("backend.github_client.httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value.__aenter__.return_value
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_client.request = AsyncMock(return_value=mock_response)

        result = await github_client._request("GET", "/test")
        assert result == {"success": True}
        mock_client.request.assert_called_once_with(
            "GET",
            "https://api.github.com/test",
            headers=github_client.headers
        )

@pytest.mark.asyncio
async def test_request_204(github_client):
    with patch("backend.github_client.httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value.__aenter__.return_value
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_client.request = AsyncMock(return_value=mock_response)

        result = await github_client._request("DELETE", "/test")
        assert result is True

@pytest.mark.asyncio
async def test_request_http_error(github_client, capsys):
    with patch("backend.github_client.httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value.__aenter__.return_value
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"

        # We need an exception that inherits from BaseException for side_effect
        class MockHTTPStatusError(Exception):
            def __init__(self, message, response=None):
                self.response = response

        error = MockHTTPStatusError("Error", response=mock_response)

        # Patch httpx.HTTPStatusError in the backend module to be our mock class
        with patch("backend.github_client.httpx.HTTPStatusError", MockHTTPStatusError):
            mock_response.raise_for_status.side_effect = error
            mock_client.request = AsyncMock(return_value=mock_response)

            result = await github_client._request("GET", "/test")
            assert result is None

            captured = capsys.readouterr()
            assert "[GitHubClient] HTTP Error 404: Not Found" in captured.out

@pytest.mark.asyncio
async def test_request_generic_error(github_client, capsys):
    with patch("backend.github_client.httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value.__aenter__.return_value
        mock_client.request = AsyncMock(side_effect=Exception("Generic error"))

        # We also need to patch HTTPStatusError to be a real exception type because in _request it tries to catch it
        # If it's globally mocked, catching it throws TypeError: catching classes that do not inherit from BaseException is not allowed
        class MockHTTPStatusError(Exception):
            pass

        with patch("backend.github_client.httpx.HTTPStatusError", MockHTTPStatusError):
            result = await github_client._request("GET", "/test")
            assert result is None

            captured = capsys.readouterr()
            assert "[GitHubClient] Request Error: Generic error" in captured.out

@pytest.mark.asyncio
async def test_get_repo_details(github_client):
    with patch.object(github_client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"id": 1}
        result = await github_client.get_repo_details("owner", "repo")
        assert result == {"id": 1}
        mock_request.assert_called_once_with("GET", "/repos/owner/repo")

@pytest.mark.asyncio
async def test_get_branches(github_client):
    with patch.object(github_client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = [{"name": "main"}]
        result = await github_client.get_branches("owner", "repo")
        assert result == [{"name": "main"}]
        mock_request.assert_called_once_with("GET", "/repos/owner/repo/branches")

@pytest.mark.asyncio
async def test_compare_commits(github_client):
    with patch.object(github_client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"status": "ahead"}
        result = await github_client.compare_commits("owner", "repo", "main", "dev")
        assert result == {"status": "ahead"}
        mock_request.assert_called_once_with("GET", "/repos/owner/repo/compare/main...dev")

@pytest.mark.asyncio
async def test_merge_branch(github_client):
    with patch.object(github_client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"sha": "123"}
        result = await github_client.merge_branch("owner", "repo", "main", "dev", message="Custom merge")
        assert result == {"sha": "123"}
        mock_request.assert_called_once_with(
            "POST",
            "/repos/owner/repo/merges",
            json={"base": "main", "head": "dev", "commit_message": "Custom merge"}
        )

@pytest.mark.asyncio
async def test_merge_branch_default_message(github_client):
    with patch.object(github_client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"sha": "123"}
        result = await github_client.merge_branch("owner", "repo", "main", "dev")
        assert result == {"sha": "123"}
        mock_request.assert_called_once_with(
            "POST",
            "/repos/owner/repo/merges",
            json={"base": "main", "head": "dev", "commit_message": "Merge dev into main"}
        )

@pytest.mark.asyncio
async def test_get_commit(github_client):
    with patch.object(github_client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"sha": "123"}
        result = await github_client.get_commit("owner", "repo", "123")
        assert result == {"sha": "123"}
        mock_request.assert_called_once_with("GET", "/repos/owner/repo/commits/123")

@pytest.mark.asyncio
async def test_delete_branch(github_client):
    with patch.object(github_client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = True
        result = await github_client.delete_branch("owner", "repo", "dev")
        assert result is True
        mock_request.assert_called_once_with("DELETE", "/repos/owner/repo/git/refs/heads/dev")

@pytest.mark.asyncio
async def test_list_pull_requests(github_client):
    with patch.object(github_client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = [{"number": 1}]
        result = await github_client.list_pull_requests("owner", "repo", state="closed")
        assert result == [{"number": 1}]
        mock_request.assert_called_once_with("GET", "/repos/owner/repo/pulls", params={"state": "closed"})

@pytest.mark.asyncio
async def test_get_pull_request(github_client):
    with patch.object(github_client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"number": 1}
        result = await github_client.get_pull_request("owner", "repo", 1)
        assert result == {"number": 1}
        mock_request.assert_called_once_with("GET", "/repos/owner/repo/pulls/1")

@pytest.mark.asyncio
async def test_get_check_runs(github_client):
    with patch.object(github_client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"total_count": 0}
        result = await github_client.get_check_runs("owner", "repo", "main")
        assert result == {"total_count": 0}
        mock_request.assert_called_once_with("GET", "/repos/owner/repo/commits/main/check-runs")

@pytest.mark.asyncio
async def test_get_commit_status(github_client):
    with patch.object(github_client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = {"state": "success"}
        result = await github_client.get_commit_status("owner", "repo", "main")
        assert result == {"state": "success"}
        mock_request.assert_called_once_with("GET", "/repos/owner/repo/commits/main/status")

@pytest.mark.asyncio
async def test_merge_pull_request_success(github_client):
    with patch("backend.github_client.httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value.__aenter__.return_value
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"sha": "123", "merged": True, "message": "Pull Request successfully merged"}
        mock_client.request = AsyncMock(return_value=mock_response)

        result = await github_client.merge_pull_request("owner", "repo", 1)
        assert result == {"sha": "123", "merged": True, "message": "Pull Request successfully merged"}
        mock_client.request.assert_called_once_with(
            "PUT",
            "https://api.github.com/repos/owner/repo/pulls/1/merge",
            headers=github_client.headers,
            json={"merge_method": "merge"}
        )

@pytest.mark.asyncio
async def test_merge_pull_request_204(github_client):
    with patch("backend.github_client.httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value.__aenter__.return_value
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_client.request = AsyncMock(return_value=mock_response)

        result = await github_client.merge_pull_request("owner", "repo", 1)
        assert result == {"merged": True}

@pytest.mark.asyncio
async def test_merge_pull_request_value_error(github_client):
    with patch("backend.github_client.httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value.__aenter__.return_value
        mock_response = MagicMock()
        mock_response.status_code = 405
        mock_response.text = "Method Not Allowed"
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_client.request = AsyncMock(return_value=mock_response)

        result = await github_client.merge_pull_request("owner", "repo", 1)
        assert result == {"message": "HTTP 405: Method Not Allowed"}

@pytest.mark.asyncio
async def test_merge_pull_request_exception(github_client):
    with patch("backend.github_client.httpx.AsyncClient") as mock_client_class:
        mock_client = mock_client_class.return_value.__aenter__.return_value
        mock_client.request = AsyncMock(side_effect=Exception("Generic error"))

        result = await github_client.merge_pull_request("owner", "repo", 1)
        assert result == {"message": "Generic error"}
