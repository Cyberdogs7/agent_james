import subprocess
import os

class GitOps:
    @staticmethod
    def get_current_branch(repo_path):
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    @staticmethod
    def list_branches(repo_path):
        try:
            result = subprocess.run(
                ["git", "branch", "--format=%(refname:short)"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip().split('\n')
        except subprocess.CalledProcessError:
            return []

    @staticmethod
    def merge_branch(repo_path, source_branch):
        try:
            # Check if source branch exists
            branches = GitOps.list_branches(repo_path)
            if source_branch not in branches:
                return False, f"Branch '{source_branch}' does not exist."

            # Perform merge
            result = subprocess.run(
                ["git", "merge", source_branch],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return True, f"Successfully merged '{source_branch}'.\n{result.stdout}"
        except subprocess.CalledProcessError as e:
            return False, f"Merge failed:\n{e.stderr}"

    @staticmethod
    def get_status(repo_path):
        try:
            result = subprocess.run(
                ["git", "status", "--short"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return "Failed to get status."

    @staticmethod
    def get_last_commit_info(repo_path):
        try:
            # Format: hash|author|date|message
            result = subprocess.run(
                ["git", "log", "-1", "--format=%h|%an|%ar|%s"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            output = result.stdout.strip()
            if output:
                parts = output.split('|', 3)
                if len(parts) == 4:
                    return {
                        "hash": parts[0],
                        "author": parts[1],
                        "date": parts[2],
                        "message": parts[3]
                    }
            return None
        except subprocess.CalledProcessError:
            return None

    @staticmethod
    def commit_changes(repo_path, message):
        try:
            # We use -a to stage all modified/deleted files.
            # Note: This does not add untracked files.
            result = subprocess.run(
                ["git", "commit", "-a", "-m", message],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return True, f"Committed changes: {result.stdout}"
        except subprocess.CalledProcessError as e:
            return False, f"Commit failed:\n{e.stderr}"

    @staticmethod
    def push_changes(repo_path):
        try:
            result = subprocess.run(
                ["git", "push"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return True, f"Successfully pushed changes.\n{result.stdout}"
        except subprocess.CalledProcessError as e:
            return False, f"Push failed:\n{e.stderr}"

    @staticmethod
    def pull_changes(repo_path):
        try:
            result = subprocess.run(
                ["git", "pull"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return True, f"Successfully pulled changes.\n{result.stdout}"
        except subprocess.CalledProcessError as e:
            return False, f"Pull failed:\n{e.stderr}"
