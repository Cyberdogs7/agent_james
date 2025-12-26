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

tools_list = [{"function_declarations": [
    generate_cad_prototype_tool,
    write_file_tool,
    read_directory_tool,
    read_file_tool
] + list(trello_tools.values())}]


