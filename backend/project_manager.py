import os
import json
import shutil
import time
import asyncio
from pathlib import Path
from backend.github_client import GitHubClient

from backend.memory_manager import MemoryManager

DEFAULT_SYSTEM_PROMPT = "Your name is James and you speak with a british accent at all times.. You have a witty and professional personality, like a cheeky butler. Sarcasm is welcome. Your creator is Chad, and you address him as 'Sir'. When answering, respond using complete and concise sentences to keep a quick pacing and keep the conversation flowing. You are a professional assistant."

VALID_VOICES = ["Puck", "Charon", "Kore", "Fenrir", "Aoede", "Sadaltager"]

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

        # State for git monitoring
        self._git_last_state = {}
        self.global_fleet_file = self.workspace_root / "fleet.json"

        # Initialize Memory Manager
        self.memory_manager = MemoryManager(self.get_current_project_path())

    def _sanitize_name(self, name: str) -> str:
        """Sanitizes a project name to be filesystem safe."""
        return "".join([c for c in name if c.isalnum() or c in (' ', '-', '_', '.')]).strip()

    def load_fleet(self):
        project_fleet_file = self.get_current_project_path() / "fleet.json"

        # Reverse Migration Check: If global fleet doesn't exist but project does, migrate it back
        if not self.global_fleet_file.exists() and project_fleet_file.exists():
            print(f"[ProjectManager] Migrating fleet.json back to global scope from project: {self.current_project}")
            try:
                # Move the file back
                shutil.move(str(project_fleet_file), str(self.global_fleet_file))
            except Exception as e:
                print(f"[ProjectManager] Error migrating fleet.json back to global scope: {e}")

        # Load from global
        if self.global_fleet_file.exists():
            try:
                with open(self.global_fleet_file, "r") as f:
                    return json.load(f)
            except:
                pass
        return []

    def save_fleet(self, fleet):
        with open(self.global_fleet_file, "w") as f:
            json.dump(fleet, f, indent=4)

    def create_project(self, name: str):
        """Creates a new project directory with subfolders."""
        safe_name = self._sanitize_name(name)
        project_path = self.projects_dir / safe_name
        
        if not project_path.exists():
            project_path.mkdir()
            (project_path / "cad").mkdir()
            (project_path / "browser").mkdir()
            self._create_default_config(project_path)
            print(f"[ProjectManager] Created project: {safe_name}")
            return True, f"Project '{safe_name}' created."
        return False, f"Project '{safe_name}' already exists."

    def get_github_token(self):
        """Retrieves the GitHub token from global settings.json, migrating from project config if necessary."""
        # 1. Check Project Config (Migration)
        config = self.get_project_config()
        token = config.get("github_token")

        settings_path = self.workspace_root / "settings.json"

        if token:
            print(f"[ProjectManager] Migrating GitHub token to global settings from project: {self.current_project}")

            # Save to global settings
            settings = {}
            if settings_path.exists():
                try:
                    with open(settings_path, "r") as f:
                        settings = json.load(f)
                except Exception as e:
                    print(f"[ProjectManager] Error reading settings.json: {e}")

            settings["github_token"] = token
            try:
                with open(settings_path, "w") as f:
                    json.dump(settings, f, indent=4)
            except Exception as e:
                print(f"[ProjectManager] Error writing to settings.json: {e}")

            # Remove from project config
            config_path = self.get_current_project_path() / "config.json"
            if config_path.exists():
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        proj_config = json.load(f)
                    if "github_token" in proj_config:
                        del proj_config["github_token"]
                        with open(config_path, "w", encoding="utf-8") as f:
                            json.dump(proj_config, f, indent=4)
                except Exception as e:
                    print(f"[ProjectManager] Error removing token from config.json: {e}")

            return token

        # 2. Check Global Settings
        if settings_path.exists():
            try:
                with open(settings_path, "r") as f:
                    settings = json.load(f)
                return settings.get("github_token")
            except Exception as e:
                print(f"[ProjectManager] Error reading settings.json: {e}")

        return None

    def sync_jules_repos(self, sources):
        """
        Syncs local fleet configuration with the list of sources from Jules.
        Does NOT clone repositories. Updates fleet.json.
        """
        fleet = self.load_fleet()
        # fleet is a list of dicts: {owner, name, source}
        existing_repos = {f"{r['owner']}/{r['name']}" for r in fleet}

        new_repos = []
        for source_obj in sources:
            source_name = source_obj.get("name") if isinstance(source_obj, dict) else source_obj

            if not source_name or not source_name.startswith("sources/github/"):
                continue

            parts = source_name.split('/')
            if len(parts) < 4:
                continue

            repo_owner = parts[2]
            repo_name = parts[3]
            full_name = f"{repo_owner}/{repo_name}"

            if full_name not in existing_repos:
                fleet.append({
                    "owner": repo_owner,
                    "name": repo_name,
                    "source": source_name
                })
                new_repos.append(full_name)

        if new_repos:
            self.save_fleet(fleet)
            return [f"Added to Fleet: {r}" for r in new_repos], "OK"

        return ["Fleet up to date."], "OK"

    def _create_default_config(self, project_path):
        """Creates a default config.json file in the project directory."""
        config_path = project_path / "config.json"
        DEFAULT_CONFIG = {
            "system_prompt": DEFAULT_SYSTEM_PROMPT,
            "jules_api_key": "",
            "voice_name": "Sadaltager",
            "jules_slack_notifications": False,
            "mode": "default"
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
        safe_name = self._sanitize_name(name)
        project_path = self.projects_dir / safe_name
        
        if project_path.exists():
            self.current_project = safe_name
            self.memory_manager = MemoryManager(self.get_current_project_path())
            print(f"[ProjectManager] Switched to project: {safe_name}")
            return True, f"Switched to project '{safe_name}'."
        return False, f"Project '{safe_name}' does not exist."

    def list_projects(self):
        """Returns a list of available projects."""
        return [d.name for d in self.projects_dir.iterdir() if d.is_dir()]

    def get_current_project_path(self):
        return self.projects_dir / self.current_project

    def get_project_path(self, name: str):
        """Returns the path for a specific project."""
        safe_name = self._sanitize_name(name)
        return self.projects_dir / safe_name

    def list_git_projects(self):
        """Returns a list of projects that are git repositories."""
        git_projects = []
        for d in self.projects_dir.iterdir():
            if d.is_dir() and (d / ".git").exists():
                git_projects.append(d.name)
        return git_projects

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
        safe_prompt = self._sanitize_name(prompt)[:30].replace(" ", "_")
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

    def _get_jules_ui_state_path(self):
        return self.get_current_project_path() / "jules_ui_state.json"

    def _load_jules_ui_state(self):
        path = self._get_jules_ui_state_path()
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ProjectManager] [ERR] Failed to read jules UI state: {e}")
            return {}

    def _save_jules_ui_state(self, state):
        path = self._get_jules_ui_state_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=4)
        except Exception as e:
            print(f"[ProjectManager] [ERR] Failed to save jules UI state: {e}")

    def mark_jules_session_seen(self, session_id: str):
        """Marks a Jules session as seen by the user."""
        self.batch_mark_jules_sessions_seen([session_id])

    def batch_mark_jules_sessions_seen(self, session_ids: list):
        """Marks multiple Jules sessions as seen in one I/O operation."""
        if not session_ids:
            return

        state = self._load_jules_ui_state()
        changed = False
        now = time.time()

        for session_id in session_ids:
            if session_id not in state:
                state[session_id] = {}

            if "seen_at" not in state[session_id]:
                state[session_id]["seen_at"] = now
                changed = True

        if changed:
            self._save_jules_ui_state(state)

    def dismiss_jules_session(self, session_id: str):
        """Marks a Jules session as dismissed (hidden)."""
        state = self._load_jules_ui_state()
        if session_id not in state:
            state[session_id] = {}

        state[session_id]["dismissed"] = True
        self._save_jules_ui_state(state)
        return True, "Session dismissed."

    def get_jules_session_state(self, session_id: str):
        """Returns the UI state (seen_at, dismissed) for a session."""
        state = self._load_jules_ui_state()
        return state.get(session_id, {})

    def get_all_jules_session_states(self):
        """Returns the entire UI state dictionary."""
        return self._load_jules_ui_state()

    # --- Swarm Management ---
    def _get_swarms_path(self):
        return self.get_current_project_path() / "swarms.json"

    def _load_swarms(self):
        path = self._get_swarms_path()
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ProjectManager] [ERR] Failed to read swarms: {e}")
            return {}

    def _save_swarms(self, swarms):
        path = self._get_swarms_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(swarms, f, indent=4)
        except Exception as e:
            print(f"[ProjectManager] [ERR] Failed to save swarms: {e}")

    def create_swarm(self, title: str):
        """Creates a new swarm mission."""
        import uuid
        swarm_id = str(uuid.uuid4())
        swarms = self._load_swarms()

        swarms[swarm_id] = {
            "id": swarm_id,
            "title": title,
            "created_at": time.time(),
            "sessions": []
        }
        self._save_swarms(swarms)
        return swarm_id, f"Swarm '{title}' created with ID {swarm_id}."

    def add_session_to_swarm(self, swarm_id: str, session_id: str):
        """Adds a session to a swarm."""
        swarms = self._load_swarms()
        if swarm_id not in swarms:
            return False, "Swarm not found."

        if session_id not in swarms[swarm_id]["sessions"]:
            swarms[swarm_id]["sessions"].append(session_id)
            self._save_swarms(swarms)
            return True, f"Session {session_id} added to swarm {swarm_id}."
        return True, "Session already in swarm."

    def get_swarms(self):
        """Returns all swarms."""
        swarms = self._load_swarms()
        # Return as list sorted by creation time desc
        return sorted(swarms.values(), key=lambda x: x.get("created_at", 0), reverse=True)

    def set_time_format(self, time_format: str):
        """Sets the time format for the project."""
        if time_format not in ["12h", "24h"]:
            return False, "Invalid time format. Please use '12h' or '24h'."

        return self.update_project_config({"time_format": time_format})

    def set_voice(self, voice_name: str):
        """Sets the voice for the current project."""
        if voice_name not in VALID_VOICES:
             return False, f"Invalid voice name '{voice_name}'. Valid voices are: {', '.join(VALID_VOICES)}"

        return self.update_project_config({"voice_name": voice_name})

    def update_persona(self, persona: str):
         """Updates the system prompt (persona) for the current project."""
         return self.update_project_config({"system_prompt": persona})

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

    def search_chat_history(self, query: str, limit: int = 50):
        """Searches for a query in the chat history of the current project."""
        log_file = self.get_current_project_path() / "chat_history.jsonl"
        if not log_file.exists():
            return []

        results = []
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                # Read all lines to search efficiently (files are expected to be reasonable size)
                # If files get massive, we might need 'grep' or chunked reading.
                for line in f:
                    try:
                        entry = json.loads(line)
                        text = entry.get('text', '')
                        sender = entry.get('sender', 'Unknown')
                        timestamp = entry.get('timestamp', 0)

                        # Simple case-insensitive search
                        if query.lower() in text.lower():
                            # Format timestamp
                            time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
                            results.append(f"[{time_str}] {sender}: {text}")
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"[ProjectManager] [ERR] Failed to search chat history: {e}")
            return [f"Error searching chat history: {e}"]

        # Return the most recent matches first, up to limit
        return results[::-1][:limit]

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

    def add_architectural_memory(self, content, tags=None):
        return self.memory_manager.add_memory(content, tags)

    def search_architectural_memory(self, query):
        return self.memory_manager.search_memory(query)

    async def _check_repo(self, client, repo):
        try:
            owner = repo['owner']
            name = repo['name']

            branches = await client.get_branches(owner, name)
            if not branches:
                return None

            # Assume first branch is default or look for main/master
            default_branch = next((b for b in branches if b['name'] in ['main', 'master']), branches[0])

            current_sha = default_branch['commit']['sha']
            repo_key = f"{owner}/{name}"
            last_seen_sha = self._git_last_state.get(repo_key)

            event = None
            if last_seen_sha and current_sha != last_seen_sha:
                # New commit detected
                commit_msg = "New remote commit detected"
                author_name = "Remote User"
                date_str = "Just now"

                # Fetch details
                commit_data = await client.get_commit(owner, name, current_sha)
                if commit_data:
                    c = commit_data.get('commit', {})
                    author_name = c.get('author', {}).get('name', author_name)
                    date_str = c.get('author', {}).get('date', date_str)
                    commit_msg = c.get('message', commit_msg)

                event = {
                    "type": "git_commit",
                    "repo": repo_key,
                    "author": author_name,
                    "message": commit_msg,
                    "hash": current_sha,
                    "date": date_str
                }

            self._git_last_state[repo_key] = current_sha
            return event
        except Exception as e:
            print(f"[ProjectManager] Error checking repo {repo.get('owner')}/{repo.get('name')}: {e}")
            return None

    async def monitor_git_repos(self):
        """
        Scans fleet for new commits (via API) since the last check.
        Returns a list of event dictionaries.
        """
        fleet = self.load_fleet()
        token = self.get_github_token()

        if not token:
            return []

        client = GitHubClient(token)
        tasks = [self._check_repo(client, repo) for repo in fleet]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        events = []
        for res in results:
            if isinstance(res, Exception):
                print(f"[ProjectManager] Monitor task failed: {res}")
                continue
            if res:
                events.append(res)

        return events

    async def generate_fleet_report(self):
        """Generates a summary of all fleet repositories (PRs, Issues, etc.)"""
        fleet = self.load_fleet()
        token = self.get_github_token()

        report = {
            "prs": [],
            "stale_prs": [],
            "total_repos": len(fleet),
            "generated_at": time.time()
        }

        if not token:
            report["error"] = "No GitHub token configured."
            return report

        client = GitHubClient(token)

        async def fetch_repo_prs(repo):
            try:
                owner = repo.get('owner')
                name = repo.get('name')
                if not owner or not name: return []

                prs = await client.list_pull_requests(owner, name)
                results = []
                if prs:
                    for pr in prs:
                        results.append({
                            "repo": f"{owner}/{name}",
                            "number": pr.get("number"),
                            "title": pr.get("title"),
                            "url": pr.get("html_url"),
                            "created_at": pr.get("created_at"),
                            "updated_at": pr.get("updated_at")
                        })
                return results
            except Exception as e:
                print(f"[ProjectManager] Error fetching report for {repo.get('name')}: {e}")
                return []

        # Execute in parallel
        tasks = [fetch_repo_prs(repo) for repo in fleet]
        all_results = await asyncio.gather(*tasks, return_exceptions=True)

        for res in all_results:
            if isinstance(res, list):
                report["prs"].extend(res)

        return report

    def format_morning_briefing(self, report):
        """Formats a fleet report into a speech script."""
        if not report:
            return "Failed to generate briefing."

        if report.get('error'):
            return f"Morning Briefing Error: {report['error']} Please check your configuration."

        prs = report.get('prs', [])
        total_repos = report.get('total_repos', 0)

        if total_repos == 0:
            return "System Instruction: Speak this exactly: 'Your fleet is currently empty, Sir. You can add repositories in the settings or ask me to sync the fleet.'"

        # Group PRs by repo for better flow
        pr_counts = {}
        for pr in prs:
            repo = pr.get('repo', 'unknown')
            pr_counts[repo] = pr_counts.get(repo, 0) + 1

        summary = f"Good morning, Sir. I am monitoring {total_repos} repositories. "

        if not prs:
            summary += "All systems are green. There are no pending Pull Requests to review."
        else:
            summary += f"You have {len(prs)} pending Pull Requests waiting for your attention. "
            # Mention top 3 repos
            details = []
            for repo, count in list(pr_counts.items())[:3]:
                details.append(f"{count} in {repo.split('/')[-1]}")

            summary += "Including " + ", ".join(details)
            if len(pr_counts) > 3:
                summary += f", and others."
            else:
                summary += "."

        return f"System Notification: Here is the latest data. You MUST act as a news anchor and read this briefing aloud to the user right now:\n\n{summary}"
