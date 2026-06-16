import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from backend.github_agent import GitHubAgent

@pytest.fixture
def mock_project_manager():
    pm = MagicMock()
    pm.get_github_token.return_value = "mock_token"
    return pm

@pytest.fixture
def github_agent(mock_project_manager):
    return GitHubAgent(mock_project_manager)

@pytest.mark.asyncio
async def test_get_client_missing_token(mock_project_manager):
    mock_project_manager.get_github_token.return_value = None
    agent = GitHubAgent(mock_project_manager)
    res = await agent.get_repo_details("owner", "repo")
    assert "GitHub token not found" in res

@pytest.mark.asyncio
@patch("backend.github_agent.GitHubClient")
async def test_get_repo_details(mock_client_class, github_agent):
    mock_client = mock_client_class.return_value
    mock_client.get_repo_details = AsyncMock(return_value={
        "full_name": "owner/repo",
        "description": "test desc",
        "stargazers_count": 42,
        "default_branch": "main",
        "html_url": "http://github.com/owner/repo"
    })
    
    res = await github_agent.get_repo_details("owner", "repo")
    assert "Repository: owner/repo" in res
    assert "Description: test desc" in res
    assert "Stars: 42" in res
    assert "Default Branch: main" in res
    assert "URL: http://github.com/owner/repo" in res
    mock_client.get_repo_details.assert_called_once_with("owner", "repo")

@pytest.mark.asyncio
@patch("backend.github_agent.GitHubClient")
async def test_list_branches(mock_client_class, github_agent):
    mock_client = mock_client_class.return_value
    mock_client.get_branches = AsyncMock(return_value=[
        {"name": "main"},
        {"name": "dev"}
    ])
    
    res = await github_agent.list_branches("owner", "repo")
    assert "Branches in 'owner/repo': main, dev" in res
    mock_client.get_branches.assert_called_once_with("owner", "repo")

@pytest.mark.asyncio
@patch("backend.github_agent.GitHubClient")
async def test_compare_commits(mock_client_class, github_agent):
    mock_client = mock_client_class.return_value
    mock_client.compare_commits = AsyncMock(return_value={
        "status": "ahead",
        "ahead_by": 5,
        "behind_by": 0,
        "total_commits": 5
    })
    
    res = await github_agent.compare_commits("owner", "repo", "main", "dev")
    assert "Status: ahead" in res
    assert "Ahead by: 5" in res
    assert "Behind by: 0" in res
    assert "Total Commits: 5" in res
    mock_client.compare_commits.assert_called_once_with("owner", "repo", "main", "dev")

@pytest.mark.asyncio
@patch("backend.github_agent.GitHubClient")
async def test_merge_branch(mock_client_class, github_agent):
    mock_client = mock_client_class.return_value
    mock_client.merge_branch = AsyncMock(return_value={
        "sha": "abcdef",
        "commit": {"message": "Merge message"}
    })
    
    res = await github_agent.merge_branch("owner", "repo", "main", "dev", "Merge msg")
    assert "Merged successfully" in res
    assert "Commit SHA: abcdef" in res
    assert "Message: Merge message" in res
    mock_client.merge_branch.assert_called_once_with("owner", "repo", "main", "dev", "Merge msg")

@pytest.mark.asyncio
@patch("backend.github_agent.GitHubClient")
async def test_get_commit(mock_client_class, github_agent):
    mock_client = mock_client_class.return_value
    mock_client.get_commit = AsyncMock(return_value={
        "sha": "abcdef",
        "commit": {
            "author": {"name": "User", "email": "user@example.com", "date": "2026-06-15"},
            "message": "Commit message"
        }
    })
    
    res = await github_agent.get_commit("owner", "repo", "abcdef")
    assert "Commit: abcdef" in res
    assert "Author: User <user@example.com>" in res
    assert "Date: 2026-06-15" in res
    assert "Message: Commit message" in res
    mock_client.get_commit.assert_called_once_with("owner", "repo", "abcdef")

