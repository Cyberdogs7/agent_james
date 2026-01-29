import sys
import threading
import hashlib
import time
import asyncio
import re

class LogStream:
    """
    A wrapper around a stream (stdout/stderr) that forwards writes to the
    original stream and to a monitor.
    """
    def __init__(self, original_stream, monitor, stream_name=""):
        self.original_stream = original_stream
        self.monitor = monitor
        self.stream_name = stream_name

    def write(self, text):
        # Write to original stream first to ensure no latency in logs
        try:
            self.original_stream.write(text)
            self.original_stream.flush()
        except Exception:
            pass # Don't break if original stream fails

        # Forward to monitor
        try:
            self.monitor.process_chunk(text)
        except Exception:
            pass # Don't let monitor bugs crash the app

    def flush(self):
        try:
            self.original_stream.flush()
        except Exception:
            pass

    def isatty(self):
        return getattr(self.original_stream, 'isatty', lambda: False)()

class LogMonitor:
    def __init__(self, callback, loop=None):
        self.callback = callback
        self.loop = loop
        self.buffer = ""
        self.capturing = False
        self.capture_buffer = []
        self.recent_errors = {} # hash -> timestamp
        self.debounce_seconds = 300 # 5 minutes debounce for same error

        # Regex to detect start of traceback
        self.traceback_start = re.compile(r'^Traceback \(most recent call last\):')

        # Regex to detect the final line of a traceback (ExceptionName: Message)
        # It usually starts at the beginning of the line (no indent) and is not "Traceback..."
        # We'll treat any non-indented line after the start as a potential end,
        # but we need to be careful about multi-line error messages.
        self.exception_line = re.compile(r'^\w+Error:|^Exception:|^[A-Z]\w+:')

    def set_loop(self, loop):
        self.loop = loop

    def process_chunk(self, text):
        # Accumulate text to handle partial writes
        self.buffer += text

        while '\n' in self.buffer:
            line, self.buffer = self.buffer.split('\n', 1)
            self.process_line(line)

    def process_line(self, line):
        clean_line = line.rstrip()

        if not self.capturing:
            # Check for start of traceback
            if self.traceback_start.search(clean_line):
                self.capturing = True
                self.capture_buffer = [clean_line]
        else:
            self.capture_buffer.append(clean_line)

            # Heuristic to detect end of traceback
            # 1. Start of a new traceback? Reset and start over.
            if self.traceback_start.search(clean_line):
                self.capture_buffer = [clean_line]
                return

            # 2. Check for the final exception line.
            # Standard python tracebacks:
            #   File "...", line X, in module
            #     code
            #   ValueError: message
            # The File/Code lines are indented. The Exception line is NOT indented.
            if clean_line and not clean_line.startswith(' ') and not clean_line.startswith('\t'):
                # It's a non-indented line. Is it an exception?
                # Most exceptions end in 'Error' or 'Exception', but custom ones might not.
                # However, almost all lines in a traceback block ARE indented, except the first and last.

                # If we have captured at least a few lines, assume this is the end.
                if len(self.capture_buffer) > 1:
                     self.finalize_capture()

            # Safety valve: Don't capture infinite buffers
            if len(self.capture_buffer) > 50:
                self.finalize_capture()

    def finalize_capture(self):
        full_traceback = "\n".join(self.capture_buffer)
        self.capturing = False
        self.capture_buffer = []

        # Debounce
        error_hash = hashlib.md5(full_traceback.encode('utf-8')).hexdigest()
        now = time.time()

        if error_hash in self.recent_errors:
            if now - self.recent_errors[error_hash] < self.debounce_seconds:
                # print(f"[LOG MONITOR] Debounced duplicate error: {error_hash}")
                return

        self.recent_errors[error_hash] = now

        # Fire callback
        if self.callback:
            if self.loop:
                self.loop.call_soon_threadsafe(self._run_callback_async, full_traceback)
            else:
                # If no loop yet, we can't really await, but we can try running it
                # or just print it.
                print(f"[LOG MONITOR] Captured Error (No Loop): {len(full_traceback)} bytes")

    def _run_callback_async(self, message):
        asyncio.create_task(self.callback(message))

    def install(self):
        sys.stdout = LogStream(sys.stdout, self, "stdout")
        sys.stderr = LogStream(sys.stderr, self, "stderr")
        print("[LOG MONITOR] Installed and monitoring for tracebacks.")
