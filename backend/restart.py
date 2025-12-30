import subprocess
import sys
import os

def restart_app():
    """
    Restarts the application by running 'npm run dev' in a new terminal window.
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    command = "npm run dev"

    print(f"Project root: {project_root}")
    print(f"Executing command: {command}")

    try:
        if sys.platform == "win32":
            subprocess.Popen(
                ['cmd', '/c', 'start', 'cmd', '/k', command],
                cwd=project_root,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        elif sys.platform == "darwin": # macOS
            subprocess.Popen(
                ['osascript', '-e', f'tell app "Terminal" to do script "cd {project_root} && {command}"'],
            )
        else: # Linux
            try:
                # Try with gnome-terminal first
                subprocess.Popen(
                    ['gnome-terminal', '--', 'bash', '-c', f'{command}; exec bash'],
                    cwd=project_root
                )
            except FileNotFoundError:
                try:
                    # Fallback to xterm
                    subprocess.Popen(
                        ['xterm', '-e', f'bash -c "{command}; exec bash"'],
                        cwd=project_root
                    )
                except FileNotFoundError:
                    print("Could not find gnome-terminal or xterm. Please run 'npm run dev' manually.")
    except Exception as e:
        print(f"Failed to restart application: {e}")

if __name__ == "__main__":
    restart_app()
