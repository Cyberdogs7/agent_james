import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import subprocess

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

try:
    from backend.git_ops import GitOps
except ImportError:
    # Fallback for when running from root
    from git_ops import GitOps

class TestGitOps(unittest.TestCase):
    @patch('subprocess.run')
    def test_get_current_branch(self, mock_run):
        mock_run.return_value = MagicMock(stdout="main\n", returncode=0)
        branch = GitOps.get_current_branch("/tmp/repo")
        self.assertEqual(branch, "main")
        mock_run.assert_called_with(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd="/tmp/repo",
            capture_output=True,
            text=True,
            check=True
        )

    @patch('subprocess.run')
    def test_get_last_commit_info(self, mock_run):
        mock_run.return_value = MagicMock(stdout="a1b2c3d|Author Name|2 hours ago|Commit message", returncode=0)
        info = GitOps.get_last_commit_info("/tmp/repo")
        self.assertIsNotNone(info)
        self.assertEqual(info["hash"], "a1b2c3d")
        self.assertEqual(info["author"], "Author Name")
        self.assertEqual(info["date"], "2 hours ago")
        self.assertEqual(info["message"], "Commit message")
        mock_run.assert_called_with(
            ["git", "log", "-1", "--format=%h|%an|%ar|%s"],
            cwd="/tmp/repo",
            capture_output=True,
            text=True,
            check=True
        )

    @patch('subprocess.run')
    def test_get_last_commit_info_fail(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(1, cmd=["git", "log"])
        info = GitOps.get_last_commit_info("/tmp/repo")
        self.assertIsNone(info)

    @patch('subprocess.run')
    def test_list_branches(self, mock_run):
        mock_run.return_value = MagicMock(stdout="main\ndev\nfeature\n", returncode=0)
        branches = GitOps.list_branches("/tmp/repo")
        self.assertEqual(branches, ["main", "dev", "feature"])

    @patch('subprocess.run')
    def test_merge_branch_success(self, mock_run):
        # Mock list_branches first
        with patch.object(GitOps, 'list_branches', return_value=['main', 'dev']):
            mock_run.return_value = MagicMock(stdout="Merge made by the 'ort' strategy.", returncode=0)
            success, msg = GitOps.merge_branch("/tmp/repo", "dev")
            self.assertTrue(success)
            self.assertIn("Successfully merged", msg)

    @patch('subprocess.run')
    def test_merge_branch_fail_not_exist(self, mock_run):
        with patch.object(GitOps, 'list_branches', return_value=['main']):
            success, msg = GitOps.merge_branch("/tmp/repo", "dev")
            self.assertFalse(success)
            self.assertIn("does not exist", msg)

    @patch('subprocess.run')
    def test_commit_changes_success(self, mock_run):
        mock_run.return_value = MagicMock(stdout="[main 1234567] message", returncode=0)
        success, msg = GitOps.commit_changes("/tmp/repo", "test commit")
        self.assertTrue(success)
        self.assertIn("Committed changes", msg)
        mock_run.assert_called_with(
            ["git", "commit", "-a", "-m", "test commit"],
            cwd="/tmp/repo",
            capture_output=True,
            text=True,
            check=True
        )

    @patch('subprocess.run')
    def test_push_changes_success(self, mock_run):
        mock_run.return_value = MagicMock(stdout="Everything up-to-date", returncode=0)
        success, msg = GitOps.push_changes("/tmp/repo")
        self.assertTrue(success)
        self.assertIn("Successfully pushed changes", msg)
        mock_run.assert_called_with(
            ["git", "push"],
            cwd="/tmp/repo",
            capture_output=True,
            text=True,
            check=True
        )

    @patch('subprocess.run')
    def test_pull_changes_success(self, mock_run):
        mock_run.return_value = MagicMock(stdout="Already up to date.", returncode=0)
        success, msg = GitOps.pull_changes("/tmp/repo")
        self.assertTrue(success)
        self.assertIn("Successfully pulled changes", msg)
        mock_run.assert_called_with(
            ["git", "pull"],
            cwd="/tmp/repo",
            capture_output=True,
            text=True,
            check=True
        )

if __name__ == '__main__':
    unittest.main()
