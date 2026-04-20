import re

with open("backend/automation_engine.py", "r") as f:
    content = f.read()

# Let's insert a check for fleet_manager into the run_checks loop
insert_code = """
        # --- Fleet Manager Check ---
        from backend.server import fleet_manager
        stuck_agents, agents_to_reallocate = fleet_manager.check_stuck_and_idle_agents()

        for agent in stuck_agents:
            msg = f"Sir, Agent {agent['id']} in {agent['current_repo']} has been stalled for over 2 hours. Please check the dashboard."
            if self.ada and self.ada.session:
                asyncio.create_task(self.ada.session.send(input=f"System Notification: You MUST ask the user exactly this: '{msg}'", end_of_turn=True))

        if agents_to_reallocate:
            agent_names = ", ".join([a['id'] for a in agents_to_reallocate])
            msg = f"Sir, we have idle agents ({agent_names}) in empty repos, while other repos have pending tasks. Would you like me to reallocate them?"
            if self.ada and self.ada.session:
                asyncio.create_task(self.ada.session.send(input=f"System Notification: You MUST ask the user exactly this: '{msg}'", end_of_turn=True))

        if stuck_agents or agents_to_reallocate:
            # Force update to clients
            from backend.server import sio
            asyncio.create_task(sio.emit('fleet_state_update', fleet_manager.get_state()))

"""

# Insert before '# 2. PR Aging Check'
content = content.replace("# 2. PR Aging Check", insert_code + "\n        # 2. PR Aging Check")

with open("backend/automation_engine.py", "w") as f:
    f.write(content)
