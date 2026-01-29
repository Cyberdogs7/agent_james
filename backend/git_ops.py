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
