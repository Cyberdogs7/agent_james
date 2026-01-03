import os
import requests
import time
import asyncio

class TrelloAgent:
    def __init__(self):
        self.api_key = os.getenv("TRELLO_API_KEY")
        self.token = os.getenv("TRELLO_TOKEN")
        self.base_url = "https://api.trello.com/1/"

    def _get_auth_params(self):
        return {"key": self.api_key, "token": self.token}

    async def _request(self, method, url, **kwargs):
        """Helper method to make requests with retry logic."""
        max_retries = 3
        base_delay = 1
        for attempt in range(max_retries):
            try:
                response = await asyncio.to_thread(requests.request, method, url, **kwargs)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    delay = base_delay * (2 ** attempt)
                    print(f"Rate limited (429) for Trello API at {url}. Retrying in {delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                else:
                    print(f"HTTP error occurred: {e}")
                    return None
            except Exception as e:
                print(f"An error occurred: {e}")
                return None
        return None

    async def list_boards(self):
        url = f"{self.base_url}members/me/boards"
        params = self._get_auth_params()
        return await self._request("GET", url, params=params)

    async def get_board(self, board_id):
        url = f"{self.base_url}boards/{board_id}"
        params = self._get_auth_params()
        return await self._request("GET", url, params=params)

    async def list_lists(self, board_id):
        url = f"{self.base_url}boards/{board_id}/lists"
        params = self._get_auth_params()
        return await self._request("GET", url, params=params)

    async def list_cards(self, list_id):
        url = f"{self.base_url}lists/{list_id}/cards"
        params = self._get_auth_params()
        return await self._request("GET", url, params=params)

    async def get_card(self, card_id):
        url = f"{self.base_url}cards/{card_id}"
        params = self._get_auth_params()
        return await self._request("GET", url, params=params)

    async def list_comments(self, card_id):
        url = f"{self.base_url}cards/{card_id}/actions"
        params = self._get_auth_params()
        params["filter"] = "commentCard"
        return await self._request("GET", url, params=params)

    async def list_attachments(self, card_id):
        url = f"{self.base_url}cards/{card_id}/attachments"
        params = self._get_auth_params()
        return await self._request("GET", url, params=params)

    async def list_checklists(self, card_id):
        url = f"{self.base_url}cards/{card_id}/checklists"
        params = self._get_auth_params()
        return await self._request("GET", url, params=params)

    async def list_members(self, board_id):
        url = f"{self.base_url}boards/{board_id}/members"
        params = self._get_auth_params()
        return await self._request("GET", url, params=params)

    async def create_board(self, name, description=None):
        url = f"{self.base_url}boards"
        params = self._get_auth_params()
        params["name"] = name
        if description:
            params["desc"] = description
        return await self._request("POST", url, params=params)

    async def create_list(self, board_id, name):
        url = f"{self.base_url}boards/{board_id}/lists"
        params = self._get_auth_params()
        params["name"] = name
        return await self._request("POST", url, params=params)

    async def create_card(self, list_id, name, description=None):
        url = f"{self.base_url}cards"
        params = self._get_auth_params()
        params["idList"] = list_id
        params["name"] = name
        if description:
            params["desc"] = description
        return await self._request("POST", url, params=params)

    async def update_board(self, board_id, name=None, description=None):
        url = f"{self.base_url}boards/{board_id}"
        params = self._get_auth_params()
        if name:
            params["name"] = name
        if description:
            params["desc"] = description
        return await self._request("PUT", url, params=params)

    async def update_list(self, list_id, name=None, pos=None):
        url = f"{self.base_url}lists/{list_id}"
        params = self._get_auth_params()
        if name:
            params["name"] = name
        if pos:
            params["pos"] = pos
        return await self._request("PUT", url, params=params)

    async def update_card(self, card_id, name=None, description=None, idList=None):
        url = f"{self.base_url}cards/{card_id}"
        params = self._get_auth_params()
        if name:
            params["name"] = name
        if description:
            params["desc"] = description
        if idList:
            params["idList"] = idList
        return await self._request("PUT", url, params=params)

    async def add_comment(self, card_id, text):
        url = f"{self.base_url}cards/{card_id}/actions/comments"
        params = self._get_auth_params()
        params["text"] = text
        return await self._request("POST", url, params=params)

    async def add_attachment(self, card_id, url):
        url = f"{self.base_url}cards/{card_id}/attachments"
        params = self._get_auth_params()
        params["url"] = url
        return await self._request("POST", url, params=params)

    async def add_checklist(self, card_id, name):
        url = f"{self.base_url}cards/{card_id}/checklists"
        params = self._get_auth_params()
        params["name"] = name
        return await self._request("POST", url, params=params)

    async def add_member_to_board(self, board_id, email):
        url = f"{self.base_url}boards/{board_id}/members"
        params = self._get_auth_params()
        params["email"] = email
        params["type"] = "normal"
        return await self._request("PUT", url, json=params)

    async def add_member_to_card(self, card_id, member_id):
        url = f"{self.base_url}cards/{card_id}/idMembers"
        params = self._get_auth_params()
        params["value"] = member_id
        return await self._request("POST", url, params=params)

    async def move_card_to_board(self, card_id, board_id):
        url = f"{self.base_url}cards/{card_id}"
        params = self._get_auth_params()
        params["idBoard"] = board_id
        return await self._request("PUT", url, params=params)

    async def move_list_to_board(self, list_id, board_id):
        url = f"{self.base_url}lists/{list_id}/move"
        params = self._get_auth_params()
        params["value"] = board_id
        return await self._request("PUT", url, params=params)

    async def delete_card(self, card_id):
        url = f"{self.base_url}cards/{card_id}"
        params = self._get_auth_params()
        return await self._request("DELETE", url, params=params)

    async def copy_board(self, board_id, name):
        url = f"{self.base_url}boards"
        params = self._get_auth_params()
        params["idBoardSource"] = board_id
        params["name"] = name
        return await self._request("POST", url, params=params)

    async def copy_card(self, card_id, list_id, name=None):
        url = f"{self.base_url}cards"
        params = self._get_auth_params()
        params["idCardSource"] = card_id
        params["idList"] = list_id
        if name:
            params["name"] = name
        return await self._request("POST", url, params=params)

    async def enable_powerup(self, board_id, powerup_id):
        url = f"{self.base_url}boards/{board_id}/powerUps"
        params = self._get_auth_params()
        params["idPlugin"] = powerup_id
        return await self._request("POST", url, json=params)

    async def disable_powerup(self, board_id, powerup_id):
        url = f"{self.base_url}boards/{board_id}/powerUps/{powerup_id}"
        params = self._get_auth_params()
        return await self._request("DELETE", url, params=params)

    async def search_cards(self, query):
        """Searches for cards across all boards the user is a member of."""
        url = f"{self.base_url}search"
        params = self._get_auth_params()
        params["query"] = query
        params["modelTypes"] = "cards"
        params["card_fields"] = "name,desc,url,idBoard"
        params["cards_limit"] = 50
        search_result = await self._request("GET", url, params=params)
        if search_result and "cards" in search_result:
            cards = search_result["cards"]
            board_ids = {card.get("idBoard") for card in cards if card.get("idBoard")}

            board_tasks = [self.get_board(board_id) for board_id in board_ids]
            board_results = await asyncio.gather(*board_tasks)

            board_names = {board_data['id']: board_data.get("name", "Unknown Board") for board_data in board_results if board_data}

            for card in cards:
                card["boardName"] = board_names.get(card.get("idBoard"), "Unknown Board")

            return cards
        return []
