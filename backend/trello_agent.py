import os
import requests
import time

# Tool Definitions
list_boards_tool = {"name": "trello_list_boards", "description": "Lists all Trello boards for the user.", "parameters": {"type": "OBJECT", "properties": {}}}
get_board_tool = {"name": "trello_get_board", "description": "Gets details for a specific Trello board.", "parameters": {"type": "OBJECT", "properties": {"board_id": {"type": "STRING"}}, "required": ["board_id"]}}
list_lists_tool = {"name": "trello_list_lists", "description": "Lists all lists on a specific board.", "parameters": {"type": "OBJECT", "properties": {"board_id": {"type": "STRING"}}, "required": ["board_id"]}}
list_cards_tool = {"name": "trello_list_cards", "description": "Lists all cards in a specific list.", "parameters": {"type": "OBJECT", "properties": {"list_id": {"type": "STRING"}}, "required": ["list_id"]}}
get_card_tool = {"name": "trello_get_card", "description": "Gets details for a specific card.", "parameters": {"type": "OBJECT", "properties": {"card_id": {"type": "STRING"}}, "required": ["card_id"]}}
list_comments_tool = {"name": "trello_list_comments", "description": "Lists all comments on a card.", "parameters": {"type": "OBJECT", "properties": {"card_id": {"type": "STRING"}}, "required": ["card_id"]}}
list_attachments_tool = {"name": "trello_list_attachments", "description": "Lists all attachments on a card.", "parameters": {"type": "OBJECT", "properties": {"card_id": {"type": "STRING"}}, "required": ["card_id"]}}
list_checklists_tool = {"name": "trello_list_checklists", "description": "Lists all checklists on a card.", "parameters": {"type": "OBJECT", "properties": {"card_id": {"type": "STRING"}}, "required": ["card_id"]}}
list_members_tool = {"name": "trello_list_members", "description": "Lists all members of a board.", "parameters": {"type": "OBJECT", "properties": {"board_id": {"type": "STRING"}}, "required": ["board_id"]}}
create_board_tool = {"name": "trello_create_board", "description": "Creates a new Trello board.", "parameters": {"type": "OBJECT", "properties": {"name": {"type": "STRING"}, "description": {"type": "STRING"}}, "required": ["name"]}}
create_list_tool = {"name": "trello_create_list", "description": "Creates a new list on a board.", "parameters": {"type": "OBJECT", "properties": {"board_id": {"type": "STRING"}, "name": {"type": "STRING"}}, "required": ["board_id", "name"]}}
create_card_tool = {"name": "trello_create_card", "description": "Creates a new card in a list.", "parameters": {"type": "OBJECT", "properties": {"list_id": {"type": "STRING"}, "name": {"type": "STRING"}, "description": {"type": "STRING"}}, "required": ["list_id", "name"]}}
update_board_tool = {"name": "trello_update_board", "description": "Updates a Trello board's details.", "parameters": {"type": "OBJECT", "properties": {"board_id": {"type": "STRING"}, "name": {"type": "STRING"}, "description": {"type": "STRING"}}, "required": ["board_id"]}}
update_list_tool = {"name": "trello_update_list", "description": "Updates a Trello list's details.", "parameters": {"type": "OBJECT", "properties": {"list_id": {"type": "STRING"}, "name": {"type": "STRING"}, "pos": {"type": "STRING"}}, "required": ["list_id"]}}
update_card_tool = {"name": "trello_update_card", "description": "Updates a card's details.", "parameters": {"type": "OBJECT", "properties": {"card_id": {"type": "STRING"}, "name": {"type": "STRING"}, "description": {"type": "STRING"}, "idList": {"type": "STRING"}}, "required": ["card_id"]}}
add_comment_tool = {"name": "trello_add_comment", "description": "Adds a comment to a card.", "parameters": {"type": "OBJECT", "properties": {"card_id": {"type": "STRING"}, "text": {"type": "STRING"}}, "required": ["card_id", "text"]}}
add_attachment_tool = {"name": "trello_add_attachment", "description": "Adds an attachment to a card.", "parameters": {"type": "OBJECT", "properties": {"card_id": {"type": "STRING"}, "url": {"type": "STRING"}}, "required": ["card_id", "url"]}}
add_checklist_tool = {"name": "trello_add_checklist", "description": "Adds a checklist to a card.", "parameters": {"type": "OBJECT", "properties": {"card_id": {"type": "STRING"}, "name": {"type": "STRING"}}, "required": ["card_id", "name"]}}
add_member_to_board_tool = {"name": "trello_add_member_to_board", "description": "Adds a member to a board.", "parameters": {"type": "OBJECT", "properties": {"board_id": {"type": "STRING"}, "email": {"type": "STRING"}}, "required": ["board_id", "email"]}}
add_member_to_card_tool = {"name": "trello_add_member_to_card", "description": "Adds a member to a card.", "parameters": {"type": "OBJECT", "properties": {"card_id": {"type": "STRING"}, "member_id": {"type": "STRING"}}, "required": ["card_id", "member_id"]}}
move_card_to_board_tool = {"name": "trello_move_card_to_board", "description": "Moves a card to a different board.", "parameters": {"type": "OBJECT", "properties": {"card_id": {"type": "STRING"}, "board_id": {"type": "STRING"}}, "required": ["card_id", "board_id"]}}
move_list_to_board_tool = {"name": "trello_move_list_to_board", "description": "Moves a list to a different board.", "parameters": {"type": "OBJECT", "properties": {"list_id": {"type": "STRING"}, "board_id": {"type": "STRING"}}, "required": ["list_id", "board_id"]}}
delete_card_tool = {"name": "trello_delete_card", "description": "Deletes a card.", "parameters": {"type": "OBJECT", "properties": {"card_id": {"type": "STRING"}}, "required": ["card_id"]}}
copy_board_tool = {"name": "trello_copy_board", "description": "Copies a board.", "parameters": {"type": "OBJECT", "properties": {"board_id": {"type": "STRING"}, "name": {"type": "STRING"}}, "required": ["board_id", "name"]}}
copy_card_tool = {"name": "trello_copy_card", "description": "Copies a card.", "parameters": {"type": "OBJECT", "properties": {"card_id": {"type": "STRING"}, "list_id": {"type": "STRING"}, "name": {"type": "STRING"}}, "required": ["card_id", "list_id"]}}
enable_powerup_tool = {"name": "trello_enable_powerup", "description": "Enables a power-up on a board.", "parameters": {"type": "OBJECT", "properties": {"board_id": {"type": "STRING"}, "powerup_id": {"type": "STRING"}}, "required": ["board_id", "powerup_id"]}}
disable_powerup_tool = {"name": "trello_disable_powerup", "description": "Disables a power-up on a board.", "parameters": {"type": "OBJECT", "properties": {"board_id": {"type": "STRING"}, "powerup_id": {"type": "STRING"}}, "required": ["board_id", "powerup_id"]}}

