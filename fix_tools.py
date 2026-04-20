import re

with open("backend/tools.py", "r") as f:
    content = f.read()

# Fix the broken replacement string
content = content.replace('''display_dashboard_tool = {

    {
        "name": "assign_agent_to_repo",''', '''display_dashboard_tool = {
    "name": "display_dashboard",
    "description": "Displays the 'War Room' dashboard, aggregating project status, Trello tickets, active agents, and device health into a unified view.",
    "parameters": {
        "type": "OBJECT",
        "properties": {}
    }
}

assign_agent_tool = {
        "name": "assign_agent_to_repo",''')

content = content.replace('''"name": "display_dashboard",
    "description": "Displays the 'War Room' dashboard, aggregating project status, Trello tickets, active agents, and device health into a unified view.",
    "parameters": {
        "type": "OBJECT",
        "properties": {}
    }
}''', '')

# Need to make sure assign_agent and add_task are added to all_tools_list or properly defined as dicts
content = content.replace('''    {
        "name": "assign_agent_to_repo",''', '''
assign_agent_tool = {
        "name": "assign_agent_to_repo",''')

content = content.replace('''    {
        "name": "add_task_to_repo_queue",''', '''
add_task_tool = {
        "name": "add_task_to_repo_queue",''')

# We'll just append them to the all_tools_list manually to be safe.
# Let's completely revert tools.py and re-patch it cleanly.
