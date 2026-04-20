import json

with open("backend/tools.py", "r") as f:
    content = f.read()

new_tools = """    {
        "name": "assign_agent_to_repo",
        "description": "Assigns an idle agent to a specific repository room.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "agent_id": {
                    "type": "STRING",
                    "description": "The ID of the agent (e.g., 'agent_1')."
                },
                "repo_name": {
                    "type": "STRING",
                    "description": "The name of the repository to assign the agent to."
                }
            },
            "required": ["agent_id", "repo_name"]
        }
    },
    {
        "name": "add_task_to_repo_queue",
        "description": "Adds a task prompt to a repository's queue for agents to pick up.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "repo_name": {
                    "type": "STRING",
                    "description": "The name of the repository."
                },
                "prompt": {
                    "type": "STRING",
                    "description": "The task instructions for the agent."
                }
            },
            "required": ["repo_name", "prompt"]
        }
    },
"""

# Find the all_tools_list array and insert right before the last item (control_music)
content = content.replace('    {\n        "name": "control_music",', new_tools + '    {\n        "name": "control_music",')

with open("backend/tools.py", "w") as f:
    f.write(content)
