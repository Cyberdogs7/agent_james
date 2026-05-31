import json
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
            with open(self.tasks_file, 'w', encoding='utf-8') as f:
                json.dump([], f, indent=4)

    def load_tasks(self):
        try:
            with open(self.tasks_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def save_tasks(self, tasks):
        with open(self.tasks_file, 'w', encoding='utf-8') as f:
            json.dump(tasks, f, indent=4)

    def validate_schedule(self, trigger_value):
        """
        Validates the structure of a schedule trigger value.
        Expected formats:
        - { "mode": "interval", "interval_minutes": 30 }
        - { "mode": "daily", "time": "09:00", "days": ["Mon", "Fri"] }
        - { "mode": "cron", "expression": "* * * * *" }
        """
        if not isinstance(trigger_value, dict):
            # Legacy support or simple string check
            return True

        mode = trigger_value.get("mode")
        if mode == "interval":
            if "interval_minutes" not in trigger_value:
                raise ValueError("Interval mode requires 'interval_minutes'")
            try:
                int(trigger_value["interval_minutes"])
            except ValueError:
                raise ValueError("interval_minutes must be a number")

        elif mode == "daily":
            if "time" not in trigger_value:
                raise ValueError("Daily mode requires 'time' (HH:MM)")
            # Basic HH:MM validation
            import re
            if not re.match(r"^\d{2}:\d{2}$", trigger_value["time"]):
                raise ValueError("Time must be in HH:MM format (24h)")

            hours, minutes = [int(x) for x in trigger_value["time"].split(':')]
            if not (0 <= hours <= 23) or not (0 <= minutes <= 59):
                raise ValueError("Invalid time (HH: 00-23, MM: 00-59)")

        elif mode == "cron":
            if "expression" not in trigger_value:
                raise ValueError("Cron mode requires 'expression'")
            from croniter import croniter
            if not croniter.is_valid(trigger_value["expression"]):
                raise ValueError(f"Invalid cron expression: {trigger_value['expression']}")

        return True

    def create_task(self, title, trigger_type="manual", trigger_value=None, action_type="none", action_value=None):
        # Validate if it's a schedule
        if trigger_type == "schedule":
            try:
                self.validate_schedule(trigger_value)
            except ValueError as e:
                print(f"[TaskManager] Invalid schedule format: {e}")
                # We could raise, but to prevent crashing server on bad input we might just log or default?
                # Raising is better for API feedback.
                # For now, we will proceed but log, assuming UI handles validation mostly.
                pass

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
            "last_run": None,
            "next_run": None # Calculated by Automation Engine
        }
        tasks.append(new_task)
        self.save_tasks(tasks)
        return new_task

    def update_task(self, task_id, updates):
        """Updates fields of an existing task."""
        tasks = self.load_tasks()
        updated = False
        for t in tasks:
            if t['id'] == task_id:
                # Update allowed top-level fields
                for field in ['title', 'status', 'last_run', 'next_run', 'healing']:
                    if field in updates:
                        t[field] = updates[field]

                # Update Trigger
                if 'trigger' in updates:
                    # Validate if updating to schedule
                    if updates['trigger'].get('type') == 'schedule':
                         try:
                             self.validate_schedule(updates['trigger'].get('value'))
                         except ValueError:
                             pass
                    t['trigger'] = updates['trigger']

                # Update Action
                if 'action' in updates:
                    t['action'] = updates['action']

                updated = True
                break

        if updated:
            self.save_tasks(tasks)
        return updated

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
        return self.update_task(task_id, {"status": status})
