import os
import shutil
import pytest
from pathlib import Path
import sys

# Add backend to path
BACKEND_DIR = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from writing_agent import WritingAgent

@pytest.fixture
def writing_agent(tmp_path):
    """Fixture to create a WritingAgent instance with a temporary projects directory."""
    # Temporarily change the current working directory to the tmp_path
    # so that the agent creates its directory inside the temp folder.
    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    agent = WritingAgent(socketio=None) # socketio is not used in these methods

    yield agent

    # Teardown: clean up the created directory and restore cwd
    projects_dir = tmp_path / agent.writing_projects_dir
    if projects_dir.exists():
        shutil.rmtree(projects_dir)
    os.chdir(original_cwd)

class TestWritingAgent:
    """Tests for the WritingAgent class."""

    def test_create_new_book(self, writing_agent):
        """Test creating a new book project."""
        book_title = "My First Book"
        result = writing_agent.create_new_book(book_title)

        assert "Successfully created" in result
        assert writing_agent.active_project == "My_First_Book"

        book_path = Path(writing_agent.writing_projects_dir) / "My_First_Book"
        assert book_path.is_dir()

        expected_subfolders = ["Chapters", "Characters", "Worldbuilding", "Notes"]
        for folder in expected_subfolders:
            assert (book_path / folder).is_dir()

        # Test creating a book that already exists
        error_result = writing_agent.create_new_book(book_title)
        assert "Error: A book project named" in error_result

    def test_list_books(self, writing_agent):
        """Test listing all book projects."""
        # Test with no books
        assert "No book projects found" in writing_agent.list_books()

        # Test after creating books
        writing_agent.create_new_book("Book One")
        writing_agent.create_new_book("Book Two")

        book_list = writing_agent.list_books()
        assert "Book_One" in book_list
        assert "Book_Two" in book_list

    def test_set_active_book(self, writing_agent):
        """Test setting the active book project."""
        writing_agent.create_new_book("Book Alpha")
        writing_agent.create_new_book("Book Beta")

        # The last created book should be active
        assert writing_agent.active_project == "Book_Beta"

        # Set active book to the first one
        result = writing_agent.set_active_book("Book Alpha")
        assert "'Book Alpha' is now the active writing project" in result
        assert writing_agent.active_project == "Book_Alpha"

        # Test setting a non-existent book
        error_result = writing_agent.set_active_book("Non Existent Book")
        assert "Error: No book project named" in error_result

    def test_create_new_character(self, writing_agent):
        """Test creating a new character file."""
        # Test with no active project
        error_result = writing_agent.create_new_character("Gandalf")
        assert "Error: No active book project" in error_result

        # Create a book to activate a project
        writing_agent.create_new_book("The Lord of the Rings")

        character_name = "Frodo Baggins"
        result = writing_agent.create_new_character(character_name)

        assert f"Created new character '{character_name}'" in result

        character_file = Path(writing_agent.writing_projects_dir) / "The_Lord_of_the_Rings" / "Characters" / "Frodo_Baggins.md"
        assert character_file.is_file()

        # Check file content for the template
        content = character_file.read_text()
        assert f"# {character_name}" in content
        assert "## Description" in content
        assert "## Backstory" in content
        assert "## Goals" in content

        # Test creating a character that already exists
        error_result = writing_agent.create_new_character(character_name)
        assert "Error: A character named" in error_result
