try:
    from time_utils import set_time_format_tool, get_datetime_tool
except ImportError:
    try:
        from backend.time_utils import set_time_format_tool, get_datetime_tool
    except ImportError:
        # Fallback definitions if import fails (e.g. during standalone testing)
        set_time_format_tool = {
            "name": "set_time_format",
            "description": "Sets the preferred time format for displaying time.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "format": {
                        "type": "STRING",
                        "description": "The desired time format, either '12h' or '24h'."
                    }
                },
                "required": ["format"]
            }
        }
        get_datetime_tool = {
            "name": "get_datetime",
            "description": "Gets the current date and time in the local timezone.",
            "parameters": {
                "type": "OBJECT",
                "properties": {}
            }
        }

generate_cad_tool = {
    "name": "generate_cad",
    "description": "Generates a 3D CAD model based on a prompt.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "prompt": {"type": "STRING", "description": "The description of the object to generate."}
        },
        "required": ["prompt"]
    },
    "behavior": "NON_BLOCKING"
}

generate_cad_prototype_tool = {
    "name": "generate_cad_prototype",
    "description": "Generates a 3D wireframe prototype based on a user's description. Use this when the user asks to 'visualize', 'prototype', 'create a wireframe', or 'design' something in 3D.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "prompt": {
                "type": "STRING",
                "description": "The user's description of the object to prototype."
            }
        },
        "required": ["prompt"]
    }
}

run_web_agent_tool = {
    "name": "run_web_agent",
    "description": "Opens a web browser and performs a task according to the prompt.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "prompt": {"type": "STRING", "description": "The detailed instructions for the web browser agent."}
        },
        "required": ["prompt"]
    },
    "behavior": "NON_BLOCKING"
}

create_project_tool = {
    "name": "create_project",
    "description": "Creates a new project folder to organize files.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING", "description": "The name of the new project."}
        },
        "required": ["name"]
    }
}

modify_timer_tool = {
    "name": "modify_timer",
    "description": "Modifies an existing timer or reminder.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING", "description": "The name of the timer or reminder to modify."},
            "new_duration": {"type": "INTEGER", "description": "The new duration of the timer in seconds."},
            "new_timestamp": {"type": "STRING", "description": "The new time for the reminder in ISO format (e.g., 'YYYY-MM-DDTHH:MM:SS')."}
        },
        "required": ["name"]
    }
}

switch_project_tool = {
    "name": "switch_project",
    "description": "Switches the current active project context.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING", "description": "The name of the project to switch to."}
        },
        "required": ["name"]
    }
}

dismiss_jules_session_tool = {
    "name": "dismiss_jules_session",
    "description": "Dismisses (hides) a Jules session from the dashboard.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "session_id": {"type": "STRING", "description": "The ID of the session to dismiss."}
        },
        "required": ["session_id"]
    }
}

stop_jules_session_tool = {
    "name": "stop_jules_session",
    "description": "Stops a running Jules session (stops polling) and dismisses it from the active view.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "session_id": {"type": "STRING", "description": "The ID of the session to stop."}
        },
        "required": ["session_id"]
    }
}

merge_pull_request_tool = {
    "name": "merge_pull_request",
    "description": "Merges a specific Pull Request on a GitHub repository.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "owner": {"type": "STRING", "description": "The owner of the repository."},
            "repo": {"type": "STRING", "description": "The name of the repository."},
            "pull_number": {"type": "INTEGER", "description": "The number of the Pull Request to merge."},
            "merge_method": {"type": "STRING", "description": "Optional merge method: 'merge', 'squash', or 'rebase'. Defaults to 'merge'."}
        },
        "required": ["owner", "repo", "pull_number"]
    }
}

list_projects_tool = {
    "name": "list_projects",
    "description": "Lists all available projects.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
    }
}

list_smart_devices_tool = {
    "name": "list_smart_devices",
    "description": "Lists all available smart home devices (lights, plugs, etc.) on the network.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
    }
}