class TrelloAgent:
    def __init__(self):
        self.api_key = os.getenv("TRELLO_API_KEY")
        self.token = os.getenv("TRELLO_TOKEN")
        self.base_url = "https://api.trello.com/1/"

    def _get_auth_params(self):
        return {"key": self.api_key, "token": self.token}

    def _request(self, method, url, **kwargs):
        """Helper method to make requests with retry logic."""
        max_retries = 3
        base_delay = 1
        for attempt in range(max_retries):
            try:
                response = requests.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    delay = base_delay * (2 ** attempt)
                    print(f"Rate limited (429) for Trello API at {url}. Retrying in {delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                else:
                    print(f"HTTP error occurred: {e}")
                    return None
            except Exception as e:
                print(f"An error occurred: {e}")
                return None
        return None

    def list_boards(self):
        url = f"{self.base_url}members/me/boards"
        params = self._get_auth_params()
        return self._request("GET", url, params=params)

    def get_board(self, board_id):
        url = f"{self.base_url}boards/{board_id}"
        params = self._get_auth_params()
        return self._request("GET", url, params=params)

    def list_lists(self, board_id):
        url = f"{self.base_url}boards/{board_id}/lists"
        params = self._get_auth_params()
        return self._request("GET", url, params=params)

    def list_cards(self, list_id):
        url = f"{self.base_url}lists/{list_id}/cards"
        params = self._get_auth_params()
        return self._request("GET", url, params=params)

    def get_card(self, card_id):
        url = f"{self.base_url}cards/{card_id}"
        params = self._get_auth_params()
        return self._request("GET", url, params=params)

    def list_comments(self, card_id):
        url = f"{self.base_url}cards/{card_id}/actions"
        params = self._get_auth_params()
        params["filter"] = "commentCard"
        return self._request("GET", url, params=params)

    def list_attachments(self, card_id):
        url = f"{self.base_url}cards/{card_id}/attachments"
        params = self._get_auth_params()
        return self._request("GET", url, params=params)

    def list_checklists(self, card_id):
        url = f"{self.base_url}cards/{card_id}/checklists"
        params = self._get_auth_params()
        return self._request("GET", url, params=params)

    def list_members(self, board_id):
        url = f"{self.base_url}boards/{board_id}/members"
        params = self._get_auth_params()
        return self._request("GET", url, params=params)

    def create_board(self, name, description=None):
        url = f"{self.base_url}boards"
        params = self._get_auth_params()
        params["name"] = name
        if description:
            params["desc"] = description
        return self._request("POST", url, params=params)

    def create_list(self, board_id, name):
        url = f"{self.base_url}boards/{board_id}/lists"
        params = self._get_auth_params()
        params["name"] = name
        return self._request("POST", url, params=params)

    def create_card(self, list_id, name, description=None):
        url = f"{self.base_url}cards"
        params = self._get_auth_params()
        params["idList"] = list_id
        params["name"] = name
        if description:
            params["desc"] = description
        return self._request("POST", url, params=params)

    def update_board(self, board_id, name=None, description=None):
        url = f"{self.base_url}boards/{board_id}"
        params = self._get_auth_params()
        if name:
            params["name"] = name
        if description:
            params["desc"] = description
        return self._request("PUT", url, params=params)

    def update_list(self, list_id, name=None, pos=None):
        url = f"{self.base_url}lists/{list_id}"
        params = self._get_auth_params()
        if name:
            params["name"] = name
        if pos:
            params["pos"] = pos
        return self._request("PUT", url, params=params)

    def update_card(self, card_id, name=None, description=None, idList=None):
        url = f"{self.base_url}cards/{card_id}"
        params = self._get_auth_params()
        if name:
            params["name"] = name
        if description:
            params["desc"] = description
        if idList:
            params["idList"] = idList
        return self._request("PUT", url, params=params)

    def add_comment(self, card_id, text):
        url = f"{self.base_url}cards/{card_id}/actions/comments"
        params = self._get_auth_params()
        params["text"] = text
        return self._request("POST", url, params=params)

    def add_attachment(self, card_id, url):
        url = f"{self.base_url}cards/{card_id}/attachments"
        params = self._get_auth_params()
        params["url"] = url
        return self._request("POST", url, params=params)

    def add_checklist(self, card_id, name):
        url = f"{self.base_url}cards/{card_id}/checklists"
        params = self._get_auth_params()
        params["name"] = name
        return self._request("POST", url, params=params)

    def add_member_to_board(self, board_id, email):
        url = f"{self.base_url}boards/{board_id}/members"
        params = self._get_auth_params()
        params["email"] = email
        params["type"] = "normal"
        return self._request("PUT", url, json=params)

    def add_member_to_card(self, card_id, member_id):
        url = f"{self.base_url}cards/{card_id}/idMembers"
        params = self._get_auth_params()
        params["value"] = member_id
        return self._request("POST", url, params=params)

    def move_card_to_board(self, card_id, board_id):
        url = f"{self.base_url}cards/{card_id}"
        params = self._get_auth_params()
        params["idBoard"] = board_id
        return self._request("PUT", url, params=params)

    def move_list_to_board(self, list_id, board_id):
        url = f"{self.base_url}lists/{list_id}/move"
        params = self._get_auth_params()
        params["value"] = board_id
        return self._request("PUT", url, params=params)

    def delete_card(self, card_id):
        url = f"{self.base_url}cards/{card_id}"
        params = self._get_auth_params()
        return self._request("DELETE", url, params=params)

    def copy_board(self, board_id, name):
        url = f"{self.base_url}boards"
        params = self._get_auth_params()
        params["idBoardSource"] = board_id
        params["name"] = name
        return self._request("POST", url, params=params)

    def copy_card(self, card_id, list_id, name=None):
        url = f"{self.base_url}cards"
        params = self._get_auth_params()
        params["idCardSource"] = card_id
        params["idList"] = list_id
        if name:
            params["name"] = name
        return self._request("POST", url, params=params)

    def enable_powerup(self, board_id, powerup_id):
        url = f"{self.base_url}boards/{board_id}/powerUps"
        params = self._get_auth_params()
        params["idPlugin"] = powerup_id
        return self._request("POST", url, json=params)

    def disable_powerup(self, board_id, powerup_id):
        url = f"{self.base_url}boards/{board_id}/powerUps/{powerup_id}"
        params = self._get_auth_params()
        return self._request("DELETE", url, params=params)

    @property
    def tools(self):
        return [
            list_boards_tool,
            get_board_tool,
            list_lists_tool,
            list_cards_tool,
            get_card_tool,
            list_comments_tool,
            list_attachments_tool,
            list_checklists_tool,
            list_members_tool,
            create_board_tool,
            create_list_tool,
            create_card_tool,
            update_board_tool,
            update_list_tool,
            update_card_tool,
            add_comment_tool,
            add_attachment_tool,
            add_checklist_tool,
            add_member_to_board_tool,
            add_member_to_card_tool,
            move_card_to_board_tool,
            move_list_to_board_tool,
            delete_card_tool,
            copy_board_tool,
            copy_card_tool,
            enable_powerup_tool,
            disable_powerup_tool,
        ]
