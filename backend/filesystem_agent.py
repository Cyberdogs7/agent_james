import os
import datetime

INCLUDE_RAW_LOGS = os.getenv("INCLUDE_RAW_LOGS", "True").lower() == "true"

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

class FileSystemAgent:
    def __init__(self, project_manager=None, session=None, on_project_update=None):
        self.tools = [write_file_tool, read_directory_tool, read_file_tool]
        self.project_manager = project_manager
        self.session = session
        self.on_project_update = on_project_update

    async def write_file(self, path, content):
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [FS] Writing file: '{path}'")

        # Auto-create project if stuck in temp
        if self.project_manager.current_project == "temp":
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            new_project_name = f"Project_{timestamp}"
            if INCLUDE_RAW_LOGS:
                print(f"[ADA DEBUG] [FS] Auto-creating project: {new_project_name}")

            success, msg = self.project_manager.create_project(new_project_name)
            if success:
                self.project_manager.switch_project(new_project_name)
                # Notify User
                try:
                    await self.session.send(input=f"System Notification: Automatic Project Creation. Switched to new project '{new_project_name}'.", end_of_turn=False)
                    if self.on_project_update:
                         self.on_project_update(new_project_name)
                except Exception as e:
                    if INCLUDE_RAW_LOGS:
                        print(f"[ADA DEBUG] [ERR] Failed to notify auto-project: {e}")

        filename = os.path.basename(path)
        current_project_path = self.project_manager.get_current_project_path()
        final_path = current_project_path / filename

        if not os.path.isabs(path):
             final_path = current_project_path / path

        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [FS] Resolved path: '{final_path}'")

        try:
            os.makedirs(os.path.dirname(final_path), exist_ok=True)
            with open(final_path, 'w', encoding='utf-8') as f:
                f.write(content)
            result = f"File '{final_path}' written successfully to project '{self.project_manager.current_project}'."
        except Exception as e:
            result = f"Failed to write file '{path}': {str(e)}"

        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [FS] Result: {result}")
        try:
             await self.session.send(input=f"System Notification: {result}", end_of_turn=True)
        except Exception as e:
             if INCLUDE_RAW_LOGS:
                print(f"[ADA DEBUG] [ERR] Failed to send fs result: {e}")
        return result

    async def read_directory(self, path):
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [FS] Reading directory: '{path}'")

        current_project_path = self.project_manager.get_current_project_path()
        final_path = current_project_path / path if not os.path.isabs(path) else path

        try:
            if not os.path.exists(final_path):
                result = f"Directory '{final_path}' does not exist."
            else:
                items = os.listdir(final_path)
                result = f"Contents of '{final_path}': {', '.join(items)}"
        except Exception as e:
            result = f"Failed to read directory '{path}': {str(e)}"

        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [FS] Result: {result}")
        try:
             await self.session.send(input=f"System Notification: {result}", end_of_turn=True)
        except Exception as e:
             if INCLUDE_RAW_LOGS:
                print(f"[ADA DEBUG] [ERR] Failed to send fs result: {e}")
        return result

    async def read_file(self, path):
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [FS] Reading file: '{path}'")

        current_project_path = self.project_manager.get_current_project_path()
        final_path = current_project_path / path if not os.path.isabs(path) else path

        try:
            if not os.path.exists(final_path):
                result = f"File '{final_path}' does not exist."
            else:
                with open(final_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                result = f"Content of '{final_path}':\n{content}"
        except Exception as e:
            result = f"Failed to read file '{path}': {str(e)}"

        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [FS] Result: {result}")
        try:
             await self.session.send(input=f"System Notification: {result}", end_of_turn=True)
        except Exception as e:
             if INCLUDE_RAW_LOGS:
                print(f"[ADA DEBUG] [ERR] Failed to send fs result: {e}")
        return result
