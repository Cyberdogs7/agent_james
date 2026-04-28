import re
with open('backend/fleet_manager.py', 'r') as f:
    content = f.read()

resolved = re.sub(
    r"<<<<<<< HEAD.*?>>>>>>> origin/master\n",
    "                    # If the task was assigned to an agent that errored out, reset its state to idle\n                    agent_id_failed = task.get(\"agent_id\")\n                    if agent_id_failed and agent_id_failed in self.agents:\n                        if self.agents[agent_id_failed][\"status\"] == \"error\":\n                            self.update_agent_session(agent_id_failed, None, \"idle\")\n",
    content, flags=re.DOTALL
)

with open('backend/fleet_manager.py', 'w') as f:
    f.write(resolved)
