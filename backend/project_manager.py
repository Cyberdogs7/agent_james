import os
import json
import shutil
import time
from pathlib import Path
try:
    from backend.writing_prompts import WRITING_MODE_SYSTEM_PROMPT
except ImportError:
    from writing_prompts import WRITING_MODE_SYSTEM_PROMPT

DEFAULT_SYSTEM_PROMPT = "Your name is James and you speak with a british accent at all times.. You have a witty and professional personality, like a cheeky butler. Sarcasm is welcome. Your creator is Chad, and you address him as 'Sir'. When answering, respond using complete and concise sentences to keep a quick pacing and keep the conversation flowing. You are a professional assistant."

class ProjectManager:
    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self.projects_dir = self.workspace_root / "projects"
        self.current_project = "temp"
        
        # Ensure projects root exists
        if not self.projects_dir.exists():
            self.projects_dir.mkdir(parents=True)

        # Ensure all existing projects have a config file
        for project_dir in self.projects_dir.iterdir():
            if project_dir.is_dir():
                config_path = project_dir / "config.json"
                if not config_path.exists():
                    print(f"[ProjectManager] Creating default config for existing project: {project_dir.name}")
                    self._create_default_config(project_dir)
            
        # Clear temp project on startup if it exists
        temp_path = self.projects_dir / "temp"
        if temp_path.exists():
            print("[ProjectManager] Clearing temp project...")
            shutil.rmtree(temp_path)
            
        # Ensure temp project receives fresh creation
        self.create_project("temp")

    def create_project(self, name: str):
        """Creates a new project directory with subfolders."""
        # Sanitize name to be safe for filesystem
        safe_name = "".join([c for c in name if c.isalnum() or c in (' ', '-', '_')]).strip()
        project_path = self.projects_dir / safe_name
        
        if not project_path.exists():
            project_path.mkdir()
            (project_path / "cad").mkdir()
            (project_path / "browser").mkdir()
            self._create_default_config(project_path)
            print(f"[ProjectManager] Created project: {safe_name}")
            return True, f"Project '{safe_name}' created."
        return False, f"Project '{safe_name}' already exists."

    def _create_default_config(self, project_path):
        """Creates a default config.json file in the project directory."""
        config_path = project_path / "config.json"
        DEFAULT_CONFIG = {
            "system_prompt": DEFAULT_SYSTEM_PROMPT,
            "jules_api_key": "",
            "voice_name": "Sadaltager"
        }
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)

    def get_project_config(self):
        """Reads and returns the config for the current project."""
        config_path = self.get_current_project_path() / "config.json"
        if not config_path.exists():
            return {}
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}

    def update_project_config(self, new_config: dict):
        """Updates and saves the config for the current project."""
        config_path = self.get_current_project_path() / "config.json"
        current_config = self.get_project_config()
        current_config.update(new_config)
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(current_config, f, indent=4)
            return True, "Configuration updated successfully."
        except Exception as e:
            return False, f"Failed to update configuration: {e}"

    def switch_project(self, name: str):
        """Switches the active project context."""
        safe_name = "".join([c for c in name if c.isalnum() or c in (' ', '-', '_')]).strip()
        project_path = self.projects_dir / safe_name
        
        if project_path.exists():
            self.current_project = safe_name
            print(f"[ProjectManager] Switched to project: {safe_name}")
            return True, f"Switched to project '{safe_name}'."
        return False, f"Project '{safe_name}' does not exist."

    def list_projects(self):
        """Returns a list of available projects."""
        return [d.name for d in self.projects_dir.iterdir() if d.is_dir()]

    def get_current_project_path(self):
        return self.projects_dir / self.current_project

    def log_chat(self, sender: str, text: str):
        """Appends a chat message to the current project's history."""
        log_file = self.get_current_project_path() / "chat_history.jsonl"
        entry = {
            "timestamp": time.time(),
            "sender": sender,
            "text": text
        }
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def save_cad_artifact(self, source_path: str, prompt: str):
        """Copies a generated CAD file to the project's 'cad' folder."""
        if not os.path.exists(source_path):
            print(f"[ProjectManager] [ERR] Source file not found: {source_path}")
            return None

        # Create a filename based on timestamp and prompt
        timestamp = int(time.time())
        # Brief sanitization of prompt for filename
        safe_prompt = "".join([c for c in prompt if c.isalnum() or c in (' ', '-', '_')])[:30].strip().replace(" ", "_")
        filename = f"{timestamp}_{safe_prompt}.stl"
        
        dest_path = self.get_current_project_path() / "cad" / filename
        
        try:
            shutil.copy2(source_path, dest_path)
            print(f"[ProjectManager] Saved CAD artifact to: {dest_path}")
            return str(dest_path)
        except Exception as e:
            print(f"[ProjectManager] [ERR] Failed to save artifact: {e}")
            return None

    def get_project_context(self, max_file_size: int = 10000) -> str:
        """
        Gathers context about the current project for the AI.
        Lists all files and reads text file contents (up to max_file_size bytes).
        """
        project_path = self.get_current_project_path()
        if not project_path.exists():
            return f"Project '{self.current_project}' does not exist."

        context_lines = [f"=== Project Context: '{self.current_project}' ==="]
        context_lines.append(f"Project directory: {project_path}")
        context_lines.append("")

        # List all files recursively
        all_files = []
        for root, dirs, files in os.walk(project_path):
            for f in files:
                rel_path = os.path.relpath(os.path.join(root, f), project_path)
                all_files.append(rel_path)

        if not all_files:
            context_lines.append("(No files in project yet)")
        else:
            context_lines.append(f"Files ({len(all_files)} total):")
            for f in all_files:
                context_lines.append(f"  - {f}")

        context_lines.append("")

        # Read text files (skip binary and large files)
        text_extensions = {'.txt', '.py', '.js', '.jsx', '.ts', '.tsx', '.json', '.md', '.html', '.css', '.jsonl'}
        for rel_path in all_files:
            ext = os.path.splitext(rel_path)[1].lower()
            if ext not in text_extensions:
                continue

            full_path = project_path / rel_path
            try:
                file_size = full_path.stat().st_size
                if file_size > max_file_size:
                    context_lines.append(f"--- {rel_path} (too large: {file_size} bytes, skipped) ---")
                    continue

                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                context_lines.append(f"--- {rel_path} ---")
                context_lines.append(content)
                context_lines.append("")
            except Exception as e:
                context_lines.append(f"--- {rel_path} (error reading: {e}) ---")

        return "\n".join(context_lines)

    def get_recent_chat_history(self, limit: int = 10):
        """Returns the last 'limit' chat messages from history."""
        log_file = self.get_current_project_path() / "chat_history.jsonl"
        if not log_file.exists():
            return []
            
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                
            # Parse last N lines
            history = []
            for line in lines[-limit:]:
                try:
                    entry = json.loads(line)
                    history.append(entry)
                except json.JSONDecodeError:
                    continue
            return history
        except Exception as e:
            print(f"[ProjectManager] [ERR] Failed to read chat history: {e}")
            return []

    def save_jules_session(self, session_id: str, title: str):
        """Saves Jules session information to local memory."""
        sessions_file = self.get_current_project_path() / "jules_sessions.json"
        sessions = []
        if sessions_file.exists():
            try:
                with open(sessions_file, "r", encoding="utf-8") as f:
                    sessions = json.load(f)
            except Exception as e:
                print(f"[ProjectManager] [ERR] Failed to read jules sessions: {e}")

        # Check if session already exists
        for s in sessions:
            if s['id'] == session_id:
                s['title'] = title
                break
        else:
            sessions.append({"id": session_id, "title": title, "timestamp": time.time()})

        try:
            with open(sessions_file, "w", encoding="utf-8") as f:
                json.dump(sessions, f, indent=4)
            print(f"[ProjectManager] Saved Jules session: {title} ({session_id})")
        except Exception as e:
            print(f"[ProjectManager] [ERR] Failed to save jules session: {e}")

    def get_jules_sessions(self):
        """Returns the list of saved Jules sessions for the current project."""
        sessions_file = self.get_current_project_path() / "jules_sessions.json"
        if not sessions_file.exists():
            return []
        try:
            with open(sessions_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ProjectManager] [ERR] Failed to read jules sessions: {e}")
            return []

    def set_time_format(self, time_format: str):
        """Sets the time format for the project."""
        if time_format not in ["12h", "24h"]:
            return False, "Invalid time format. Please use '12h' or '24h'."

        return self.update_project_config({"time_format": time_format})

    def append_system_prompt(self, text: str):
        """Appends text to the system prompt in config.json."""
        config = self.get_project_config()
        current_prompt = config.get("system_prompt", DEFAULT_SYSTEM_PROMPT)
        new_prompt = f"{current_prompt}\n{text}"
        return self.update_project_config({"system_prompt": new_prompt})

    def reset_system_prompt(self):
        """Resets the system prompt to the default."""
        return self.update_project_config({"system_prompt": DEFAULT_SYSTEM_PROMPT})

    def get_system_prompt(self):
        """Returns the current system prompt."""
        config = self.get_project_config()
        return config.get("system_prompt", DEFAULT_SYSTEM_PROMPT)

    def search_files(self, query: str):
        """Searches for a query in all text files within the current project."""
        project_path = self.get_current_project_path()
        results = []
        text_extensions = {'.txt', '.py', '.js', '.jsx', '.ts', '.tsx', '.json', '.md', '.html', '.css', '.jsonl'}

        for root, _, files in os.walk(project_path):
            for file in files:
                if os.path.splitext(file)[1].lower() in text_extensions:
                    file_path = Path(root) / file
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            for line_num, line in enumerate(f, 1):
                                if query.lower() in line.lower():
                                    results.append({
                                        "file": str(file_path.relative_to(project_path)),
                                        "line": line_num,
                                        "content": line.strip()
                                    })
                    except Exception as e:
                        print(f"[ProjectManager] [ERR] Failed to read file {file_path}: {e}")
        return results

    def enable_writing_mode(self):
        """Enables Writing Mode for the current project."""
        config = self.get_project_config()
        if config.get("mode") == "writing":
            return True, "Writing Mode is already enabled."

        # Backup current system prompt
        current_prompt = config.get("system_prompt", DEFAULT_SYSTEM_PROMPT)

        # Create necessary directories
        project_path = self.get_current_project_path()
        for folder in ["plot", "characters", "world", "chapters", "research"]:
            (project_path / folder).mkdir(exist_ok=True)

        # Update config
        update_data = {
            "mode": "writing",
            "backup_system_prompt": current_prompt,
            "system_prompt": WRITING_MODE_SYSTEM_PROMPT
        }
        return self.update_project_config(update_data)

    def disable_writing_mode(self):
        """Disables Writing Mode and restores previous configuration."""
        config = self.get_project_config()
        if config.get("mode") != "writing":
            return True, "Writing Mode is not enabled."

        # Restore backed up prompt, or default if missing
        original_prompt = config.get("backup_system_prompt", DEFAULT_SYSTEM_PROMPT)

        # Update config
        update_data = {
            "mode": "standard",
            "system_prompt": original_prompt
        }

        success, msg = self.update_project_config(update_data)
        if success:
             return True, "Writing Mode disabled. Standard configuration restored."
        return False, msg
