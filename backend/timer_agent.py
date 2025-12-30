import asyncio
import datetime
import time
import json
import os
import math
import struct
import pyaudio
from tzlocal import get_localzone
from time_utils import get_local_time

class TimerAgent:
    def __init__(self, session=None, sio=None, storage_file="timers.json"):
        self.session = session
        self.sio = sio
        self.storage_file = storage_file
        self.active_timers = {}
        self.active_reminders = {}
        self._pyaudio_instance = pyaudio.PyAudio()
        self._active_tasks = {} # To track all running timer/reminder tasks
        self._load_from_disk()
        self._update_loop_task = None # Will be started on demand

    def _start_update_loop_if_needed(self):
        """Starts the background broadcast loop if it's not already running."""
        if self._update_loop_task is None:
            try:
                # Check if a loop is running
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    self._update_loop_task = asyncio.create_task(self._broadcast_updates())
            except RuntimeError:
                # No running loop, do nothing. This happens in synchronous contexts like tests.
                pass

    def stop(self):
        """Stops all running tasks."""
        if self._update_loop_task:
            self._update_loop_task.cancel()
        for task in self._active_tasks.values():
            task.cancel()
        self._active_tasks = {}

    async def _broadcast_updates(self):
        """Periodically sends the status of all timers and reminders to the frontend."""
        while True:
            try:
                if self.sio:
                    # Prepare the data for the frontend
                    timers_list = []
                    for name, data in self.active_timers.items():
                        timers_list.append({
                            'name': name,
                            'type': 'timer',
                            'end_time': data['end_time'],
                            'duration': data['duration'],
                        })
                    for name, data in self.active_reminders.items():
                        timers_list.append({
                            'name': name,
                            'type': 'reminder',
                            'reminder_time': data['reminder_time'],
                        })

                    await self.sio.emit('timers_update', {'timers': timers_list})

                await asyncio.sleep(1) # Broadcast every second for live countdowns
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in TimerAgent update loop: {e}")
                await asyncio.sleep(5) # Wait longer if there's an error

    def _play_notification_sound(self):
        # A simple notification sound using pyaudio
        try:
            sample_rate = 44100
            duration = 0.5
            frequency = 440.0
            
            # Generate a simple sine wave
            num_samples = int(sample_rate * duration)
            samples = []
            for i in range(num_samples):
                sample = math.sin(2 * math.pi * frequency * i / sample_rate)
                samples.append(int(sample * 32767))
            
            # Pack into binary data
            data = struct.pack('<' + ('h' * len(samples)), *samples)
            
            stream = self._pyaudio_instance.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=sample_rate,
                output=True
            )
            stream.write(data)
            stream.stop_stream()
            stream.close()
        except Exception as e:
            print(f"Error playing notification sound: {e}")

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
                self._active_tasks[name] = task
                self.active_timers[name] = {
                    "task": task,
                    "end_time": timer_data["end_time"],
                    "name": name,
                    "duration": timer_data["duration"],
                }

        for name, reminder_data in data.get("reminders", {}).items():
            try:
                reminder_time = datetime.datetime.fromisoformat(reminder_data["reminder_time"])
                # Ensure the loaded time is timezone-aware for correct comparison
                if reminder_time.tzinfo is None:
                    reminder_time = reminder_time.replace(tzinfo=get_localzone())
                now = get_local_time()
                delay = (reminder_time - now).total_seconds()
                if delay > 0:
                    task = asyncio.create_task(self._reminder_task(delay, name, reminder_data["reminder_time"]))
                    self._active_tasks[name] = task
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
                if self.sio:
                    await self.sio.emit('timer_finished', {'name': name})
                self.active_timers.pop(name, None)
                self._active_tasks.pop(name, None)
                self._save_to_disk()
        except asyncio.CancelledError:
            # Timer was cancelled, do nothing.
            pass


    async def set_timer(self, duration: int, name: str):
        """Sets a timer for a specified duration in seconds."""
        if name in self.active_timers or name in self.active_reminders:
            return f"A timer or reminder with the name '{name}' already exists."

        self._start_update_loop_if_needed()
        task = asyncio.create_task(self._timer_task(duration, name))
        self._active_tasks[name] = task
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
                if self.sio:
                    await self.sio.emit('reminder_due', {'name': name, 'timestamp': timestamp})
                self.active_reminders.pop(name, None)
                self._active_tasks.pop(name, None)
                self._save_to_disk()
        except asyncio.CancelledError:
            # Reminder was cancelled, do nothing.
            pass


    async def set_reminder(self, timestamp: str, name: str):
        """Sets a reminder for a specific time (e.g., 'YYYY-MM-DDTHH:MM:SS')."""
        if name in self.active_timers or name in self.active_reminders:
            return f"A timer or reminder with the name '{name}' already exists."

        try:
            reminder_time = datetime.datetime.fromisoformat(timestamp)
            if reminder_time.tzinfo is None:
                reminder_time = reminder_time.replace(tzinfo=get_localzone())

            now = get_local_time()
            delay = (reminder_time - now).total_seconds()

            if delay <= 0:
                return "The specified time is in the past."

            self._start_update_loop_if_needed()
            aware_timestamp = reminder_time.isoformat()
            task = asyncio.create_task(self._reminder_task(delay, name, aware_timestamp))
            self._active_tasks[name] = task
            self.active_reminders[name] = {
                "task": task,
                "reminder_time": aware_timestamp,
                "name": name
            }
            self._save_to_disk()
            return f"Reminder '{name}' set for {aware_timestamp}."

        except ValueError:
            return "Invalid timestamp format. Please use ISO format (e.g., 'YYYY-MM-DDTHH:MM:SS')."

    async def modify_timer(self, name: str, new_duration: int = None, new_timestamp: str = None):
        """Modifies an existing timer or reminder."""
        if name in self.active_timers:
            if new_duration is not None:
                # Cancel the old task
                self.active_timers[name]["task"].cancel()
                self._active_tasks.pop(name, None)
                # Create a new task with the new duration
                task = asyncio.create_task(self._timer_task(new_duration, name))
                self._active_tasks[name] = task
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
                    if reminder_time.tzinfo is None:
                        reminder_time = reminder_time.replace(tzinfo=get_localzone())

                    now = get_local_time()
                    delay = (reminder_time - now).total_seconds()

                    if delay <= 0:
                        return "The specified time is in the past."

                    # Cancel the old task
                    self.active_reminders[name]["task"].cancel()
                    self._active_tasks.pop(name, None)
                    # Create a new task with the new timestamp
                    aware_timestamp = reminder_time.isoformat()
                    task = asyncio.create_task(self._reminder_task(delay, name, aware_timestamp))
                    self._active_tasks[name] = task
                    self.active_reminders[name].update({
                        "task": task,
                        "reminder_time": aware_timestamp,
                    })
                    self._save_to_disk()
                    return f"Reminder '{name}' modified to {aware_timestamp}."
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
            self._active_tasks.pop(name, None)
            del self.active_timers[name]
            self._save_to_disk()
            return f"Timer '{name}' deleted."
        elif name in self.active_reminders:
            self.active_reminders[name]["task"].cancel()
            self._active_tasks.pop(name, None)
            del self.active_reminders[name]
            self._save_to_disk()
            return f"Reminder '{name}' deleted."
        else:
            return f"No timer or reminder found with the name '{name}'."
