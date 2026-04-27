import json

def patch():
    with open("backend/fleet_manager.py", "r") as f:
        content = f.read()

    # Update ensure_repo
    old_ensure = """    def ensure_repo(self, repo_name):
        if repo_name not in self.repos:
            self.repos[repo_name] = {"name": repo_name, "queue": []}
            self.save_state()"""

    new_ensure = """    def ensure_repo(self, repo_name):
        if repo_name not in self.repos:
            self.repos[repo_name] = {"name": repo_name, "queue": [], "is_active": False}
            self.save_state()"""

    content = content.replace(old_ensure, new_ensure)

    # Update get_by_session
    old_get = """    def get_by_session(self, session_id):
        for agent_id, agent in self.agents.items():
            if agent.get("current_session") == session_id:
                repo_name = agent.get("current_repo")
                if repo_name in self.repos:
                    for task in self.repos[repo_name]["queue"]:
                        if task.get("agent_id") == agent_id and task.get("status") not in ["completed", "failed"]:
                            return agent_id, repo_name, task["id"]
        return None, None, None"""

    new_get = """    def get_by_session(self, session_id):
        for agent_id, agent in self.agents.items():
            if agent.get("current_session") == session_id:
                for repo_name, repo_data in self.repos.items():
                    for task in repo_data["queue"]:
                        if task.get("agent_id") == agent_id and task.get("status") not in ["completed", "failed"]:
                            return agent_id, repo_name, task["id"]
        return None, None, None"""

    content = content.replace(old_get, new_get)

    new_methods = """
    def set_repo_active(self, repo_name, active):
        self.ensure_repo(repo_name)
        self.repos[repo_name]["is_active"] = active
        if not active:
            # When moving repo out, agents go back to pool but continue if busy
            for agent_id, agent in self.agents.items():
                if agent.get("current_repo") == repo_name:
                    # Just remove them from the repo visually, they keep working
                    agent["current_repo"] = None
        self.save_state()
"""

    if "def set_repo_active" not in content:
        content = content.replace("    def ensure_repo", new_methods + "    def ensure_repo")

    with open("backend/fleet_manager.py", "w") as f:
        f.write(content)

patch()
