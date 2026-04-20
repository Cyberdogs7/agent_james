with open("backend/tools.py", "r") as f:
    content = f.read()

# Fix the broken array/dict syntax
content = content.replace('''    {
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
    "name": "display_dashboard",''', '''    "name": "display_dashboard",''')

content = content.replace('''    {
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
    },''', '')


# Let's add them at the bottom of the all_tools_list instead.
tools_to_append = """    {
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
    }
"""
content = content.replace('    {\n        "name": "control_music",', tools_to_append + '    {\n        "name": "control_music",')

with open("backend/tools.py", "w") as f:
    f.write(content)
