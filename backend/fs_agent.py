import asyncio
import os
from pathlib import Path
import aiofiles

class FileSystemAgent:
    def __init__(self, project_manager):
        self.project_manager = project_manager

    def _resolve_path(self, path):
        """Resolves the path relative to the current project root."""
        current_project_path = self.project_manager.get_current_project_path()

        # If absolute path is provided, try to make it relative or just use basename for safety
        if os.path.isabs(path):
            # Try to make relative to project root if it starts with it
            try:
                rel_path = Path(path).relative_to(current_project_path)
                final_path = current_project_path / rel_path
            except ValueError:
                # Outside project root? Use basename in project root.
                filename = os.path.basename(path)
                final_path = current_project_path / filename
        else:
            final_path = current_project_path / path

        return final_path

    async def write_file(self, path, content):
        """Writes content to a file asynchronously."""
        final_path = self._resolve_path(path)

        try:
            # Ensure directory exists (can block slightly, but minimal impact compared to file I/O)
            dir_name = os.path.dirname(final_path)
            if dir_name:
                def _make_dirs():
                    os.makedirs(dir_name, exist_ok=True)
                await asyncio.to_thread(_make_dirs)

            async with aiofiles.open(final_path, 'w', encoding='utf-8') as f:
                await f.write(content)
            return f"File '{final_path}' written successfully to project '{self.project_manager.current_project}'."
        except Exception as e:
            return f"Failed to write file '{path}': {str(e)}"

    async def read_file(self, path):
        """Reads content from a file asynchronously."""
        final_path = self._resolve_path(path)

        try:
            # Check existence (minimal block)
            def _check_exists():
                return os.path.exists(final_path)
            exists = await asyncio.to_thread(_check_exists)

            if not exists:
                return f"File '{final_path}' does not exist."

            async with aiofiles.open(final_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            return f"Content of '{final_path}':\n{content}"
        except Exception as e:
            return f"Failed to read file '{path}': {str(e)}"

    async def read_directory(self, path):
        """Lists contents of a directory asynchronously."""
        final_path = self._resolve_path(path)

        def _perform_list():
            if not os.path.exists(final_path):
                return f"Directory '{final_path}' does not exist."
            if not os.path.isdir(final_path):
                return f"Path '{final_path}' is not a directory."
            items = os.listdir(final_path)
            return f"Contents of '{final_path}': {', '.join(items)}"

        try:
            return await asyncio.to_thread(_perform_list)
        except Exception as e:
            return f"Failed to read directory '{path}': {str(e)}"
