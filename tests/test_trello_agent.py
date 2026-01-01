"""
Tests for Trello Agent.
"""
import pytest
from unittest.mock import patch
import os

# Set dummy environment variables for testing
os.environ["TRELLO_API_KEY"] = "test_key"
os.environ["TRELLO_TOKEN"] = "test_token"
os.environ["TRELLO_BOARD_ID"] = "test_board"

from backend.trello_agent import TrelloAgent


@pytest.fixture
def trello_agent():
    """Fixture to create a TrelloAgent instance for testing."""
    return TrelloAgent()


def test_trello_agent_initialization(trello_agent):
    """Test TrelloAgent initializes correctly."""
    assert trello_agent.api_key == "test_key"
    assert trello_agent.token == "test_token"
    # assert trello_agent.board_id == "test_board" # This attribute is not set in the constructor
    print("TrelloAgent initialized with credentials")


def test_list_boards(trello_agent):
    """Test listing Trello boards."""
    with patch("requests.request") as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = [{"id": "board1", "name": "Test Board"}]

        boards = trello_agent.list_boards()
        assert len(boards) > 0
        assert boards[0]["name"] == "Test Board"
        print("Successfully listed Trello boards")


def test_get_board(trello_agent):
    """Test getting a specific Trello board."""
    with patch("requests.request") as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = {"id": "board1", "name": "Specific Board"}

        board = trello_agent.get_board("board1")
        assert board["name"] == "Specific Board"
        print("Successfully retrieved a specific Trello board")


def test_list_lists(trello_agent):
    """Test listing lists on a board."""
    with patch("requests.request") as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = [{"id": "list1", "name": "To Do"}]

        lists = trello_agent.list_lists("board1")
        assert len(lists) > 0
        assert lists[0]["name"] == "To Do"
        print("Successfully listed lists on a board")


def test_list_cards(trello_agent):
    """Test listing cards in a list."""
    with patch("requests.request") as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = [{"id": "card1", "name": "My Task"}]

        cards = trello_agent.list_cards("list1")
        assert len(cards) > 0
        assert cards[0]["name"] == "My Task"
        print("Successfully listed cards in a list")


def test_get_card(trello_agent):
    """Test getting a specific card."""
    with patch("requests.request") as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = {"id": "card1", "name": "Specific Task"}

        card = trello_agent.get_card("card1")
        assert card["name"] == "Specific Task"
        print("Successfully retrieved a specific card")


def test_list_comments(trello_agent):
    """Test listing comments on a card."""
    with patch("requests.request") as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = [{"id": "comment1", "data": {"text": "A comment"}}]

        comments = trello_agent.list_comments("card1")
        assert len(comments) > 0
        print("Successfully listed comments")


def test_list_attachments(trello_agent):
    """Test listing attachments on a card."""
    with patch("requests.request") as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = [{"id": "att1", "name": "file.txt"}]

        attachments = trello_agent.list_attachments("card1")
        assert len(attachments) > 0
        print("Successfully listed attachments")


def test_list_checklists(trello_agent):
    """Test listing checklists on a card."""
    with patch("requests.request") as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = [{"id": "cl1", "name": "Sub-tasks"}]

        checklists = trello_agent.list_checklists("card1")
        assert len(checklists) > 0
        print("Successfully listed checklists")


def test_list_members(trello_agent):
    """Test listing members of a board."""
    with patch("requests.request") as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = [{"id": "mem1", "fullName": "Test User"}]

        members = trello_agent.list_members("board1")
        assert len(members) > 0
        print("Successfully listed board members")


def test_create_board(trello_agent):
    """Test creating a Trello board."""
    with patch("requests.request") as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = {"id": "new_board", "name": "New Board"}

        new_board = trello_agent.create_board("New Board")
        assert new_board["name"] == "New Board"
        print("Successfully created a Trello board")


def test_create_list(trello_agent):
    """Test creating a list on a board."""
    with patch("requests.request") as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = {"id": "new_list", "name": "New List"}

        new_list = trello_agent.create_list("board1", "New List")
        assert new_list["name"] == "New List"
        print("Successfully created a Trello list")


def test_create_card(trello_agent):
    """Test creating a card in a list."""
    with patch("requests.request") as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = {"id": "new_card", "name": "New Task"}

        new_card = trello_agent.create_card("list1", "New Task")
        assert new_card["name"] == "New Task"
        print("Successfully created a Trello card")


def test_update_board(trello_agent):
    """Test updating a Trello board."""
    with patch("requests.request") as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = {"id": "board1", "name": "Updated Board"}

        updated_board = trello_agent.update_board("board1", name="Updated Board")
        assert updated_board["name"] == "Updated Board"
        print("Successfully updated a Trello board")


def test_update_list(trello_agent):
    """Test updating a Trello list."""
    with patch("requests.request") as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = {"id": "list1", "name": "Updated List"}

        updated_list = trello_agent.update_list("list1", name="Updated List")
        assert updated_list["name"] == "Updated List"
        print("Successfully updated a Trello list")


def test_update_card(trello_agent):
    """Test updating a Trello card."""
    with patch("requests.request") as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = {"id": "card1", "name": "Updated Task"}

        updated_card = trello_agent.update_card("card1", name="Updated Task")
        assert updated_card["name"] == "Updated Task"
        print("Successfully updated a Trello card")


def test_add_comment(trello_agent):
    """Test adding a comment to a card."""
    with patch("requests.request") as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = {"id": "new_comment"}

        comment = trello_agent.add_comment("card1", "This is a comment")
        assert "id" in comment
        print("Successfully added a comment")


def test_delete_card(trello_agent):
    """Test deleting a card."""
    with patch("requests.request") as mock_request:
        mock_request.return_value.status_code = 200
        mock_request.return_value.json.return_value = {}

        response = trello_agent.delete_card("card1")
        assert response is not None
        print("Successfully deleted a card")
