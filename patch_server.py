def patch():
    with open("backend/server.py", "r") as f:
        content = f.read()

    new_endpoint = """
@sio.event
async def set_repo_active_state(sid, data):
    repo_name = data.get('repo_name')
    is_active = data.get('is_active')
    if repo_name is not None and is_active is not None:
        fleet_manager.set_repo_active(repo_name, is_active)
        await sio.emit('fleet_state_update', fleet_manager.get_state())

@sio.event
async def assign_agent_to_repo(sid, data):"""

    # We need to replace the decorator @sio.event\nasync def assign_agent_to_repo specifically
    target = "@sio.event\nasync def assign_agent_to_repo(sid, data):"
    if "@sio.event\nasync def set_repo_active_state(sid, data):" not in content:
        content = content.replace(target, new_endpoint)

    with open("backend/server.py", "w") as f:
        f.write(content)

patch()
