import os
import sys
import subprocess
import threading
import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class BugHunterHandler(FileSystemEventHandler):
    def __init__(self, callback, project_root):
        self.callback = callback
        self.project_root = project_root
        self.debounce_timer = None
        self.debounce_interval = 2.0
        self.lock = threading.Lock()
        self.test_process = None

    def on_modified(self, event):
        if event.is_directory:
            return
        if not event.src_path.endswith(".py"):
            return

        self._trigger_debounce(event.src_path)

    def _trigger_debounce(self, file_path):
        with self.lock:
            if self.debounce_timer:
                self.debounce_timer.cancel()
            self.debounce_timer = threading.Timer(self.debounce_interval, self._run_tests, args=[file_path])
            self.debounce_timer.start()

    def _run_tests(self, file_path):
        with self.lock:
            if self.test_process and self.test_process.poll() is None:
                print("[BUG HUNTER] Tests already running, skipping trigger.")
                return

        # Map file to test
        test_file = self._resolve_test_file(file_path)
        if not test_file:
            print(f"[BUG HUNTER] No matching test found for {os.path.basename(file_path)}")
            return

        print(f"[BUG HUNTER] Detected change in {os.path.basename(file_path)}. Running {test_file}...")

        try:
            self.test_process = subprocess.Popen(
                [sys.executable, "-m", "pytest", test_file],
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = self.test_process.communicate()

            if self.test_process.returncode != 0:
                print("[BUG HUNTER] Tests failed!")
                summary = self._parse_output(stdout + stderr, os.path.basename(file_path))
                if summary:
                    self._notify(summary)
            else:
                print("[BUG HUNTER] Tests passed.")

        except Exception as e:
            print(f"[BUG HUNTER] Error running tests: {e}")

    def _resolve_test_file(self, file_path):
        """
        Simple heuristic:
        backend/foo.py -> tests/test_foo.py
        """
        filename = os.path.basename(file_path)

        # If it's already a test, run it
        if filename.startswith("test_"):
            return file_path

        # Try to find corresponding test
        test_name = f"test_{filename}"
        potential_test_path = os.path.join(self.project_root, "tests", test_name)

        if os.path.exists(potential_test_path):
            return potential_test_path

        return None

    def _parse_output(self, output, trigger_file):
        lines = output.splitlines()
        for line in lines:
            if "FAILED" in line and "::" in line:
                parts = line.split("::")
                if len(parts) >= 2:
                    test_part = parts[1].strip()
                    test_name = test_part.split(" ")[0]
                    return f"Sir, that edit to {trigger_file} seems to have broken {test_name}."

        if "ERRORS" in output or "error" in output.lower():
             return f"Sir, I detected an error while running tests for {trigger_file}."

        return None

    def _notify(self, message):
        self.callback(message)

class BugHunter:
    def __init__(self, project_root, callback):
        self.project_root = project_root
        self.callback = callback
        self.observer = None
        self.loop = None

    def start(self):
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            print("[BUG HUNTER] Warning: No running event loop found during start()")

        event_handler = BugHunterHandler(self._dispatch_notification, self.project_root)
        self.observer = Observer()

        # Watch backend and tests
        for folder in ["backend", "tests"]:
            path = os.path.join(self.project_root, folder)
            if os.path.exists(path):
                self.observer.schedule(event_handler, path, recursive=True)

        self.observer.start()
        print("[BUG HUNTER] Started (Watchdog).")

    def stop(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()

    def _dispatch_notification(self, message):
        print(f"[BUG HUNTER] Notification: {message}")
        if self.callback:
            if self.loop and self.loop.is_running():
                 self.loop.call_soon_threadsafe(self._run_callback_async, message)
            else:
                print("[BUG HUNTER] Warning: Event loop not running, cannot deliver notification.")

    def _run_callback_async(self, message):
         asyncio.create_task(self.callback(message))
