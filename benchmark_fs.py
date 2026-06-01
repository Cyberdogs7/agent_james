import asyncio
import time
import os
import tempfile
from pathlib import Path

# Create dummy ProjectManager
class DummyProjectManager:
    def get_current_project_path(self):
        return Path(tempfile.gettempdir())

    @property
    def current_project(self):
        return "dummy_project"

# Old FileSystemAgent
class FileSystemAgentOld:
    def __init__(self, project_manager):
        self.project_manager = project_manager

    def _resolve_path(self, path):
        current_project_path = self.project_manager.get_current_project_path()
        if os.path.isabs(path):
            try:
                rel_path = Path(path).relative_to(current_project_path)
                final_path = current_project_path / rel_path
            except ValueError:
                filename = os.path.basename(path)
                final_path = current_project_path / filename
        else:
            final_path = current_project_path / path
        return final_path

    async def write_file(self, path, content):
        final_path = self._resolve_path(path)
        def _perform_write():
            os.makedirs(os.path.dirname(final_path), exist_ok=True)
            with open(final_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"File '{final_path}' written successfully"
        try:
            return await asyncio.to_thread(_perform_write)
        except Exception as e:
            return f"Failed: {str(e)}"

    async def read_file(self, path):
        final_path = self._resolve_path(path)
        def _perform_read():
            if not os.path.exists(final_path):
                return "Not exist"
            with open(final_path, 'r', encoding='utf-8') as f:
                return f.read()
        try:
            return await asyncio.to_thread(_perform_read)
        except Exception as e:
            return f"Failed: {str(e)}"

async def main():
    agent = FileSystemAgentOld(DummyProjectManager())

    # Benchmark write
    start = time.perf_counter()
    tasks = [agent.write_file(f"test_{i}.txt", f"content {i}") for i in range(1000)]
    await asyncio.gather(*tasks)
    write_time = time.perf_counter() - start
    print(f"Old write (1000 files): {write_time:.4f} seconds")

    # Benchmark read
    start = time.perf_counter()
    tasks = [agent.read_file(f"test_{i}.txt") for i in range(1000)]
    await asyncio.gather(*tasks)
    read_time = time.perf_counter() - start
    print(f"Old read (1000 files): {read_time:.4f} seconds")

if __name__ == "__main__":
    asyncio.run(main())