@pytest.mark.asyncio
@patch("backend.github_agent.GitHubClient")
async def test_delete_branch(mock_client_class, github_agent):
    mock_client = mock_client_class.return_value
    mock_client.delete_branch = AsyncMock(return_value=True)
    
    res = await github_agent.delete_branch("owner", "repo", "dev")
    assert "Successfully deleted branch 'dev'" in res
    mock_client.delete_branch.assert_called_once_with("owner", "repo", "dev")

@pytest.mark.asyncio
@patch("backend.github_agent.GitHubClient")
async def test_list_pull_requests(mock_client_class, github_agent):
    mock_client = mock_client_class.return_value
    mock_client.list_pull_requests = AsyncMock(return_value=[
        {
            "number": 1,
            "title": "PR 1",
            "user": {"login": "user1"},
            "state": "open",
            "html_url": "http://github.com/owner/repo/pull/1"
        }
    ])
    
    res = await github_agent.list_pull_requests("owner", "repo", "open")
    assert "Pull Requests (open):" in res
    assert "PR #1: PR 1 by user1 (State: open) - http://github.com/owner/repo/pull/1" in res
    mock_client.list_pull_requests.assert_called_once_with("owner", "repo", "open")

@pytest.mark.asyncio
@patch("backend.github_agent.GitHubClient")
async def test_get_pull_request(mock_client_class, github_agent):
    mock_client = mock_client_class.return_value
    mock_client.get_pull_request = AsyncMock(return_value={
        "number": 1,
        "title": "PR 1",
        "state": "open",
        "merged": False,
        "user": {"login": "user1"},
        "base": {"ref": "main"},
        "head": {"ref": "dev"},
        "body": "PR description",
        "html_url": "http://github.com/owner/repo/pull/1"
    })
    
    res = await github_agent.get_pull_request("owner", "repo", 1)
    assert "PR #1: PR 1" in res
    assert "State: open (Merged: False)" in res
    assert "Author: user1" in res
    assert "Base Branch: main" in res
    assert "Head Branch: dev" in res
    assert "Body: PR description" in res
    assert "URL: http://github.com/owner/repo/pull/1" in res
    mock_client.get_pull_request.assert_called_once_with("owner", "repo", 1)

@pytest.mark.asyncio
@patch("backend.github_agent.GitHubClient")
async def test_merge_pull_request(mock_client_class, github_agent):
    mock_client = mock_client_class.return_value
    mock_client.merge_pull_request = AsyncMock(return_value={"merged": True})
    
    res = await github_agent.merge_pull_request("owner", "repo", 1, "merge")
    assert "Successfully merged PR #1" in res
    mock_client.merge_pull_request.assert_called_once_with("owner", "repo", 1, "merge")

@pytest.mark.asyncio
@patch("backend.github_agent.GitHubClient")
async def test_get_check_runs(mock_client_class, github_agent):
    mock_client = mock_client_class.return_value
    mock_client.get_check_runs = AsyncMock(return_value={
        "check_runs": [
            {"name": "build", "status": "completed", "conclusion": "success", "html_url": "http://build"}
        ]
    })
    
    res = await github_agent.get_check_runs("owner", "repo", "abcdef")
    assert "Check Runs for abcdef:" in res
    assert "- build: completed / success (http://build)" in res
    mock_client.get_check_runs.assert_called_once_with("owner", "repo", "abcdef")

@pytest.mark.asyncio
@patch("backend.github_agent.GitHubClient")
async def test_get_commit_status(mock_client_class, github_agent):
    mock_client = mock_client_class.return_value
    mock_client.get_commit_status = AsyncMock(return_value={
        "state": "success",
        "statuses": [
            {"context": "ci/tests", "state": "success", "description": "Tests passed"}
        ]
    })
    
    res = await github_agent.get_commit_status("owner", "repo", "abcdef")
    assert "Commit Status for abcdef:" in res
    assert "Combined State: success" in res
    assert "- ci/tests: success (Tests passed)" in res
    mock_client.get_commit_status.assert_called_once_with("owner", "repo", "abcdef")

