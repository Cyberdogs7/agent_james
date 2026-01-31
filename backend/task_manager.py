import json
import os
import uuid
import time
from pathlib import Path

class TaskManager:
    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.tasks_file = self.project_path / "tasks.json"
        self._ensure_file()

    def _ensure_file(self):
        if not self.tasks_file.exists():
            default_tasks = [
                {
                    "id": str(uuid.uuid4()),
                    "title": "Announce New Commits",
                    "trigger": {
                        "type": "git",
                        "value": "*"
                    },
                    "action": {
                        "type": "notify",
                        "value": "New commit detected."
                    },
                    "status": "active",
                    "created_at": time.time(),
                    "last_run": None
                }
            ]
            with open(self.tasks_file, 'w', encoding='utf-8') as f:
                json.dump(default_tasks, f, indent=4)

    def load_tasks(self):
        try:
            with open(self.tasks_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def save_tasks(self, tasks):
        with open(self.tasks_file, 'w', encoding='utf-8') as f:
            json.dump(tasks, f, indent=4)

    def create_task(self, title, trigger_type="manual", trigger_value=None, action_type="none", action_value=None):
        tasks = self.load_tasks()
        new_task = {
            "id": str(uuid.uuid4()),
            "title": title,
            "trigger": {
                "type": trigger_type, # manual, schedule, git, trello
                "value": trigger_value
            },
            "action": {
                "type": action_type, # run_script, notify, jules_task
                "value": action_value
            },
            "status": "active", # active, paused, completed
            "created_at": time.time(),
            "last_run": None
        }
        tasks.append(new_task)
        self.save_tasks(tasks)
        return new_task

    def delete_task(self, task_id):
        tasks = self.load_tasks()
        initial_count = len(tasks)
        tasks = [t for t in tasks if t['id'] != task_id]
        if len(tasks) < initial_count:
            self.save_tasks(tasks)
            return True
        return False

    def list_tasks(self):
        return self.load_tasks()

    def update_task_status(self, task_id, status):
        tasks = self.load_tasks()
        for t in tasks:
            if t['id'] == task_id:
                t['status'] = status
                self.save_tasks(tasks)
                return True
        return False