control_light_tool = {
    "name": "control_light",
    "description": "Controls a smart light device.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "target": {
                "type": "STRING",
                "description": "The IP address of the device to control. Always prefer the IP address over the alias for reliability."
            },
            "action": {
                "type": "STRING",
                "description": "The action to perform: 'turn_on', 'turn_off', or 'set'."
            },
            "brightness": {
                "type": "INTEGER",
                "description": "Optional brightness level (0-100)."
            },
            "color": {
                "type": "STRING",
                "description": "Optional color name (e.g., 'red', 'cool white') or 'warm'."
            }
        },
        "required": ["target", "action"]
    }
}

discover_printers_tool = {
    "name": "discover_printers",
    "description": "Discovers 3D printers available on the local network.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
    }
}

print_stl_tool = {
    "name": "print_stl",
    "description": "Prints an STL file to a 3D printer. Handles slicing the STL to G-code and uploading to the printer.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "stl_path": {"type": "STRING", "description": "Path to STL file, or 'current' for the most recent CAD model."},
            "printer": {"type": "STRING", "description": "Printer name or IP address."},
            "profile": {"type": "STRING", "description": "Optional slicer profile name."}
        },
        "required": ["stl_path", "printer"]
    }
}

get_print_status_tool = {
    "name": "get_print_status",
    "description": "Gets the current status of a 3D printer including progress, time remaining, and temperatures.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "printer": {"type": "STRING", "description": "Printer name or IP address."}
        },
        "required": ["printer"]
    }
}

iterate_cad_tool = {
    "name": "iterate_cad",
    "description": "Modifies or iterates on the current CAD design based on user feedback. Use this when the user asks to adjust, change, modify, or iterate on the existing 3D model (e.g., 'make it taller', 'add a handle', 'reduce the thickness').",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "prompt": {"type": "STRING", "description": "The changes or modifications to apply to the current design."}
        },
        "required": ["prompt"]
    },
    "behavior": "NON_BLOCKING"
}

set_timer_tool = {
    "name": "set_timer",
    "description": "Sets a timer for a specified duration.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "duration": {"type": "INTEGER", "description": "The duration of the timer in seconds."},
            "name": {"type": "STRING", "description": "The name of the timer."}
        },
        "required": ["duration", "name"]
    }
}

set_reminder_tool = {
    "name": "set_reminder",
    "description": "Sets a reminder for a specific time.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "timestamp": {"type": "STRING", "description": "The time for the reminder in ISO format (e.g., 'YYYY-MM-DDTHH:MM:SS')."},
            "name": {"type": "STRING", "description": "The name of the reminder."}
        },
        "required": ["timestamp", "name"]
    }
}

list_timers_tool = {
    "name": "list_timers",
    "description": "Lists all active timers and reminders.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
    }
}

delete_entry_tool = {
    "name": "delete_entry",
    "description": "Deletes a timer or reminder by name.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING", "description": "The name of the timer or reminder to delete."}
        },
        "required": ["name"]
    }
}

check_for_updates_tool = {
    "name": "check_for_updates",
    "description": "Checks if a new version of the application is available from the GitHub repository.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
    }
}

apply_update_tool = {
    "name": "apply_update",
    "description": "Downloads the latest version of the application from GitHub and restarts the application to apply the changes.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
    }
}

change_voice_tool = {
    "name": "change_voice",
    "description": "Changes the voice of the assistant for the current project. This will cause a brief reconnection.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "voice_name": {"type": "STRING", "description": "The name of the voice to switch to. Valid options are: Puck, Charon, Kore, Fenrir, Aoede, Sadaltager."}
        },
        "required": ["voice_name"]
    }
}