@pytest.mark.asyncio
@patch("backend.github_agent.GitHubClient")
async def test_create_pull_request(mock_client_class, github_agent):
    mock_client = mock_client_class.return_value
    mock_client.create_pull_request = AsyncMock(return_value={
        "number": 2,
        "title": "New PR",
        "html_url": "http://github.com/owner/repo/pull/2"
    })
    
    res = await github_agent.create_pull_request("owner", "repo", "New PR", "dev", "main", "body text", True)
    assert "Successfully created PR #2: New PR" in res
    assert "URL: http://github.com/owner/repo/pull/2" in res
    mock_client.create_pull_request.assert_called_once_with("owner", "repo", "New PR", "dev", "main", "body text", True)

@pytest.mark.asyncio
@patch("backend.github_agent.GitHubClient")
async def test_list_issues(mock_client_class, github_agent):
    mock_client = mock_client_class.return_value
    mock_client.list_issues = AsyncMock(return_value=[
        {
            "number": 10,
            "title": "Issue 10",
            "user": {"login": "user2"},
            "state": "open",
            "html_url": "http://github.com/owner/repo/issues/10"
        }
    ])
    
    res = await github_agent.list_issues("owner", "repo", "open", assignee="user2")
    assert "Issues/PRs (open):" in res
    assert "Issue #10: Issue 10 by user2 (State: open)" in res
    mock_client.list_issues.assert_called_once_with("owner", "repo", "open", "user2", None, None, None)

@pytest.mark.asyncio
@patch("backend.github_agent.GitHubClient")
async def test_get_issue(mock_client_class, github_agent):
    mock_client = mock_client_class.return_value
    mock_client.get_issue = AsyncMock(return_value={
        "number": 10,
        "title": "Issue 10",
        "state": "open",
        "user": {"login": "user2"},
        "labels": [{"name": "bug"}],
        "body": "Issue description",
        "html_url": "http://github.com/owner/repo/issues/10"
    })
    
    res = await github_agent.get_issue("owner", "repo", 10)
    assert "Issue #10: Issue 10" in res
    assert "State: open" in res
    assert "Author: user2" in res
    assert "Labels: bug" in res
    assert "Body: Issue description" in res
    assert "URL: http://github.com/owner/repo/issues/10" in res
    mock_client.get_issue.assert_called_once_with("owner", "repo", 10)

@pytest.mark.asyncio
@patch("backend.github_agent.GitHubClient")
async def test_create_issue(mock_client_class, github_agent):
    mock_client = mock_client_class.return_value
    mock_client.create_issue = AsyncMock(return_value={
        "number": 11,
        "title": "New issue",
        "html_url": "http://github.com/owner/repo/issues/11"
    })
    
    res = await github_agent.create_issue("owner", "repo", "New issue", "body text", ["user2"], ["bug"])
    assert "Successfully created Issue #11: New issue" in res
    assert "URL: http://github.com/owner/repo/issues/11" in res
    mock_client.create_issue.assert_called_once_with("owner", "repo", "New issue", "body text", ["user2"], ["bug"])

@pytest.mark.asyncio
@patch("backend.github_agent.GitHubClient")
async def test_create_issue_comment(mock_client_class, github_agent):
    mock_client = mock_client_class.return_value
    mock_client.create_issue_comment = AsyncMock(return_value={
        "id": 999,
        "body": "comment text"
    })
    
    res = await github_agent.create_issue_comment("owner", "repo", 10, "comment text")
    assert "Successfully added comment on Issue #10 (Comment ID: 999)." in res
    mock_client.create_issue_comment.assert_called_once_with("owner", "repo", 10, "comment text")
