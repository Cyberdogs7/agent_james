import asyncio
import datetime
import time
import json
import os
from pyo import *

class TimerAgent:
    def __init__(self, session=None, storage_file="timers.json"):
        self.session = session
        self.storage_file = storage_file
        self.active_timers = {}
        self.active_reminders = {}
        self._server = Server().boot()
        self._load_from_disk()

    def _play_notification_sound(self):
        self._server.start()
        # A simple notification sound
        env = Adsr(attack=0.01, decay=0.2, sustain=0, release=0.1, dur=0.31)
        sig = Sine(freq=[440, 880], mul=env*0.5).out()
        env.play()
        time.sleep(0.5)
        self._server.stop()

    def _save_to_disk(self):
        timers_to_save = {
            name: {
                "end_time": data["end_time"],
                "name": data["name"],
                "duration": data["duration"],
            }
            for name, data in self.active_timers.items()
        }
        reminders_to_save = {
            name: {
                "reminder_time": data["reminder_time"],
                "name": data["name"],
            }
            for name, data in self.active_reminders.items()
        }
        with open(self.storage_file, "w") as f:
            json.dump({"timers": timers_to_save, "reminders": reminders_to_save}, f)

    def _load_from_disk(self):
        if not os.path.exists(self.storage_file):
            return

        with open(self.storage_file, "r") as f:
            data = json.load(f)

        for name, timer_data in data.get("timers", {}).items():
            remaining_duration = timer_data["end_time"] - time.time()
            if remaining_duration > 0:
                task = asyncio.create_task(self._timer_task(remaining_duration, name))
                self.active_timers[name] = {
                    "task": task,
                    "end_time": timer_data["end_time"],
                    "name": name,
                    "duration": timer_data["duration"],
                }

        for name, reminder_data in data.get("reminders", {}).items():
            try:
                reminder_time = datetime.datetime.fromisoformat(reminder_data["reminder_time"])
                now = datetime.datetime.now()
                delay = (reminder_time - now).total_seconds()
                if delay > 0:
                    task = asyncio.create_task(self._reminder_task(delay, name, reminder_data["reminder_time"]))
                    self.active_reminders[name] = {
                        "task": task,
                        "reminder_time": reminder_data["reminder_time"],
                        "name": name,
                    }
            except ValueError:
                print(f"Error loading reminder '{name}': Invalid timestamp format.")


    async def _send_notification(self, message):
        self._play_notification_sound()
        if self.session:
            await self.session.send(input=f"System Notification: {message}", end_of_turn=True)

    async def _timer_task(self, duration, name):
        try:
            await asyncio.sleep(duration)
            if name in self.active_timers: # Check if it wasn't cancelled
                await self._send_notification(f"Timer '{name}' is up!")
                self.active_timers.pop(name, None)
                self._save_to_disk()
        except asyncio.CancelledError:
            # Timer was cancelled, do nothing.
            pass


    async def set_timer(self, duration: int, name: str):
        """Sets a timer for a specified duration in seconds."""
        if name in self.active_timers or name in self.active_reminders:
            return f"A timer or reminder with the name '{name}' already exists."

        task = asyncio.create_task(self._timer_task(duration, name))
        self.active_timers[name] = {
            "task": task,
            "end_time": time.time() + duration,
            "name": name,
            "duration": duration
        }
        self._save_to_disk()
        return f"Timer '{name}' set for {duration} seconds."

    async def _reminder_task(self, delay, name, timestamp):
        try:
            await asyncio.sleep(delay)
            if name in self.active_reminders: # Check if it wasn't cancelled
                await self._send_notification(f"Reminder: '{name}'")
                self.active_reminders.pop(name, None)
                self._save_to_disk()
        except asyncio.CancelledError:
            # Reminder was cancelled, do nothing.
            pass


    async def set_reminder(self, timestamp: str, name: str):
        """Sets a reminder for a specific time (e.g., 'YYYY-MM-DDTHH:MM:SS')."""
        if name in self.active_timers or name in self.active_reminders:
            return f"A timer or reminder with the name '{name}' already exists."

        try:
            # Using fromisoformat which is more robust
            reminder_time = datetime.datetime.fromisoformat(timestamp)
            now = datetime.datetime.now()
            delay = (reminder_time - now).total_seconds()

            if delay <= 0:
                return "The specified time is in the past."

            task = asyncio.create_task(self._reminder_task(delay, name, timestamp))
            self.active_reminders[name] = {
                "task": task,
                "reminder_time": timestamp,
                "name": name
            }
            self._save_to_disk()
            return f"Reminder '{name}' set for {timestamp}."

        except ValueError:
            return "Invalid timestamp format. Please use ISO format (e.g., 'YYYY-MM-DDTHH:MM:SS')."

    async def modify_timer(self, name: str, new_duration: int = None, new_timestamp: str = None):
        """Modifies an existing timer or reminder."""
        if name in self.active_timers:
            if new_duration is not None:
                # Cancel the old task
                self.active_timers[name]["task"].cancel()
                # Create a new task with the new duration
                task = asyncio.create_task(self._timer_task(new_duration, name))
                self.active_timers[name].update({
                    "task": task,
                    "end_time": time.time() + new_duration,
                    "duration": new_duration,
                })
                self._save_to_disk()
                return f"Timer '{name}' modified to {new_duration} seconds."
            else:
                return "Please provide a new duration for the timer."
        elif name in self.active_reminders:
            if new_timestamp is not None:
                try:
                    reminder_time = datetime.datetime.fromisoformat(new_timestamp)
                    now = datetime.datetime.now()
                    delay = (reminder_time - now).total_seconds()

                    if delay <= 0:
                        return "The specified time is in the past."

                    # Cancel the old task
                    self.active_reminders[name]["task"].cancel()
                    # Create a new task with the new timestamp
                    task = asyncio.create_task(self._reminder_task(delay, name, new_timestamp))
                    self.active_reminders[name].update({
                        "task": task,
                        "reminder_time": new_timestamp,
                    })
                    self._save_to_disk()
                    return f"Reminder '{name}' modified to {new_timestamp}."
                except ValueError:
                    return "Invalid timestamp format. Please use ISO format (e.g., 'YYYY-MM-DDTHH:MM:SS')."
            else:
                return "Please provide a new timestamp for the reminder."
        else:
            return f"No timer or reminder found with the name '{name}'."

    def list_timers(self):
        """Lists all active timers and reminders."""
        response = "Active Timers:\n"
        if not self.active_timers:
            response += "  - None\n"
        else:
            for name, data in self.active_timers.items():
                remaining = data['end_time'] - time.time()
                response += f"  - {name}: {int(remaining)} seconds remaining\n"

        response += "\nActive Reminders:\n"
        if not self.active_reminders:
            response += "  - None\n"
        else:
            for name, data in self.active_reminders.items():
                response += f"  - {name}: at {data['reminder_time']}\n"

        return response

    def delete_entry(self, name: str):
        """Deletes a timer or reminder by name."""
        if name in self.active_timers:
            self.active_timers[name]["task"].cancel()
            del self.active_timers[name]
            self._save_to_disk()
            return f"Timer '{name}' deleted."
        elif name in self.active_reminders:
            self.active_reminders[name]["task"].cancel()
            del self.active_reminders[name]
            self._save_to_disk()
            return f"Reminder '{name}' deleted."
        else:
            return f"No timer or reminder found with the name '{name}'."
