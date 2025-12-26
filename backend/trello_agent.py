import os
import requests
import time

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
