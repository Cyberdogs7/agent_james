import pytest
from unittest.mock import MagicMock
from backend.log_monitor import LogMonitor, LogStream

class MockStream:
    def __init__(self):
        self.content = ""
        self.flushed = False

    def write(self, text):
        self.content += text

    def flush(self):
        self.flushed = True

def test_log_monitor_traceback_detection():
    callback_mock = MagicMock()

    # Use a dummy loop object if needed, but for unit test we can just mock the loop's call_soon_threadsafe
    loop_mock = MagicMock()
    # When call_soon_threadsafe is called, we just execute the function immediately for this test
    def side_effect(func, *args):
        # The func passed is _run_callback_async, which creates a task
        # We can just simulate the effect by calling the callback mock directly
        callback_mock(*args)

    loop_mock.call_soon_threadsafe.side_effect = side_effect

    monitor = LogMonitor(callback=callback_mock, loop=loop_mock)

    # Test Data
    traceback_text = """Traceback (most recent call last):
  File "server.py", line 10, in <module>
    main()
  File "server.py", line 5, in main
    raise ValueError("Oops")
ValueError: Oops
"""

    # Feed chunks
    chunks = traceback_text.splitlines(keepends=True)
    for chunk in chunks:
        monitor.process_chunk(chunk)

    # Check if callback was called
    assert callback_mock.called
    args = callback_mock.call_args[0]
    assert "ValueError: Oops" in args[0]
    assert "Traceback (most recent call last):" in args[0]

def test_log_stream_forwarding():
    original = MockStream()
    monitor = MagicMock()
    stream = LogStream(original, monitor)

    stream.write("Hello World")

    assert original.content == "Hello World"
    monitor.process_chunk.assert_called_with("Hello World")

def test_debounce():
    callback_mock = MagicMock()
    loop_mock = MagicMock()
    loop_mock.call_soon_threadsafe.side_effect = lambda f, *a: callback_mock(*a)

    monitor = LogMonitor(callback=callback_mock, loop=loop_mock)
    monitor.debounce_seconds = 60 # Set debounce window

    traceback_text = "Traceback (most recent call last):\n  File X\nValueError: Error\n"

    # First Error
    monitor.process_chunk(traceback_text)
    assert callback_mock.call_count == 1

    # Duplicate Error immediately
    monitor.process_chunk(traceback_text)
    assert callback_mock.call_count == 1 # Should stay 1

    # Different Error
    traceback_text_2 = "Traceback (most recent call last):\n  File Y\nTypeError: Error\n"
    monitor.process_chunk(traceback_text_2)
    assert callback_mock.call_count == 2
