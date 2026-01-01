import os
import re


class WritingAgent:
    def __init__(self, sio):
        self.sio = sio
        self.active_project = None
        self.writing_projects_dir = "writing_projects"
        if not os.path.exists(self.writing_projects_dir):
            os.makedirs(self.writing_projects_dir)

    def _sanitize_filename(self, name):
        """Sanitizes a string to be a valid filename."""
        return re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')

    def create_new_book(self, book_title: str):
        """
        Creates a new book project with a standard directory structure.
        Args:
            book_title (str): The title of the new book.
        """
        sanitized_title = self._sanitize_filename(book_title)
        book_path = os.path.join(self.writing_projects_dir, sanitized_title)
        if os.path.exists(book_path):
            return f"Error: A book project named '{book_title}' already exists."

        os.makedirs(book_path)
        subfolders = ["Chapters", "Characters", "Worldbuilding", "Notes"]
        for folder in subfolders:
            os.makedirs(os.path.join(book_path, folder))

        self.active_project = sanitized_title
        return f"Successfully created new book project '{book_title}'. It is now the active project."

    def set_active_book(self, book_title: str):
        """
        Sets a book as the active project for subsequent commands.
        Args:
            book_title (str): The title of the book to set as active.
        """
        sanitized_title = self._sanitize_filename(book_title)
        book_path = os.path.join(self.writing_projects_dir, sanitized_title)
        if not os.path.exists(book_path):
            return f"Error: No book project named '{book_title}' found."

        self.active_project = sanitized_title
        return f"'{book_title}' is now the active writing project."

    def list_books(self):
        """
        Lists all available book projects.
        """
        try:
            books = [d for d in os.listdir(self.writing_projects_dir) if os.path.isdir(os.path.join(self.writing_projects_dir, d))]
            if not books:
                return "No book projects found."
            return "Available book projects:\n- " + "\n- ".join(books)
        except FileNotFoundError:
            return "The writing projects directory has not been created yet."

    def create_new_character(self, character_name: str):
        """
        Creates a new character file with a template in the active project.
        Args:
            character_name (str): The name of the character.
        """
        if not self.active_project:
            return "Error: No active book project. Please create a new book or set an active one first."

        sanitized_name = self._sanitize_filename(character_name)
        character_path = os.path.join(self.writing_projects_dir, self.active_project, "Characters", f"{sanitized_name}.md")

        if os.path.exists(character_path):
            return f"Error: A character named '{character_name}' already exists in the project '{self.active_project}'."

        template = (
            f"# {character_name}\n\n"
            "## Description\n\n"
            "...\n\n"
            "## Backstory\n\n"
            "...\n\n"
            "## Goals\n\n"
            "...\n"
        )

        with open(character_path, "w") as f:
            f.write(template)

        return f"Created new character '{character_name}' in project '{self.active_project}'."

    @property
    def tools(self):
        return [
            self.create_new_book,
            self.set_active_book,
            self.list_books,
            self.create_new_character,
        ]
