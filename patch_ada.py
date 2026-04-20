import re

with open("backend/ada.py", "r") as f:
    content = f.read()

# Add tool registrations
reg_code = """
        self.tool_registry.register("assign_agent_to_repo", self.handle_assign_agent)
        self.tool_registry.register("add_task_to_repo_queue", self.handle_add_task)
"""

content = content.replace('self.tool_registry.register("display_dashboard", self.handle_display_dashboard)',
                          reg_code + '        self.tool_registry.register("display_dashboard", self.handle_display_dashboard)')

# Add handlers
handlers_code = """

    async def handle_assign_agent(self, agent_id, repo_name):
        from backend.server import fleet_manager, sio
        if fleet_manager.assign_agent(agent_id, repo_name):
            await sio.emit('fleet_state_update', fleet_manager.get_state())
            return f"Assigned {agent_id} to {repo_name}."
        return f"Failed to assign {agent_id}. Agent may not exist."

    async def handle_add_task(self, repo_name, prompt):
        from backend.server import fleet_manager, sio
        fleet_manager.add_task_to_queue(repo_name, prompt)
        await sio.emit('fleet_state_update', fleet_manager.get_state())
        return f"Task added to {repo_name} queue."
"""

content = content.replace('async def handle_display_dashboard(self):', handlers_code + '\n    async def handle_display_dashboard(self):')

with open("backend/ada.py", "w") as f:
    f.write(content)