update_persona_tool = {
    "name": "update_persona",
    "description": "Updates the persona (system instructions) for the current project. This effectively changes who the assistant 'is'. Use this to switch roles (e.g., from 'Cheeky Butler' to 'Strict Commander'). This will cause a brief reconnection.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "persona": {"type": "STRING", "description": "The new system prompt description of the persona."}
        },
        "required": ["persona"]
    }
}

display_dashboard_tool = {
    "name": "display_dashboard",
    "description": "Displays the 'War Room' dashboard, aggregating project status, Trello tickets, active agents, and device health into a unified view.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
    }
}

get_morning_briefing_tool = {
    "name": "get_morning_briefing",
    "description": "Retrieves the daily morning briefing (fleet status, PRs, issues). Use this when the user asks for 'the briefing', 'status report', or 'what's new'. Returns text that you MUST read aloud to the user.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "force_refresh": {
                "type": "BOOLEAN",
                "description": "Optional: Set to true to force a fresh report generation instead of using cached data."
            }
        },
    }
}

send_jules_feedback_tool = {
    "name": "send_jules_feedback",
    "description": "Sends feedback to a Jules session.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "session_id": {
                "type": "STRING",
                "description": "The ID of the session to send feedback to."
            },
            "feedback": {
                "type": "STRING",
                "description": "The feedback to send."
            }
        },
        "required": ["session_id", "feedback"]
    }
}

run_jules_agent_tool = {
    "name": "run_jules_agent",
    "description": "Creates a new Jules task. If the source is not provided, the user will be prompted to select one.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "prompt": {
                "type": "STRING",
                "description": "The prompt to send to the Jules agent."
            },
            "source": {
                "type": "STRING",
                "description": "Optional: The source to use for the Jules agent."
            }
        },
        "required": ["prompt"]
    }
}

spawn_swarm_agent_tool = {
    "name": "spawn_swarm_agent",
    "description": "Spawns a new Swarm Agent (Jules) with a specific role and task. Use this to delegate work to specialized agents.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "role": {
                "type": "STRING",
                "description": "The role of the agent (e.g., 'Frontend Engineer', 'Security Auditor', 'Python Expert')."
            },
            "prompt": {
                "type": "STRING",
                "description": "The detailed task or instruction for the agent."
            },
            "source": {
                "type": "STRING",
                "description": "Optional: The source context (repo) for the agent."
            },
            "swarm_id": {
                "type": "STRING",
                "description": "Optional: The ID of the swarm/mission this agent belongs to."
            }
        },
        "required": ["role", "prompt"]
    }
}

create_swarm_mission_tool = {
    "name": "create_swarm_mission",
    "description": "Initializes a new Swarm Mission. Returns a swarm_id that should be passed to spawn_swarm_agent calls.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "title": {
                "type": "STRING",
                "description": "The title of the mission (e.g., 'Refactor Authentication', 'Fix UI Bugs')."
            }
        },
        "required": ["title"]
    }
}


list_jules_sources_tool = {
    "name": "list_jules_sources",
    "description": "Lists all available Jules sources.",
    "parameters": {
        "type": "OBJECT",
        "properties": {}
    }
}

toggle_jules_slack_notifications_tool = {
    "name": "toggle_jules_slack_notifications",
    "description": "Enables or disables Slack notifications for Jules agent status updates. Default is disabled.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "enabled": {
                "type": "BOOLEAN",
                "description": "True to enable notifications, False to disable."
            }
        },
        "required": ["enabled"]
    }
}

set_auto_merge_threshold_tool = {
    "name": "set_auto_merge_threshold",
    "description": "Sets the minimum age (in hours) for a Pull Request to be considered for automatic smart merging.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "hours": {
                "type": "NUMBER",
                "description": "The number of hours a PR must be open and stable."
            }
        },
        "required": ["hours"]
    }
}

