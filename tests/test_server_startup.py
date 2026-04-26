import subprocess
import os
import time
import signal
import sys

def test_server_port_config():
    # Path to server.py
    server_path = "backend/server.py"

    # Set custom port
    custom_port = "9999"
    env = os.environ.copy()
    env["SERVER_PORT"] = custom_port
    env["GEMINI_API_KEY"] = "dummy_key_for_testing"

    print(f"Starting server with SERVER_PORT={custom_port}")

    # Start server process
    process = subprocess.Popen(
        [sys.executable, server_path],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=os.getcwd() # Run from root
    )

    try:
        # Read output line by line for a few seconds
        start_time = time.time()
        found_port_message = False

        while time.time() - start_time < 10: # Wait up to 10 seconds
            line = process.stdout.readline()
            if line:
                print(f"[SERVER STDOUT] {line.strip()}")
                if f"Starting server on port {custom_port}" in line:
                    found_port_message = True
                    break

            # Check if process exited
            if process.poll() is not None:
                stderr = process.stderr.read()
                print(f"[SERVER STDERR] {stderr}")
                break

        if found_port_message:
            print("SUCCESS: Server started with custom port.")
        else:
            print("FAILURE: Did not find port startup message.")
            sys.exit(1)

    finally:
        # Cleanup
        if process.poll() is None:
            print("Killing server process...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

if __name__ == "__main__":
    test_server_port_config()
