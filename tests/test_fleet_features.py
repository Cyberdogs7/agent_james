import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from backend.automation_engine import AutomationEngine
from backend.github_client import GitHubClient

class TestFleetFeatures(unittest.IsolatedAsyncioTestCase):
    async def test_cross_project_trigger(self):
        print("\n[TEST] Testing Cross-Project Triggers...")

        # Mocks
        mock_pm = MagicMock()
        mock_pm.list_projects.return_value = ["ProjectA", "ProjectB"]
        mock_pm.get_project_path = lambda name: f"/mock/path/{name}"
        mock_pm.current_project = "ProjectA" # Current is A

        mock_ada = MagicMock()
        mock_ada.handle_jules_request = AsyncMock(return_value="Task Started")

        # Mock Task Manager Class
        # We need it to return different tasks based on the path
        mock_tm_class = MagicMock()

        def mock_tm_init(path):
            tm = MagicMock()
            if "ProjectA" in path:
                tm.list_tasks.return_value = [] # No tasks in A
            elif "ProjectB" in path:
                # Project B has a trigger listening for commits in RepoA
                tm.list_tasks.return_value = [{
                    "id": "task_b",
                    "status": "active",
                    "title": "Build Project B",
                    "trigger": {
                        "type": "git",
                        "value": "owner/RepoA"
                    },
                    "action": {
                        "type": "jules_task",
                        "value": "Run Tests"
                    }
                }]
            return tm

        mock_tm_class.side_effect = mock_tm_init

        # Instantiate Engine
        # We mock the task_manager argument but it's not used directly for this test,
        # as the engine uses self.task_manager.__class__
        initial_tm = MagicMock()
        initial_tm.__class__ = mock_tm_class

        engine = AutomationEngine(initial_tm, mock_pm, mock_ada)

        # Trigger Event
        event_data = {
            "type": "git_commit",
            "repo": "owner/RepoA",
            "message": "Update core",
            "author": "Dev"
        }

        await engine.trigger_event("git_commit", event_data)

        # Verification
        # Expect handle_jules_request to be called
        mock_ada.handle_jules_request.assert_called_once()

        # Verify Context Injection
        call_args = mock_ada.handle_jules_request.call_args
        prompt = call_args[0][0]

        print(f"Generated Prompt: {prompt}")

        assert "Context: You are working on project 'ProjectB'" in prompt
        assert "Trigger Context" in prompt
        assert "owner/RepoA" in prompt

        print("[TEST] Success: Cross-project task triggered with correct context.")

    async def test_github_merge_pr(self):
        print("\n[TEST] Testing GitHubClient.merge_pull_request...")
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"merged": True}
            mock_instance.request.return_value = mock_response

            client = GitHubClient("token")
            result = await client.merge_pull_request("owner", "repo", 42, "squash")

            assert result["merged"] is True
            mock_instance.request.assert_called_with(
                "PUT",
                "https://api.github.com/repos/owner/repo/pulls/42/merge",
                headers=client.headers,
                json={"merge_method": "squash"}
            )
            print("[TEST] Success: merge_pull_request called correctly.")

    async def test_stalled_pr_nag(self):
        print("\n[TEST] Testing Stalled PR Nagging...")

        # Mocks
        mock_pm = MagicMock()
        mock_pm.get_github_token.return_value = "token"
        mock_pm.load_fleet.return_value = [{"owner": "Owner", "name": "Repo"}]

        mock_ada = MagicMock()
        mock_ada.handle_external_event = AsyncMock()
        mock_ada.jules_agent = MagicMock()
        mock_ada.jules_agent.list_sessions = AsyncMock(return_value=[]) # No sessions

        engine = AutomationEngine(MagicMock(), mock_pm, mock_ada)

        # Mock GitHub Client inside the method scope?
        # AutomationEngine imports GitHubClient. We need to patch it where it is imported.
        # It's imported in backend.automation_engine.

        with patch('backend.automation_engine.GitHubClient') as MockGH:
            import sys
            import types
            sys.modules['backend.server'] = types.ModuleType('backend.server')
            sys.modules['backend.server'].fleet_manager = MagicMock()
            sys.modules['backend.server'].fleet_manager.repos = {"Owner/Repo": {"is_active": True}}

            mock_client = MockGH.return_value

            # Setup stalled PR
            stalled_time = "2023-01-01T00:00:00Z" # Very old
            mock_client.list_pull_requests = AsyncMock(return_value=[{
                "title": "Stalled Feature",
                "html_url": "http://github.com/Owner/Repo/pull/1",
                "number": 1,
                "updated_at": stalled_time
            }])

            # Force run logic
            await engine._monitor_stalled_items()

            # Verification
            mock_ada.handle_external_event.assert_called_once()
            call_arg = mock_ada.handle_external_event.call_args[0][0]

            print(f"Nag Message: {call_arg}")
            msg = call_arg['message']

            # Check if Owner/Repo and Number are present (Proof that 'owner' variable was resolved)
            assert "Owner/Repo" in msg
            assert "#1" in msg
            assert "Stalled Feature" in msg

            print("[TEST] Success: Nag message constructed correctly without NameError.")

if __name__ == "__main__":
    unittest.main()
