import unittest
from unittest.mock import patch, AsyncMock
import sys
import os
import asyncio

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.trello_agent import TrelloAgent

class TestTrelloAgent(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.agent = TrelloAgent()
        self.agent.api_key = "test_key"
        self.agent.token = "test_token"

    @patch('backend.trello_agent.TrelloAgent._request', new_callable=AsyncMock)
    async def test_list_boards(self, mock_request):
        mock_request.return_value = [{"id": "1", "name": "Test Board"}]
        boards = await self.agent.list_boards()
        self.assertEqual(len(boards), 1)
        self.assertEqual(boards[0]["name"], "Test Board")
        mock_request.assert_called_with(
            "GET",
            "https://api.trello.com/1/members/me/boards",
            params={"key": "test_key", "token": "test_token"}
        )

    @patch('backend.trello_agent.TrelloAgent._request', new_callable=AsyncMock)
    async def test_get_board(self, mock_request):
        mock_request.return_value = {"id": "1", "name": "Test Board"}
        board = await self.agent.get_board("1")
        self.assertEqual(board["name"], "Test Board")
        mock_request.assert_called_with(
            "GET",
            "https://api.trello.com/1/boards/1",
            params={"key": "test_key", "token": "test_token"}
        )

    @patch('backend.trello_agent.TrelloAgent._request', new_callable=AsyncMock)
    async def test_list_lists(self, mock_request):
        mock_request.return_value = [{"id": "1", "name": "Test List"}]
        lists = await self.agent.list_lists("1")
        self.assertEqual(len(lists), 1)
        self.assertEqual(lists[0]["name"], "Test List")
        mock_request.assert_called_with(
            "GET",
            "https://api.trello.com/1/boards/1/lists",
            params={"key": "test_key", "token": "test_token"}
        )

    @patch('backend.trello_agent.TrelloAgent._request', new_callable=AsyncMock)
    async def test_list_cards(self, mock_request):
        mock_request.return_value = [{"id": "1", "name": "Test Card"}]
        cards = await self.agent.list_cards("1")
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["name"], "Test Card")
        mock_request.assert_called_with(
            "GET",
            "https://api.trello.com/1/lists/1/cards",
            params={"key": "test_key", "token": "test_token"}
        )

    @patch('backend.trello_agent.TrelloAgent._request', new_callable=AsyncMock)
    async def test_get_card(self, mock_request):
        mock_request.return_value = {"id": "1", "name": "Test Card"}
        card = await self.agent.get_card("1")
        self.assertEqual(card["name"], "Test Card")
        mock_request.assert_called_with(
            "GET",
            "https://api.trello.com/1/cards/1",
            params={"key": "test_key", "token": "test_token"}
        )

    @patch('backend.trello_agent.TrelloAgent._request', new_callable=AsyncMock)
    async def test_list_comments(self, mock_request):
        mock_request.return_value = [{"id": "1", "data": {"text": "Test Comment"}}]
        comments = await self.agent.list_comments("1")
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0]["data"]["text"], "Test Comment")
        mock_request.assert_called_with(
            "GET",
            "https://api.trello.com/1/cards/1/actions",
            params={"key": "test_key", "token": "test_token", "filter": "commentCard"}
        )

    @patch('backend.trello_agent.TrelloAgent._request', new_callable=AsyncMock)
    async def test_list_attachments(self, mock_request):
        mock_request.return_value = [{"id": "1", "name": "Test Attachment"}]
        attachments = await self.agent.list_attachments("1")
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0]["name"], "Test Attachment")
        mock_request.assert_called_with(
            "GET",
            "https://api.trello.com/1/cards/1/attachments",
            params={"key": "test_key", "token": "test_token"}
        )

    @patch('backend.trello_agent.TrelloAgent._request', new_callable=AsyncMock)
    async def test_list_checklists(self, mock_request):
        mock_request.return_value = [{"id": "1", "name": "Test Checklist"}]
        checklists = await self.agent.list_checklists("1")
        self.assertEqual(len(checklists), 1)
        self.assertEqual(checklists[0]["name"], "Test Checklist")
        mock_request.assert_called_with(
            "GET",
            "https://api.trello.com/1/cards/1/checklists",
            params={"key": "test_key", "token": "test_token"}
        )

    @patch('backend.trello_agent.TrelloAgent._request', new_callable=AsyncMock)
    async def test_list_members(self, mock_request):
        mock_request.return_value = [{"id": "1", "fullName": "Test Member"}]
        members = await self.agent.list_members("1")
        self.assertEqual(len(members), 1)
        self.assertEqual(members[0]["fullName"], "Test Member")
        mock_request.assert_called_with(
            "GET",
            "https://api.trello.com/1/boards/1/members",
            params={"key": "test_key", "token": "test_token"}
        )

    @patch('backend.trello_agent.TrelloAgent._request', new_callable=AsyncMock)
    async def test_create_board(self, mock_request):
        mock_request.return_value = {"id": "1", "name": "New Board"}
        board = await self.agent.create_board("New Board", "A new board.")
        self.assertEqual(board["name"], "New Board")
        mock_request.assert_called_with(
            "POST",
            "https://api.trello.com/1/boards",
            params={"key": "test_key", "token": "test_token", "name": "New Board", "desc": "A new board."}
        )

    @patch('backend.trello_agent.TrelloAgent._request', new_callable=AsyncMock)
    async def test_create_list(self, mock_request):
        mock_request.return_value = {"id": "1", "name": "New List"}
        trello_list = await self.agent.create_list("1", "New List")
        self.assertEqual(trello_list["name"], "New List")
        mock_request.assert_called_with(
            "POST",
            "https://api.trello.com/1/boards/1/lists",
            params={"key": "test_key", "token": "test_token", "name": "New List"}
        )

    @patch('backend.trello_agent.TrelloAgent._request', new_callable=AsyncMock)
    async def test_create_card(self, mock_request):
        mock_request.return_value = {"id": "1", "name": "New Card"}
        card = await self.agent.create_card("1", "New Card", "A new card.")
        self.assertEqual(card["name"], "New Card")
        mock_request.assert_called_with(
            "POST",
            "https://api.trello.com/1/cards",
            params={"key": "test_key", "token": "test_token", "idList": "1", "name": "New Card", "desc": "A new card."}
        )

    @patch('backend.trello_agent.TrelloAgent._request', new_callable=AsyncMock)
    async def test_update_board(self, mock_request):
        mock_request.return_value = {"id": "1", "name": "Updated Board"}
        board = await self.agent.update_board("1", "Updated Board")
        self.assertEqual(board["name"], "Updated Board")
        mock_request.assert_called_with(
            "PUT",
            "https://api.trello.com/1/boards/1",
            params={"key": "test_key", "token": "test_token", "name": "Updated Board"}
        )

    @patch('backend.trello_agent.TrelloAgent._request', new_callable=AsyncMock)
    async def test_update_list(self, mock_request):
        mock_request.return_value = {"id": "1", "name": "Updated List"}
        trello_list = await self.agent.update_list("1", "Updated List")
        self.assertEqual(trello_list["name"], "Updated List")
        mock_request.assert_called_with(
            "PUT",
            "https://api.trello.com/1/lists/1",
            params={"key": "test_key", "token": "test_token", "name": "Updated List"}
        )

    @patch('backend.trello_agent.TrelloAgent._request', new_callable=AsyncMock)
    async def test_update_card(self, mock_request):
        mock_request.return_value = {"id": "1", "name": "Updated Card"}
        card = await self.agent.update_card("1", "Updated Card")
        self.assertEqual(card["name"], "Updated Card")
        mock_request.assert_called_with(
            "PUT",
            "https://api.trello.com/1/cards/1",
            params={"key": "test_key", "token": "test_token", "name": "Updated Card"}
        )

    @patch('backend.trello_agent.TrelloAgent._request', new_callable=AsyncMock)
    async def test_add_comment(self, mock_request):
        mock_request.return_value = {"id": "1", "data": {"text": "New Comment"}}
        comment = await self.agent.add_comment("1", "New Comment")
        self.assertEqual(comment["data"]["text"], "New Comment")
        mock_request.assert_called_with(
            "POST",
            "https://api.trello.com/1/cards/1/actions/comments",
            params={"key": "test_key", "token": "test_token", "text": "New Comment"}
        )

    @patch('backend.trello_agent.TrelloAgent._request', new_callable=AsyncMock)
    async def test_delete_card(self, mock_request):
        mock_request.return_value = {}
        await self.agent.delete_card("1")
        mock_request.assert_called_with(
            "DELETE",
            "https://api.trello.com/1/cards/1",
            params={"key": "test_key", "token": "test_token"}
        )

if __name__ == '__main__':
    unittest.main()