add_architectural_memory_tool = {
    "name": "add_architectural_memory",
    "description": "Stores an architectural decision, constraint, or 'lesson learned' in the project's long-term memory. Use this when you make a significant decision or discover a best practice.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "content": {
                "type": "STRING",
                "description": "The memory content (e.g., 'Use httpx instead of requests', 'Database schema must use UUIDs')."
            },
            "tags": {
                "type": "ARRAY",
                "items": {
                    "type": "STRING"
                },
                "description": "Optional tags for categorization (e.g., ['architecture', 'python', 'database'])."
            }
        },
        "required": ["content"]
    }
}

list_jules_sessions_tool = {
    "name": "list_jules_sessions",
    "description": "Lists all Jules sessions saved in the current project's local memory.",
    "parameters": {
        "type": "OBJECT",
        "properties": {}
    }
}

list_jules_activities_tool = {
    "name": "list_jules_activities",
    "description": "Lists all activities for a specific Jules session.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "session_id": {
                "type": "STRING",
                "description": "The ID of the session to list activities for."
            }
        },
        "required": ["session_id"]
    }
}

jules_get_diff_tool = {
    "name": "jules_get_diff",
    "description": "Retrieves the code diff (unified patch) for a Jules session or a specific activity. Use this to see what code changes the agent has made.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "session_id": {
                "type": "STRING",
                "description": "The ID of the session."
            },
            "activity_id": {
                "type": "STRING",
                "description": "Optional: The ID of a specific activity to get the diff from."
            }
        },
        "required": ["session_id"]
    }
}

write_file_tool = {
    "name": "write_file",
    "description": "Writes content to a file at the specified path. Overwrites if exists.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "path": {
                "type": "STRING",
                "description": "The path of the file to write to."
            },
            "content": {
                "type": "STRING",
                "description": "The content to write to the file."
            }
        },
        "required": ["path", "content"]
    }
}

read_directory_tool = {
    "name": "read_directory",
    "description": "Lists the contents of a directory.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "path": {
                "type": "STRING",
                "description": "The path of the directory to list."
            }
        },
        "required": ["path"]
    }
}

read_file_tool = {
    "name": "read_file",
    "description": "Reads the content of a file.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "path": {
                "type": "STRING",
                "description": "The path of the file to read."
            }
        },
        "required": ["path"]
    }
}

append_system_prompt_tool = {
    "name": "append_system_prompt",
    "description": "Appends text to the end of the current project's system prompt. Automatically adds a newline separator.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "text": {
                "type": "STRING",
                "description": "The text to append to the system prompt."
            }
        },
        "required": ["text"]
    }
}

delete_custom_system_prompt_tool = {
    "name": "delete_custom_system_prompt",
    "description": "Resets the project's system prompt to the default value. Requires user confirmation.",
    "parameters": {
        "type": "OBJECT",
        "properties": {}
    }
}

get_system_prompt_tool = {
    "name": "get_system_prompt",
    "description": "Retrieves the current system prompt for the project.",
    "parameters": {
        "type": "OBJECT",
        "properties": {}
    }
}

switch_video_source_tool = {
    "name": "switch_video_source",
    "description": "Switches the video input source between the webcam and the screen. Use 'screen' to see what the user sees on their monitor, and 'camera' to see the user.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "source": {
                "type": "STRING",
                "description": "The video source to switch to. Must be either 'camera' or 'screen'."
            }
        },
        "required": ["source"]
    }
}

