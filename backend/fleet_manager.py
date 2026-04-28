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

    def update_max_agents(self, new_max):
        self.max_agents = new_max
        self._ensure_agents()
        self.save_state()

    def _ensure_agents(self):
        # Determine the maximum required agent ID by looking at existing IDs
        existing_numbers = [int(a_id.split('_')[1]) for a_id in self.agents.keys() if a_id.startswith('agent_')]
        highest_existing = max(existing_numbers) if existing_numbers else 0

        # We need at least max_agents, but maybe more if we haven't been able to downscale yet
        target_max_id = max(self.max_agents, highest_existing)

        # Fill in any gaps up to target_max_id
        for i in range(1, target_max_id + 1):
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

        # If we have too many agents, try to remove unassigned idle ones from the top
        if len(self.agents) > self.max_agents:
            agent_ids = sorted(list(self.agents.keys()), key=lambda x: int(x.split('_')[1]), reverse=True)
            for agent_id in agent_ids:
                # We only want to remove agents that are above max_agents to preserve order if possible
                num = int(agent_id.split('_')[1])
                if num > self.max_agents:
                    agent = self.agents[agent_id]
                    if agent["status"] == "idle" and agent["current_repo"] is None:
                        del self.agents[agent_id]

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
    def ensure_repo(self, repo_name):
        if repo_name not in self.repos:
            self.repos[repo_name] = {"name": repo_name, "queue": [], "is_active": False}
            self.save_state()

    def add_task_to_queue(self, repo_name, prompt, depends_on=None):
        self.ensure_repo(repo_name)
        task_id = f"task_{int(time.time()*1000)}"
        self.repos[repo_name]["queue"].append({
            "id": task_id,
            "prompt": prompt,
            "status": "pending", # pending, in_progress, completed, failed
            "depends_on": depends_on,
            "agent_id": None
        })
        self.save_state()
        return task_id

    def update_task_status(self, repo_name, task_id, status, agent_id=None):
        if repo_name in self.repos:
            for task in self.repos[repo_name]["queue"]:
                if task["id"] == task_id:
                    task["status"] = status
                    if agent_id is not None:
                        task["agent_id"] = agent_id
                    break
            self.save_state()

    def remove_task_from_queue(self, repo_name, task_id):
        if repo_name in self.repos:
            self.repos[repo_name]["queue"] = [t for t in self.repos[repo_name]["queue"] if t["id"] != task_id]
            self.save_state()

    def retry_task(self, repo_name, task_id):
        if repo_name in self.repos:
            for task in self.repos[repo_name]["queue"]:
                if task["id"] == task_id:
                    task["status"] = "pending"
                    task["agent_id"] = None
                    break
            self.save_state()

    def clear_completed_tasks(self, repo_name):
        if repo_name in self.repos:
            self.repos[repo_name]["queue"] = [t for t in self.repos[repo_name]["queue"] if t.get("status") != "completed"]
            self.save_state()

    def get_by_session(self, session_id):
        for agent_id, agent in self.agents.items():
            if agent.get("current_session") == session_id:
                for repo_name, repo_data in self.repos.items():
                    for task in repo_data["queue"]:
                        if task.get("agent_id") == agent_id and task.get("status") not in ["completed", "failed"]:
                            return agent_id, repo_name, task["id"]
        return None, None, None

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
        """Returns the next pending task whose dependencies are satisfied."""
        if repo_name in self.repos and self.repos[repo_name]["queue"]:
            queue = self.repos[repo_name]["queue"]
            # Pre-compute ALL task states for dependency checking
            # If a task is no longer in the queue (e.g., cleared), its status is 'cleared'
            task_status = {t["id"]: t.get("status") for t in queue}

            for task in queue:
                if task.get("status", "pending") == "pending":
                    depends_on = task.get("depends_on")
                    # Task is unblocked if it has no dependency, OR
                    # if the dependency is completed, OR
                    # if the dependency is no longer in the queue (was cleared).
                    if not depends_on or task_status.get(depends_on) == "completed" or depends_on not in task_status:
                        return task
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
