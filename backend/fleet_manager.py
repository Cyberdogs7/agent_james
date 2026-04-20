import time
import json
from pathlib import Path

class FleetManager:
    def __init__(self, data_file="fleet_state.json", max_agents=15):
        self.data_file = Path(data_file)
        self.max_agents = max_agents

        # In-memory state
        self.agents = {} # agent_id -> { id, status, current_repo, current_session, last_active, error }
        self.repos = {}  # repo_name -> { name, queue: [{id, prompt}] }

        self.load_state()
        self._ensure_agents()

    def _ensure_agents(self):
        # Make sure we have exactly max_agents available
        current_agent_ids = list(self.agents.keys())
        for i in range(1, self.max_agents + 1):
            agent_id = f"agent_{i}"
            if agent_id not in self.agents:
                self.agents[agent_id] = {
                    "id": agent_id,
                    "status": "idle", # idle, working, stuck, error
                    "current_repo": None,
                    "current_session": None,
                    "last_active": time.time(),
                    "error": None
                }

    def load_state(self):
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.agents = data.get("agents", {})
                    self.repos = data.get("repos", {})
            except Exception as e:
                print(f"[FleetManager] Error loading state: {e}")

    def save_state(self):
        try:
            with open(self.data_file, 'w') as f:
                json.dump({"agents": self.agents, "repos": self.repos}, f, indent=2)
        except Exception as e:
            print(f"[FleetManager] Error saving state: {e}")

    def get_state(self):
        return {
            "agents": list(self.agents.values()),
            "repos": list(self.repos.values())
        }

    def ensure_repo(self, repo_name):
        if repo_name not in self.repos:
            self.repos[repo_name] = {"name": repo_name, "queue": []}
            self.save_state()

    def add_task_to_queue(self, repo_name, prompt):
        self.ensure_repo(repo_name)
        task_id = f"task_{int(time.time()*1000)}"
        self.repos[repo_name]["queue"].append({"id": task_id, "prompt": prompt})
        self.save_state()
        return task_id

    def remove_task_from_queue(self, repo_name, task_id):
        if repo_name in self.repos:
            self.repos[repo_name]["queue"] = [t for t in self.repos[repo_name]["queue"] if t["id"] != task_id]
            self.save_state()

    def assign_agent(self, agent_id, repo_name):
        if agent_id in self.agents:
            self.ensure_repo(repo_name)
            self.agents[agent_id]["current_repo"] = repo_name
            self.agents[agent_id]["status"] = "idle" # Defaults to idle until it picks up a task
            self.agents[agent_id]["last_active"] = time.time()
            self.save_state()
            return True
        return False

    def unassign_agent(self, agent_id):
        if agent_id in self.agents:
            self.agents[agent_id]["current_repo"] = None
            self.agents[agent_id]["status"] = "idle"
            self.agents[agent_id]["last_active"] = time.time()
            self.save_state()
            return True
        return False

    def update_agent_session(self, agent_id, session_id, status="working"):
        if agent_id in self.agents:
            self.agents[agent_id]["current_session"] = session_id
            self.agents[agent_id]["status"] = status
            self.agents[agent_id]["last_active"] = time.time()
            if status == "error":
                self.agents[agent_id]["error"] = "Agent encountered an error or stalled."
            else:
                self.agents[agent_id]["error"] = None
            self.save_state()

    def get_next_task(self, repo_name):
        if repo_name in self.repos and self.repos[repo_name]["queue"]:
            return self.repos[repo_name]["queue"].pop(0)
        return None

    def check_stuck_and_idle_agents(self):
        """
        Returns a tuple: (stuck_agents, agents_to_reallocate)
        """
        stuck_agents = []
        agents_to_reallocate = []
        now = time.time()

        # Repos with items in queue
        repos_with_work = [r for r in self.repos.values() if r["queue"]]

        for agent in self.agents.values():
            time_idle = now - agent["last_active"]

            # Stuck Check: Working for > 2 hours with no activity update
            if agent["status"] == "working" and time_idle > 7200: # 2 hours
                agent["status"] = "stuck"
                agent["error"] = "Session stalled for > 2 hours"
                stuck_agents.append(agent)
                self.save_state()

            # Idle Reallocation Check: Idle for > 5 mins, assigned to empty repo, and other repos have work
            elif agent["status"] == "idle" and agent["current_repo"] and time_idle > 300: # 5 mins
                repo_name = agent["current_repo"]
                if repo_name in self.repos and not self.repos[repo_name]["queue"]:
                    if repos_with_work:
                        agents_to_reallocate.append(agent)
                        # Reset timer so we don't spam
                        agent["last_active"] = now
                        self.save_state()

        return stuck_agents, agents_to_reallocate