trello_tools = {
    "list_boards": {
        "name": "trello_list_boards",
        "description": "Lists all Trello boards.",
        "parameters": {}
    },
    "get_board": {
        "name": "trello_get_board",
        "description": "Gets details for a specific Trello board.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "board_id": {"type": "STRING", "description": "The ID of the board to retrieve."}
            },
            "required": ["board_id"]
        }
    },
    "list_lists": {
        "name": "trello_list_lists",
        "description": "Lists all lists on a specific Trello board.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "board_id": {"type": "STRING", "description": "The ID of the board."}
            },
            "required": ["board_id"]
        }
    },
    "list_cards": {
        "name": "trello_list_cards",
        "description": "Lists all cards in a specific Trello list.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "list_id": {"type": "STRING", "description": "The ID of the list."}
            },
            "required": ["list_id"]
        }
    },
    "get_card": {
        "name": "trello_get_card",
        "description": "Gets details for a specific Trello card.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "card_id": {"type": "STRING", "description": "The ID of the card to retrieve."}
            },
            "required": ["card_id"]
        }
    },
    "list_comments": {
        "name": "trello_list_comments",
        "description": "Lists all comments on a specific Trello card.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "card_id": {"type": "STRING", "description": "The ID of the card."}
            },
            "required": ["card_id"]
        }
    },
    "list_attachments": {
        "name": "trello_list_attachments",
        "description": "Lists all attachments on a specific Trello card.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "card_id": {"type": "STRING", "description": "The ID of the card."}
            },
            "required": ["card_id"]
        }
    },
    "list_checklists": {
        "name": "trello_list_checklists",
        "description": "Lists all checklists on a specific Trello card.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "card_id": {"type": "STRING", "description": "The ID of the card."}
            },
            "required": ["card_id"]
        }
    },
    "list_members": {
        "name": "trello_list_members",
        "description": "Lists all members of a specific Trello board.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "board_id": {"type": "STRING", "description": "The ID of the board."}
            },
            "required": ["board_id"]
        }
    },
    "create_board": {
        "name": "trello_create_board",
        "description": "Creates a new Trello board.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "name": {"type": "STRING", "description": "The name of the new board."},
                "description": {"type": "STRING", "description": "A description for the board."}
            },
            "required": ["name"]
        }
    },
    "create_list": {
        "name": "trello_create_list",
        "description": "Creates a new list on a Trello board.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "board_id": {"type": "STRING", "description": "The ID of the board."},
                "name": {"type": "STRING", "description": "The name of the new list."}
            },
            "required": ["board_id", "name"]
        }
    },
    "create_card": {
        "name": "trello_create_card",
        "description": "Creates a new card in a Trello list.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "list_id": {"type": "STRING", "description": "The ID of the list."},
                "name": {"type": "STRING", "description": "The name of the new card."},
                "description": {"type": "STRING", "description": "A description for the card."}
            },
            "required": ["list_id", "name"]
        }
    },
    "update_board": {
        "name": "trello_update_board",
        "description": "Updates a Trello board.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "board_id": {"type": "STRING", "description": "The ID of the board to update."},
                "name": {"type": "STRING", "description": "The new name for the board."},
                "description": {"type": "STRING", "description": "The new description for the board."}
            },
            "required": ["board_id"]
        }
    },
    "update_list": {
        "name": "trello_update_list",
        "description": "Updates a Trello list.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "list_id": {"type": "STRING", "description": "The ID of the list to update."},
                "name": {"type": "STRING", "description": "The new name for the list."},
                "pos": {"type": "STRING", "description": "The new position for the list."}
            },
            "required": ["list_id"]
        }
    },
    "update_card": {
        "name": "trello_update_card",
        "description": "Updates a Trello card.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "card_id": {"type": "STRING", "description": "The ID of the card to update."},
                "name": {"type": "STRING", "description": "The new name for the card."},
                "description": {"type": "STRING", "description": "The new description for the card."},
                "idList": {"type": "STRING", "description": "The new list for the card."}
            },
            "required": ["card_id"]
        }
    },
    "add_comment": {
        "name": "trello_add_comment",
        "description": "Adds a comment to a Trello card.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "card_id": {"type": "STRING", "description": "The ID of the card."},
                "text": {"type": "STRING", "description": "The comment text."}
            },
            "required": ["card_id", "text"]
        }
    },
    "add_attachment": {
        "name": "trello_add_attachment",
        "description": "Adds an attachment to a Trello card.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "card_id": {"type": "STRING", "description": "The ID of the card."},
                "url": {"type": "STRING", "description": "The URL of the attachment."}
            },
            "required": ["card_id", "url"]
        }
    },
    "add_checklist": {
        "name": "trello_add_checklist",
        "description": "Adds a checklist to a Trello card.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "card_id": {"type": "STRING", "description": "The ID of the card."},
                "name": {"type": "STRING", "description": "The name of the checklist."}
            },
            "required": ["card_id", "name"]
        }
    },
    "add_member_to_board": {
        "name": "trello_add_member_to_board",
        "description": "Adds a member to a Trello board.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "board_id": {"type": "STRING", "description": "The ID of the board."},
                "email": {"type": "STRING", "description": "The email of the member to add."}
            },
            "required": ["board_id", "email"]
        }
    },
    "add_member_to_card": {
        "name": "trello_add_member_to_card",
        "description": "Adds a member to a Trello card.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "card_id": {"type": "STRING", "description": "The ID of the card."},
                "member_id": {"type": "STRING", "description": "The ID of the member to add."}
            },
            "required": ["card_id", "member_id"]
        }
    },
    "move_card_to_board": {
        "name": "trello_move_card_to_board",
        "description": "Moves a Trello card to another board.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "card_id": {"type": "STRING", "description": "The ID of the card to move."},
                "board_id": {"type": "STRING", "description": "The ID of the destination board."}
            },
            "required": ["card_id", "board_id"]
        }
    },
    "move_list_to_board": {
        "name": "trello_move_list_to_board",
        "description": "Moves a Trello list to another board.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "list_id": {"type": "STRING", "description": "The ID of the list to move."},
                "board_id": {"type": "STRING", "description": "The ID of the destination board."}
            },
            "required": ["list_id", "board_id"]
        }
    },
    "delete_card": {
        "name": "trello_delete_card",
        "description": "Deletes a Trello card.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "card_id": {"type": "STRING", "description": "The ID of the card to delete."}
            },
            "required": ["card_id"]
        }
    },
    "copy_board": {
        "name": "trello_copy_board",
        "description": "Copies a Trello board.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "board_id": {"type": "STRING", "description": "The ID of the board to copy."},
                "name": {"type": "STRING", "description": "The name of the new board."}
            },
            "required": ["board_id", "name"]
        }
    },
    "copy_card": {
        "name": "trello_copy_card",
        "description": "Copies a Trello card.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "card_id": {"type": "STRING", "description": "The ID of the card to copy."},
                "list_id": {"type": "STRING", "description": "The ID of the destination list."}
            },
            "required": ["card_id", "list_id"]
        }
    },
    "enable_powerup": {
        "name": "trello_enable_powerup",
        "description": "Enables a Power-Up on a Trello board.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "board_id": {"type": "STRING", "description": "The ID of the board."},
                "powerup_id": {"type": "STRING", "description": "The ID of the Power-Up to enable."}
            },
            "required": ["board_id", "powerup_id"]
        }
    },
    "disable_powerup": {
        "name": "trello_disable_powerup",
        "description": "Disables a Power-Up on a Trello board.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "board_id": {"type": "STRING", "description": "The ID of the board."},
                "powerup_id": {"type": "STRING", "description": "The ID of the Power-Up to disable."}
            },
            "required": ["board_id", "powerup_id"]
        }
    }
}

