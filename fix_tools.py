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

    {
        "name": "assign_agent_to_repo",''')

with open("backend/tools.py", "w") as f:
    f.write(content)
