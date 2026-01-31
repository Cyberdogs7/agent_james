import os
import time
import sys
import subprocess
import threading
import asyncio

class BugHunter:
    def __init__(self, project_root, callback):
        self.project_root = project_root
        self.callback = callback
        self.running = False
        self.last_mtime = {}
        self.debounce_timer = None
        self.debounce_interval = 2.0  # Seconds
        self.loop = None
        self.lock = threading.Lock()

    def start(self):
        """Starts the background monitoring thread."""
        self.running = True
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            print("[BUG HUNTER] Warning: No running event loop found during start()")

        threading.Thread(target=self._monitor_loop, daemon=True).start()
        print("[BUG HUNTER] Started proactively hunting for bugs.")

    def stop(self):
        self.running = False
        if self.debounce_timer:
            self.debounce_timer.cancel()

    def _monitor_loop(self):
        # Initial scan to populate mtime
        self._check_files(initial=True)

        while self.running:
            try:
                changed = self._check_files()
                if changed:
                    self._trigger_debounce()
            except Exception as e:
                print(f"[BUG HUNTER] Error in monitor loop: {e}")
            time.sleep(1)

    def _check_files(self, initial=False):
        changed = False
        # Monitor backend and tests
        paths_to_monitor = [
            os.path.join(self.project_root, "backend"),
            os.path.join(self.project_root, "tests")
        ]

        for path in paths_to_monitor:
            if not os.path.exists(path):
                continue
            for root, dirs, files in os.walk(path):
                # Skip __pycache__
                if "__pycache__" in dirs:
                    dirs.remove("__pycache__")

                for f in files:
                    if f.endswith(".py"):
                        full_path = os.path.join(root, f)
                        try:
                            mtime = os.stat(full_path).st_mtime
                            if full_path not in self.last_mtime:
                                self.last_mtime[full_path] = mtime
                                if not initial:
                                    # New file created
                                    print(f"[BUG HUNTER] New file detected: {f}")
                                    changed = True
                            elif mtime > self.last_mtime[full_path]:
                                self.last_mtime[full_path] = mtime
                                print(f"[BUG HUNTER] Modified file detected: {f}")
                                changed = True
                        except OSError:
                            pass
        return changed

    def _trigger_debounce(self):
        with self.lock:
            if self.debounce_timer:
                self.debounce_timer.cancel()
            self.debounce_timer = threading.Timer(self.debounce_interval, self._run_tests)
            self.debounce_timer.start()

    def _run_tests(self):
        print("[BUG HUNTER] Running relevant tests...")
        try:
            # Run pytest
            # We want to capture output to parse failures
            # We run from project_root
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                # Tests failed
                print("[BUG HUNTER] Tests failed!")
                summary = self._parse_output(result.stdout + result.stderr)
                if summary:
                    self._notify(summary)
            else:
                print("[BUG HUNTER] All tests passed.")

        except Exception as e:
            print(f"[BUG HUNTER] Error running tests: {e}")

    def _parse_output(self, output):
        # Simple parser to find the failed test
        # Look for "FAILED tests/... ::test_name" lines
        lines = output.splitlines()
        failed_tests = []

        for line in lines:
            if "FAILED" in line and "::" in line:
                # Example: tests/test_math.py::test_add FAILED
                # Or: FAILED tests/test_math.py::test_add - assert...
                parts = line.split("::")
                if len(parts) >= 2:
                    # Clean up filename (remove FAILED prefix if present)
                    file_part = parts[0].strip()
                    if "FAILED " in file_part:
                        file_part = file_part.replace("FAILED ", "")
                    file_name = os.path.basename(file_part)

                    # Clean up test name (remove status suffix)
                    test_part = parts[1].strip()
                    test_name = test_part.split(" ")[0]

                    failed_tests.append((file_name, test_name))

        if failed_tests:
            # Just report the first failure for brevity
            file_name, test_name = failed_tests[0]
            return f"Sir, that last edit seems to have broken {test_name} in {file_name}."

        # Check for collection errors or other failures
        if "ERRORS" in output or "error" in output.lower():
             return "Sir, I detected an error while running the test suite."

        return None

    def _notify(self, message):
        print(f"[BUG HUNTER] Notification: {message}")
        if self.callback:
            if self.loop and self.loop.is_running():
                 self.loop.call_soon_threadsafe(self._run_callback_async, message)
            else:
                print("[BUG HUNTER] Warning: Event loop not running, cannot deliver notification.")

    def _run_callback_async(self, message):
         asyncio.create_task(self.callback(message))