apply_task_fix_tool = {
    "name": "apply_task_fix",
    "description": "Applies a self-healing code fix to a failed automation task. Use this when the user approves a fix for a broken script.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "task_id": {
                "type": "STRING",
                "description": "The ID of the failed task."
            }
        },
        "required": ["task_id"]
    }
}

run_ollama_agent_tool = {
    "name": "run_ollama_agent",
    "description": "Creates a new local Ollama agent task. Use this when the user specifically asks for a local agent, or when you need to perform a task locally without sending data to the cloud. Supports reading local files for context.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "prompt": {
                "type": "STRING",
                "description": "The prompt to send to the local agent."
            },
            "source": {
                "type": "STRING",
                "description": "Optional: The local file path or directory to use as context."
            },
            "model": {
                "type": "STRING",
                "description": "Optional: The name of the Ollama model to use (e.g., 'llama3'). Defaults to 'llama3'."
            },
            "role": {
                "type": "STRING",
                "description": "Optional: The role of the agent."
            }
        },
        "required": ["prompt"]
    }
}

all_tools_list = [
    generate_cad_tool,
    generate_cad_prototype_tool,
    run_web_agent_tool,
    create_project_tool,
    switch_project_tool,
    list_projects_tool,
    list_smart_devices_tool,
    control_light_tool,
    discover_printers_tool,
    print_stl_tool,
    get_print_status_tool,
    iterate_cad_tool,
    set_timer_tool,
    set_reminder_tool,
    list_timers_tool,
    delete_entry_tool,
    modify_timer_tool,
    check_for_updates_tool,
    apply_update_tool,
    change_voice_tool,
    update_persona_tool,
    display_dashboard_tool,
    get_morning_briefing_tool,
    write_file_tool,
    read_directory_tool,
    read_file_tool,
    run_jules_agent_tool,
    run_ollama_agent_tool,
    spawn_swarm_agent_tool,
    create_swarm_mission_tool,
    send_jules_feedback_tool,
    list_jules_sources_tool,
    list_jules_sessions_tool,
    list_jules_activities_tool,
    jules_get_diff_tool,
    append_system_prompt_tool,
    delete_custom_system_prompt_tool,
    get_system_prompt_tool,
    toggle_jules_slack_notifications_tool,
    set_auto_merge_threshold_tool,
    add_architectural_memory_tool,
    switch_video_source_tool,
    apply_task_fix_tool,
    dismiss_jules_session_tool,
    stop_jules_session_tool,
    merge_pull_request_tool,
    set_time_format_tool,
    get_datetime_tool
] + list(trello_tools.values()) + [
    {
        "name": "search",
        "description": "Searches for a query across all available tools, local files, AND conversation history. Use this to find past decisions or discussions.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "The search query."}
            },
            "required": ["query"]
        }
    },
    {
        "name": "search_gifs",
        "description": "Searches for GIFs.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "The search query."
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "display_content",
        "description": "Displays content on the screen, such as images or widgets.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "content_type": {
                    "type": "STRING",
                    "description": "Use 'image' for URLs, 'widget' for data, or 'clear' to hide content."
                },
                "url": {
                    "type": "STRING",
                    "description": "The URL of an image."
                },
                "widget_type": {
                    "type": "STRING",
                    "description": "The kind of widget, e.g., 'weather'."
                },
                "data": {
                    "type": "OBJECT",
                    "description": "JSON data for the widget, usually from another tool."
                },
                "duration": {
                    "type": "INTEGER",
                    "description": "Optional duration in seconds. Defaults to a short period."
                }
            },
            "required": ["content_type"]
        }
    },
    {
        "name": "get_weather",
        "description": "Fetches weather forecast data for a given location. Can retrieve future forecasts (up to 16 days), historical data (up to 92 days), and specific hourly or daily weather variables (e.g., temperature_2m_max, wind_speed_10m, uv_index). Always use this tool when the user asks for the weather.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "location": {
                    "type": "STRING",
                    "description": "The city and state, e.g., San Francisco, CA"
                },
                "forecast_days": {
                    "type": "INTEGER",
                    "description": "The number of days to forecast (0-16). Defaults to 7."
                },
                "past_days": {
                    "type": "INTEGER",
                    "description": "The number of past days to retrieve data for (0-92)."
                },
                "hourly": {
                    "type": "ARRAY",
                    "items": {
                        "type": "STRING"
                    },
                    "description": "A list of hourly weather variables to retrieve (e.g., 'temperature_2m', 'precipitation_probability')."
                },
                "daily": {
                    "type": "ARRAY",
                    "items": {
                        "type": "STRING"
                    },
                    "description": "A list of daily aggregate weather variables to retrieve (e.g., 'temperature_2m_max', 'uv_index_max')."
                }
            },
            "required": ["location"]
        }
    },
    {
        "name": "restart_application",
        "description": "Restarts the entire application, including the backend and frontend. Use this tool when the user asks to 'restart' or 'reboot' the system.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
},
{
    "name": "git_merge_branch",
    "description": "Merges a git branch into the current branch.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "branch_name": {
                "type": "STRING",
                "description": "The name of the branch to merge."
                },
                "repo_name": {
                    "type": "STRING",
                    "description": "Optional: The name of the project/repo to operate on. Defaults to current project."
            }
        },
        "required": ["branch_name"]
    }
    },
    {
        "name": "git_commit",
        "description": "Commits all modified and deleted files (git commit -a) with a message.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "message": {
                    "type": "STRING",
                    "description": "The commit message."
                },
                "repo_name": {
                    "type": "STRING",
                    "description": "Optional: The name of the project/repo to operate on. Defaults to current project."
                }
            },
            "required": ["message"]
        }
    },
    {
        "name": "git_push",
        "description": "Pushes commits to the remote repository.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "repo_name": {
                    "type": "STRING",
                    "description": "Optional: The name of the project/repo to operate on. Defaults to current project."
                }
            }
        }
    },
    {
        "name": "git_status",
        "description": "Gets the detailed status of a specific repository (branch, changes, last commit).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "repo_name": {
                    "type": "STRING",
                    "description": "Optional: The name of the project/repo to get status for. Defaults to current project."
                }
            }
        }
    },
    {
        "name": "git_fleet_status",
        "description": "Generates a high-level status report for ALL git repositories (branch, clean/dirty state, last commit summary). Use this to give an 'Engineering Manager' style overview.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "sync_git_repos",
        "description": "Syncs the local fleet with the sources available to Jules. Clones any missing repositories.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "git_pull",
        "description": "Pulls changes from the remote repository.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "repo_name": {
                    "type": "STRING",
                    "description": "Optional: The name of the project/repo to operate on. Defaults to current project."
                }
            }
        }
    },
    {
        "name": "git_list_repos",
        "description": "Lists all available local git repositories.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "git_list_branches",
        "description": "Lists all branches in a git repository.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "repo_name": {
                    "type": "STRING",
                    "description": "Optional: The name of the project/repo to list branches for. Defaults to current project."
                }
            }
        }
    },
    {
        "name": "proactive_suggestion",
        "description": "A tool for the proactive agent to make suggestions to the user.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "suggestion": {
                    "type": "STRING",
                    "description": "The suggestion to make to the user."
                }
            },
            "required": ["suggestion"]
        }
    },
    {
        "name": "send_slack_message",
        "description": "Sends a message to a Slack channel.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "message": {
                    "type": "STRING",
                    "description": "The message to send."
                }
            },
            "required": ["message"]
        }
    },
    {
        "name": "control_os",
        "description": "Controls the operating system (launch apps, volume, lock screen, sleep).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "The action to perform: 'launch', 'set_volume', 'mute', 'unmute', 'lock_screen', 'sleep'."
                },
                "value": {
                    "type": "STRING",
                    "description": "The value for the action (e.g., app name for 'launch', volume level 0-100 for 'set_volume')."
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "play_music",
        "description": "Plays a song or artist on YouTube Music. Use this when the user asks to play music.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "The song, artist, or album to play."
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "control_music",
        "description": "Controls music playback (pause, resume, next, previous, volume).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "enum": ["play", "pause", "resume", "next", "previous", "volume_up", "volume_down"],
                    "description": "The action to perform."
                }
            },
            "required": ["action"]
        }
    }
]

# Legacy support for existing imports
tools_list = [{'google_search': {}}, {"function_declarations": all_tools_list}]
