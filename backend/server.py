import sys
import asyncio
from backend.jules_agent import JulesAgent

# Fix for asyncio subprocess support on Windows
# MUST BE SET BEFORE OTHER IMPORTS
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import socketio
import uvicorn
from backend.fleet_manager import FleetManager
from backend.db import init_db, get_all_accounts, add_account, update_account, delete_account
from backend.jules_agent import JulesAgent
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import threading
import sys
import os
import time
import json
import copy
from datetime import datetime
from pathlib import Path



# Ensure we can import ada and backend modules
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)
sys.path.append(current_dir)

from backend import ada
from authenticator import FaceAuthenticator
from kasa_agent import KasaAgent
from project_manager import ProjectManager
from slack_agent import SlackAgent
from scraper_agent import ScraperAgent
fleet_manager = FleetManager(data_file="projects/fleet_state.json")
try:
    from backend.message_deduplicator import MessageDeduplicator
except ImportError:
    from message_deduplicator import MessageDeduplicator

try:
    from backend.bug_hunter import BugHunter
except ImportError:
    from bug_hunter import BugHunter

try:
    from backend.task_manager import TaskManager
except ImportError:
    from task_manager import TaskManager

try:
    from backend.automation_engine import AutomationEngine
except ImportError:
    from automation_engine import AutomationEngine

# Create a Socket.IO server
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await startup_event()
    yield
    # Shutdown
    # Assuming no shutdown event logic right now

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount projects directory for static file access (e.g. avatars)
# project_root is calculated below, but we need it here or need to defer mounting.
# Let's move project_root calc up or use relative path logic assuming backend execution context.
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
projects_dir = os.path.join(project_root, "projects")
if not os.path.exists(projects_dir):
    os.makedirs(projects_dir)
app.mount("/projects", StaticFiles(directory=projects_dir), name="projects")

app_socketio = socketio.ASGIApp(sio, app)

import signal

# --- SHUTDOWN HANDLER ---
def signal_handler(sig, frame):
    print(f"\n[SERVER] Caught signal {sig}. Exiting gracefully...")
    # Clean up audio loop
    if audio_loop:
        try:
            print("[SERVER] Stopping Audio Loop...")
            audio_loop.stop() 
        except:
            pass
    # Force kill
    print("[SERVER] Force exiting...")
    os._exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Global state
audio_loop = None
loop_task = None
server_loop = None
dashboard_task = None # Task for streaming dashboard updates
authenticator = None
kasa_agent = KasaAgent()
slack_agent = None
scraper_agent = None
log_monitor = None
automation_engine = None
task_manager = None
# Deduplicator for UI inputs (which don't have built-in IDs usually)
ui_deduplicator = MessageDeduplicator(max_size=500)
SETTINGS_FILE = "settings.json"

async def handle_runtime_error(error_log):
    """Callback for LogMonitor to notify the model of runtime crashes."""
    print(f"[SERVER] Handling runtime error: {len(error_log)} bytes detected")
    if audio_loop and audio_loop.session:
        # Construct a clear prompt for the model
        msg = (
            f"System Notification: A runtime error was detected in the backend logs:\n"
            f"```\n{error_log}\n```\n"
            f"Please inform the user about this crash immediately. "
            f"Ask them: 'I detected a runtime error. Would you like me to attempt a fix?' "
            f"If they say yes, use the 'run_jules_agent' tool with the error details."
        )
        try:
            # We must await the send operation
            await audio_loop.session.send(input=msg, end_of_turn=True)
            print("[SERVER] Sent runtime error notification to model.")
        except Exception as e:
            print(f"[SERVER] Failed to send error notification: {e}")

async def handle_bug_hunter_notification(message):
    """Callback for BugHunter to notify the model of test failures."""
    print(f"[SERVER] Handling Bug Hunter notification: {message}")
    if audio_loop and audio_loop.session:
        msg = f"System Notification: {message}"
        try:
            await audio_loop.session.send(input=msg, end_of_turn=True)
            print("[SERVER] Sent bug report to model.")
        except Exception as e:
            print(f"[SERVER] Failed to send bug report: {e}")

async def handle_slack_message(message):
    """Callback function for the SlackAgent to handle incoming messages."""
    if audio_loop and audio_loop.session:
        print(f"[SERVER] Forwarding Slack message to audio loop: {message}")
        # This function mimics the behavior of the user_input socket event
        if audio_loop.project_manager:
            audio_loop.project_manager.log_chat("User", message)

        # Set the source of the message to 'slack'
        audio_loop.message_source = 'slack'

        await audio_loop.session.send(input=message, end_of_turn=True)
    else:
        print("[SERVER] Audio loop not ready, cannot process Slack message.")

# Determine project root and initialize ProjectManager
# project_root already calculated above
project_manager = ProjectManager(project_root)

DEFAULT_SETTINGS = {
    "face_auth_enabled": False, # Default OFF as requested
    "tool_permissions": {
        "generate_cad": True,
        "run_web_agent": True,
        "write_file": True,
        "read_directory": True,
        "read_file": True,
        "create_project": True,
        "switch_project": True,
        "list_projects": True
    },
    "printers": [], # List of {host, port, name, type}
    "kasa_devices": [], # List of {ip, alias, model}
    "camera_flipped": False # Invert cursor horizontal direction
}

SETTINGS = copy.deepcopy(DEFAULT_SETTINGS)

def deep_merge(target, source):
    """
    Recursively merge source dictionary into target dictionary.
    """
    for key, value in source.items():
        if isinstance(value, dict):
            node = target.setdefault(key, {})
            if isinstance(node, dict):
                deep_merge(node, value)
            else:
                target[key] = value
        else:
            target[key] = value
    return target

def load_settings():
    global SETTINGS
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                loaded = json.load(f)
                # Merge with defaults to ensure new keys exist
                deep_merge(SETTINGS, loaded)

            print(f"Loaded settings: {SETTINGS}")
        except Exception as e:
            print(f"Error loading settings: {e}")

def save_settings():
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(SETTINGS, f, indent=4)
        print("Settings saved.")
    except Exception as e:
        print(f"Error saving settings: {e}")

# Load on startup
load_settings()

authenticator = None
kasa_agent = KasaAgent(known_devices=SETTINGS.get("kasa_devices"))
# tool_permissions is now SETTINGS["tool_permissions"]


async def initial_fleet_sync():
    print("[SERVER] Running initial fleet sync...")
    try:

        # Try to get API key from config
        config = project_manager.get_project_config()
        api_key = config.get("jules_api_key") or os.getenv("JULES_API_KEY")

        if not api_key:
            print("[SERVER] Cannot perform initial fleet sync: No Jules API Key found.")
            return

        agent = JulesAgent(api_key=api_key)
        response = await agent.list_sources()

        sources = []
        if response and isinstance(response, dict) and "sources" in response:
            sources = response["sources"]
        elif isinstance(response, list):
            sources = response

        if sources:
            # Use to_thread to prevent blocking if it does any heavy IO

            results, status = await asyncio.to_thread(project_manager.sync_jules_repos, sources)
            print(f"[SERVER] Initial fleet sync complete. Status: {status}")
        else:
            print("[SERVER] Initial fleet sync: No sources found or failed to fetch.")

    except Exception as e:
        print(f"[SERVER] Error during initial fleet sync: {e}")

def sync_fleet_agent_pool():
    accounts = get_all_accounts()
    total_max = 0
    if not accounts:
        total_max = 15
    else:
        for account in accounts:
            limit = account.get("concurrent_sessions_limit")
            if limit is None:
                total_max += 15 # Default for unlimited/unspecified
            else:
                total_max += limit

    fleet_manager.update_max_agents(total_max)

async def startup_event():
    init_db()
    sync_fleet_agent_pool()
    global server_loop
    server_loop = asyncio.get_running_loop()
    global slack_agent, scraper_agent, log_monitor
    import sys
    print(f"[SERVER DEBUG] Startup Event Triggered")
    print(f"[SERVER DEBUG] Python Version: {sys.version}")
    try:
        loop = asyncio.get_running_loop()
        print(f"[SERVER DEBUG] Running Loop: {type(loop)}")
        policy = asyncio.get_event_loop_policy()
        print(f"[SERVER DEBUG] Current Policy: {type(policy)}")
    except Exception as e:
        print(f"[SERVER DEBUG] Error checking loop: {e}")

    # Initialize Log Monitor
    try:
        from log_monitor import LogMonitor
        print("[SERVER] Startup: Initializing Log Monitor...")
        # Get the running loop to pass to the monitor for thread-safe callbacks
        current_loop = asyncio.get_running_loop()
        log_monitor = LogMonitor(callback=handle_runtime_error, loop=current_loop)
        log_monitor.install()
    except Exception as e:
        print(f"[SERVER] Failed to install LogMonitor: {e}")
        import traceback
        traceback.print_exc()

    # Initialize Bug Hunter
    try:
        print("[SERVER] Startup: Initializing Bug Hunter...")
        bug_hunter = BugHunter(project_root, callback=handle_bug_hunter_notification)
        bug_hunter.start()
    except Exception as e:
        print(f"[SERVER] Failed to install BugHunter: {e}")
        traceback.print_exc()

    print("[SERVER] Startup: Initializing Kasa Agent...")
    await kasa_agent.initialize()

    print("[SERVER] Startup: Initializing Slack Agent...")
    slack_agent = SlackAgent(on_message=handle_slack_message)
    asyncio.create_task(slack_agent.start())
    print("[SERVER] Slack Agent startup task created.")

    print("[SERVER] Startup: Initializing Scraper Agent...")
    scraper_agent = ScraperAgent()
    print("[SERVER] Scraper Agent initialized.")

    global task_manager, automation_engine
    print("[SERVER] Startup: Initializing Automation Engine...")
    task_manager = TaskManager(project_manager.get_current_project_path())
    automation_engine = AutomationEngine(task_manager, project_manager)
    asyncio.create_task(automation_engine.start())
    print("[SERVER] Automation Engine started.")

    print("[SERVER] Startup: Triggering initial fleet sync...")
    asyncio.create_task(initial_fleet_sync())


@app.get("/status")
async def status():
    return {"status": "running", "service": "A.D.A Backend"}

@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")
    await sio.emit('status', {'msg': 'Connected to A.D.A Backend'}, room=sid)

    global authenticator
    
    # Callback for Auth Status
    async def on_auth_status(is_auth):
        print(f"[SERVER] Auth status change: {is_auth}")
        await sio.emit('auth_status', {'authenticated': is_auth})

        if is_auth:
            # Trigger briefing check
            asyncio.create_task(check_morning_briefing_trigger())

    # Callback for Auth Camera Frames
    async def on_auth_frame(frame_b64):
        await sio.emit('auth_frame', {'image': frame_b64})

    # Initialize Authenticator if not already done
    if authenticator is None:
        authenticator = FaceAuthenticator(
            reference_image_path="reference.jpg",
            on_status_change=on_auth_status,
            on_frame=on_auth_frame
        )
    
    # Check if already authenticated or needs to start
    if authenticator.authenticated:
        await sio.emit('auth_status', {'authenticated': True})
    else:
        # Check Settings for Auth
        if SETTINGS.get("face_auth_enabled", False):
            await sio.emit('auth_status', {'authenticated': False})
            # Start the auth loop in background
            asyncio.create_task(authenticator.start_authentication_loop())
        else:
            # Bypass Auth
            print("Face Auth Disabled. Auto-authenticating.")
            # We don't change authenticator state to true to avoid confusion if re-enabled? 
            # Or we should just tell client it's auth'd.
            await sio.emit('auth_status', {'authenticated': True})

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")

@sio.event
async def start_audio(sid, data=None):
    global audio_loop, loop_task
    
    # Optional: Block if not authenticated
    # Only block if auth is ENABLED and not authenticated
    if SETTINGS.get("face_auth_enabled", False):
        if authenticator and not authenticator.authenticated:
            print("Blocked start_audio: Not authenticated.")
            await sio.emit('error', {'msg': 'Authentication Required'})
            return

    print("Starting Audio Loop...")
    
    device_index = None
    device_name = None
    if data:
        if 'device_index' in data:
            device_index = data['device_index']
        if 'device_name' in data:
            device_name = data['device_name']
            
    print(f"Using input device: Name='{device_name}', Index={device_index}")
    
    if audio_loop:
        if loop_task and not loop_task.is_alive():
             print("Audio loop task appeared finished/cancelled. Clearing and restarting...")
             audio_loop = None
             loop_task = None
        else:
             print("Audio loop already running. Re-connecting client to session.")
             await sio.emit('status', {'msg': 'A.D.A Already Running'})
             return


    # Callback to send audio data to frontend
    def on_audio_data(data_bytes):
        # Schedule on the main server event loop since this is called from the audio thread
        global server_loop
        if server_loop:
            asyncio.run_coroutine_threadsafe(sio.emit('audio_data', {'data': data_bytes}), server_loop)

    # Callback to send CAL data to frontend
    def on_cad_data(data):
        info = f"{len(data.get('vertices', []))} vertices" if 'vertices' in data else f"{len(data.get('data', ''))} bytes (STL)"
        print(f"Sending CAD data to frontend: {info}")
        if server_loop:

            asyncio.run_coroutine_threadsafe(sio.emit('cad_data', data), server_loop)

    # Callback to send Browser data to frontend
    def on_web_data(data):
        print(f"Sending Browser data to frontend: {len(data.get('log', ''))} chars logs")
        if server_loop:

            asyncio.run_coroutine_threadsafe(sio.emit('browser_frame', data), server_loop)
        
    # Callback to send Transcription data to frontend
    def on_transcription(data):
        # data = {"sender": "User"|"ADA", "text": "..."}
        if server_loop:

            asyncio.run_coroutine_threadsafe(sio.emit('transcription', data), server_loop)

    # Callback to send Confirmation Request to frontend
    def on_tool_confirmation(data):
        # data = {"id": "uuid", "tool": "tool_name", "args": {...}}
        print(f"Requesting confirmation for tool: {data.get('tool')}")
        if server_loop:

            asyncio.run_coroutine_threadsafe(sio.emit('tool_confirmation_request', data), server_loop)

    # Callback to send CAD status to frontend
    def on_cad_status(status):
        # status can be: 
        # - a string like "generating" (from ada.py handle_cad_request)
        # - a dict with {status, attempt, max_attempts, error} (from CadAgent)
        if isinstance(status, dict):
            print(f"Sending CAD Status: {status.get('status')} (attempt {status.get('attempt')}/{status.get('max_attempts')})")
            if server_loop:

                asyncio.run_coroutine_threadsafe(sio.emit('cad_status', status), server_loop)
        else:
            # Legacy: simple string
            print(f"Sending CAD Status: {status}")
            if server_loop:

                asyncio.run_coroutine_threadsafe(sio.emit('cad_status', {'status': status}), server_loop)

    # Callback to send CAD thoughts to frontend (streaming)
    def on_cad_thought(thought_text):
        if server_loop:

            asyncio.run_coroutine_threadsafe(sio.emit('cad_thought', {'text': thought_text}), server_loop)

    # Callback to send Project Update to frontend
    def on_project_update(project_name):
        print(f"Sending Project Update: {project_name}")
        if server_loop:

            asyncio.run_coroutine_threadsafe(sio.emit('project_update', {'project': project_name}), server_loop)

    # Callback to send Device Update to frontend
    def on_device_update(devices):
        # devices is a list of dicts
        print(f"Sending Kasa Device Update: {len(devices)} devices")
        if server_loop:

            asyncio.run_coroutine_threadsafe(sio.emit('kasa_devices', devices), server_loop)

    # Callback to send Error to frontend
    def on_error(msg):
        print(f"Sending Error to frontend: {msg}")
        if server_loop:

            asyncio.run_coroutine_threadsafe(sio.emit('error', {'msg': msg}), server_loop)

    def on_display_content(data):
        print(f"Sending display content to frontend: {data}")
        if data.get("content_type") == "suggestion":
            if server_loop:

                asyncio.run_coroutine_threadsafe(sio.emit('proactive_suggestion', {"suggestion": data.get("suggestion")}), server_loop)
        else:
            if server_loop:

                asyncio.run_coroutine_threadsafe(sio.emit('display_content', data), server_loop)

    # Initialize ADA
    try:
        print(f"Initializing AudioLoop with device_index={device_index}")
        audio_loop = ada.AudioLoop(
            sio=sio,
            video_mode="none", 
            on_audio_data=on_audio_data,
            on_cad_data=on_cad_data,
            on_web_data=on_web_data,
            on_transcription=on_transcription,
            on_tool_confirmation=on_tool_confirmation,
            on_cad_status=on_cad_status,
            on_cad_thought=on_cad_thought,
            on_project_update=on_project_update,
            on_device_update=on_device_update,
            on_error=on_error,
            on_display_content=on_display_content,

            input_device_index=device_index,
            input_device_name=device_name,
            kasa_agent=kasa_agent,
            project_manager=project_manager,
            slack_agent=slack_agent,
            scraper_agent=scraper_agent
        )
        print("AudioLoop initialized successfully.")

        # Apply current permissions
        audio_loop.update_permissions(SETTINGS["tool_permissions"])
        
        # Check initial mute state
        if data and data.get('muted', False):
            print("Starting with Audio Paused")
            audio_loop.set_paused(True)

        print("Creating asyncio task for AudioLoop.run()")
        def run_audio_loop_in_thread(loop_instance):
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                new_loop.run_until_complete(loop_instance.run())
            finally:
                new_loop.close()

        loop_task = threading.Thread(target=run_audio_loop_in_thread, args=(audio_loop,), daemon=True)
        loop_task.start()

        
        audio_loop.update_agent.sio = sio

        # Connect Automation Engine to Ada for notifications
        if automation_engine:
            automation_engine.ada = audio_loop
            audio_loop.automation_engine = automation_engine
            print("[SERVER] Connected Automation Engine to Ada instance (Bidirectional).")

        # Trigger initial briefing check after a short delay to allow connection
        async def delayed_briefing_check():
            await asyncio.sleep(3)
            await check_morning_briefing_trigger()
        asyncio.create_task(delayed_briefing_check())

        print("Emitting 'A.D.A Started'")
        await sio.emit('status', {'msg': 'A.D.A Started'})

        # Load saved printers
        saved_printers = SETTINGS.get("printers", [])
        if audio_loop.printer_agent:
            print(f"[SERVER] Loading {len(saved_printers)} saved printers...")
            for p in saved_printers:
                audio_loop.printer_agent.add_printer_manually(
                    name=p.get("name", p["host"]),
                    host=p["host"],
                    port=p.get("port", 80),
                    printer_type=p.get("type", "moonraker"),
                    camera_url=p.get("camera_url")
                )
        
        # Start Printer Monitor
        asyncio.create_task(monitor_printers_loop())
        
    except Exception as e:
        print(f"CRITICAL ERROR STARTING ADA: {e}")
        import traceback
        traceback.print_exc()
        await sio.emit('error', {'msg': f"Failed to start: {str(e)}"})
        audio_loop = None # Ensure we can try again


async def check_morning_briefing_trigger():
    """Checks if a morning briefing is pending and triggers it if appropriate."""
    if not automation_engine or not audio_loop:
        return

    if automation_engine.briefing_status == "PENDING":
        print("[SERVER] Triggering Morning Briefing Offer...")

        # Use a system notification to prompt the model
        # We phrase it as a "System Notification" telling the model what to do.
        msg = "System Notification: The user's Daily Morning Briefing is ready (generated at 09:00). Please politely inform the user: 'Good morning, Sir. I have your daily briefing ready. Would you like to hear it?'"

        # Ensure session is active.
        if audio_loop.session:
             try:
                 await audio_loop.session.send(input=msg, end_of_turn=True)
             except Exception as e:
                 print(f"[SERVER] Failed to trigger briefing: {e}")

async def monitor_printers_loop():
    """Background task to query printer status periodically."""
    print("[SERVER] Starting Printer Monitor Loop")
    while audio_loop and audio_loop.printer_agent:
        try:
            agent = audio_loop.printer_agent
            if not agent.printers:
                await asyncio.sleep(5)
                continue
                
            tasks = []
            for host, printer in agent.printers.items():
                if printer.printer_type.value != "unknown":
                    tasks.append(agent.get_print_status(host))
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, Exception):
                        pass # Ignore errors for now
                    elif res:
                        # res is PrintStatus object
                        await sio.emit('print_status_update', res.to_dict())
                        
        except asyncio.CancelledError:
            print("[SERVER] Printer Monitor Cancelled")
            break
        except Exception as e:
            print(f"[SERVER] Monitor Loop Error: {e}")
            
        await asyncio.sleep(2) # Update every 2 seconds for responsiveness

@sio.event
async def stop_audio(sid):
    global audio_loop
    if audio_loop:
        audio_loop.stop() 
        print("Stopping Audio Loop")
        audio_loop = None
        await sio.emit('status', {'msg': 'A.D.A Stopped'})

@sio.event
async def pause_audio(sid):
    global audio_loop
    if audio_loop:
        audio_loop.set_paused(True)
        print("Pausing Audio")
        await sio.emit('status', {'msg': 'Audio Paused'})

@sio.event
async def resume_audio(sid):
    global audio_loop
    if audio_loop:
        audio_loop.set_paused(False)
        print("Resuming Audio")
        await sio.emit('status', {'msg': 'Audio Resumed'})

@sio.event
async def confirm_tool(sid, data):
    # data: { "id": "...", "confirmed": True/False }
    request_id = data.get('id')
    confirmed = data.get('confirmed', False)
    
    print(f"[SERVER DEBUG] Received confirmation response for {request_id}: {confirmed}")
    
    if audio_loop:
        audio_loop.resolve_tool_confirmation(request_id, confirmed)
    else:
        print("Audio loop not active, cannot resolve confirmation.")

@sio.event
async def shutdown(sid, data=None):
    """Gracefully shutdown the server when the application closes."""
    global audio_loop, loop_task, authenticator

    print("[SERVER] ========================================")
    print("[SERVER] SHUTDOWN SIGNAL RECEIVED FROM FRONTEND")
    print("[SERVER] ========================================")

    # Stop audio loop
    if audio_loop:
        print("[SERVER] Stopping Audio Loop...")
        audio_loop.stop()
        audio_loop = None

    # Cancel the loop task if running
    if loop_task and loop_task.is_alive():
        print("[SERVER] Joining loop task...")
        await asyncio.to_thread(loop_task.join, 2.0)
        loop_task = None

    # Stop authenticator if running
    if authenticator:
        print("[SERVER] Stopping Authenticator...")
        authenticator.stop()

    if automation_engine:
        print("[SERVER] Stopping Automation Engine...")
        automation_engine.stop()

    print("[SERVER] Graceful shutdown complete. Terminating process...")

    # Force exit immediately - os._exit bypasses cleanup but ensures termination
    if data and data.get("restart"):
        print("[SERVER] Restarting application...")
        import subprocess
        # Use sys.executable to restart the backend with the same python interpreter
        # and use Popen with a new process group to ensure it survives our exit
        try:
            # Re-run the same command that started this script
            # sys.executable is the path to python.exe
            # sys.argv[0] is server.py
            # We want to make sure we are in the right directory
            backend_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(backend_dir)

            if sys.platform == 'win32':
                # On Windows, we can use start to launch a new console window or just spawn it detached
                # npm run dev is what the original code used, maybe it's preferred to restart EVERYTHING
                # Let's try to stick to what the user had but make it more robust
                subprocess.Popen("npm run dev", shell=True, cwd=project_root, creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                subprocess.Popen("npm run dev", shell=True, cwd=project_root)
        except Exception as e:
            print(f"[SERVER] Failed to restart: {e}")

        os._exit(0)
    else:
        os._exit(0)

@sio.event
async def restart_request(sid, data=None):
    """Restart the application after an update."""
    print("[SERVER] Restart request received.")
    await shutdown(sid, {"restart": True})

@sio.event
async def user_input(sid, data):
    text = data.get('text')
    msg_id = data.get('id')

    # Deduplication for UI Inputs
    # If frontend sends an ID, use it. Otherwise, hash the content + rough time.
    # Note: Hashing content alone is risky if user types "hello" twice.
    # We rely on the fact that if a user re-submits, it's a new intent.
    # BUT, if the socket reconnects and replays, it will be the SAME text at roughly the same time.
    # If the frontend is smart, it adds a UUID. If not, we do our best.

    if msg_id:
        if not ui_deduplicator.check_and_add(msg_id):
            print(f"[SERVER] Duplicate UI message ID {msg_id}. Ignoring.")
            return
    else:
        # Fallback: Hash content + timestamp (to 1-second precision)
        # This prevents the EXACT same message arriving in the same second from being processed twice.
        # This is a heuristic to stop rapid-fire duplicates from network glitches.
        import time
        import hashlib
        # Use 2-second window to be safe against slight network delays
        timestamp_key = int(time.time() / 2)
        content_hash = hashlib.sha256(f"{text}-{timestamp_key}".encode()).hexdigest()
        if not ui_deduplicator.check_and_add(content_hash):
             print(f"[SERVER] Duplicate UI message content (heuristic) '{text}'. Ignoring.")
             return

    print(f"[SERVER DEBUG] User input received: '{text}'")
    
    if not audio_loop:
        print("[SERVER DEBUG] [Error] Audio loop is None. Cannot send text.")
        await sio.emit('error', {'msg': 'System not ready (Audio Loop inactive)'})
        return

    if not audio_loop.session:
        print("[SERVER DEBUG] [Error] Session is None. Cannot send text.")
        await sio.emit('error', {'msg': 'System not ready (No active session)'})
        return

    if text:
        print(f"[SERVER DEBUG] Sending message to model: '{text}'")
        
        # Log User Input to Project History
        if audio_loop and audio_loop.project_manager:
            audio_loop.project_manager.log_chat("User", text)
            
        # Use the same 'send' method that worked for audio, as 'send_realtime_input' and 'send_client_content' seem unstable in this env
        # INJECT VIDEO FRAME IF AVAILABLE (VAD-style logic for Text Input)
        if audio_loop and audio_loop._latest_image_payload:
            print(f"[SERVER DEBUG] Piggybacking video frame with text input.")
            try:
                # Send frame first
                await audio_loop.session.send(input=audio_loop._latest_image_payload, end_of_turn=False)
            except Exception as e:
                print(f"[SERVER DEBUG] Failed to send piggyback frame: {e}")

        # Explicitly flush/interrupt audio queue to simulate "interrupt" behavior for text input
        # This mirrors what happens when VAD detects speech
        audio_loop.clear_audio_queue()
        audio_loop.set_last_input_source('ui')

        try:
            await audio_loop.session.send(input=text, end_of_turn=True)
            print(f"[SERVER DEBUG] Message sent to model successfully.")
        except Exception as e:
             print(f"[SERVER DEBUG] Failed to send text to model: {e}")
             await sio.emit('error', {'msg': f"Failed to send message: {e}"})

import json
from datetime import datetime
from pathlib import Path

# ... (imports)

@sio.event
async def video_frame(sid, data):
    # data should contain 'image' which is binary (blob) or base64 encoded
    image_data = data.get('image')
    if image_data and audio_loop:
        # We don't await this because we don't want to block the socket handler
        # But send_frame is async, so we create a task
        asyncio.create_task(audio_loop.send_frame(image_data))

@sio.event
async def save_memory(sid, data):
    try:
        messages = data.get('messages', [])
        if not messages:
            print("No messages to save.")
            return

        # Ensure directory exists
        memory_dir = Path("long_term_memory")
        memory_dir.mkdir(exist_ok=True)

        # Generate filename
        # Use provided filename if available, else timestamp
        provided_name = data.get('filename')
        
        if provided_name:
            # Simple sanitization
            if not provided_name.endswith('.txt'):
                provided_name += '.txt'
            # Prevent directory traversal
            filename = memory_dir / Path(provided_name).name 
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = memory_dir / f"memory_{timestamp}.txt"

        # Write to file
        with open(filename, 'w', encoding='utf-8') as f:
            for msg in messages:
                sender = msg.get('sender', 'Unknown')
                text = msg.get('text', '')
        print(f"Conversation saved to {filename}")
        await sio.emit('status', {'msg': 'Memory Saved Successfully'})

    except Exception as e:
        print(f"Error saving memory: {e}")
        await sio.emit('error', {'msg': f"Failed to save memory: {str(e)}"})

@sio.event
async def upload_memory(sid, data):
    print(f"Received memory upload request")
    try:
        memory_text = data.get('memory', '')
        if not memory_text:
            print("No memory data provided.")
            return

        if not audio_loop:
             print("[SERVER DEBUG] [Error] Audio loop is None. Cannot load memory.")
             await sio.emit('error', {'msg': "System not ready (Audio Loop inactive)"})
             return
        
        if not audio_loop.session:
             print("[SERVER DEBUG] [Error] Session is None. Cannot load memory.")
             await sio.emit('error', {'msg': "System not ready (No active session)"})
             return

        # Send to model
        print("Sending memory context to model...")
        context_msg = f"System Notification: The user has uploaded a long-term memory file. Please load the following context into your understanding. The format is a text log of previous conversations:\n\n{memory_text}"
        
        await audio_loop.session.send(input=context_msg, end_of_turn=True)
        print("Memory context sent successfully.")
        await sio.emit('status', {'msg': 'Memory Loaded into Context'})

    except Exception as e:
        print(f"Error uploading memory: {e}")
        await sio.emit('error', {'msg': f"Failed to upload memory: {str(e)}"})

@sio.event
async def discover_kasa(sid):
    print(f"Received discover_kasa request")
    try:
        devices = await kasa_agent.discover_devices()
        await sio.emit('kasa_devices', devices)
        await sio.emit('status', {'msg': f"Found {len(devices)} Kasa devices"})
        
        # Save to settings
        # devices is a list of full device info dicts. minimizing for storage.
        saved_devices = []
        for d in devices:
            saved_devices.append({
                "ip": d["ip"],
                "alias": d["alias"],
                "model": d["model"]
            })
        
        # Merge with existing to preserve any manual overrides? 
        # For now, just overwrite with latest scan result + previously known if we want to be fancy,
        # but user asked for "Any new devices that are scanned are added there".
        # A simple full persistence of current state is safest.
        SETTINGS["kasa_devices"] = saved_devices
        save_settings()
        print(f"[SERVER] Saved {len(saved_devices)} Kasa devices to settings.")
        
    except Exception as e:
        print(f"Error discovering kasa: {e}")
        await sio.emit('error', {'msg': f"Kasa Discovery Failed: {str(e)}"})

@sio.event
async def iterate_cad(sid, data):
    # data: { prompt: "make it bigger" }
    prompt = data.get('prompt')
    print(f"Received iterate_cad request: '{prompt}'")
    
    if not audio_loop or not audio_loop.cad_agent:
        await sio.emit('error', {'msg': "CAD Agent not available"})
        return

    try:
        # Notify user work has started
        await sio.emit('status', {'msg': 'Iterating design...'})
        await sio.emit('cad_status', {'status': 'generating'})
        
        # Call the agent with project path
        cad_output_dir = str(audio_loop.project_manager.get_current_project_path() / "cad")
        result = await audio_loop.cad_agent.iterate_prototype(prompt, output_dir=cad_output_dir)
        
        if result:
            info = f"{len(result.get('data', ''))} bytes (STL)"
            print(f"Sending updated CAD data: {info}")
            await sio.emit('cad_data', result)
            # Save to Project
            if 'file_path' in result:
                saved_path = audio_loop.project_manager.save_cad_artifact(result['file_path'], prompt)
                if saved_path:
                    print(f"[SERVER] Saved iterated CAD to {saved_path}")

            await sio.emit('status', {'msg': 'Design updated'})
        else:
            await sio.emit('error', {'msg': 'Failed to update design'})
            
    except Exception as e:
        print(f"Error iterating CAD: {e}")
        await sio.emit('error', {'msg': f"Iteration Error: {str(e)}"})

@sio.event
async def generate_cad(sid, data):
    # data: { prompt: "make a cube" }
    prompt = data.get('prompt')
    print(f"Received generate_cad request: '{prompt}'")
    
    if not audio_loop or not audio_loop.cad_agent:
        await sio.emit('error', {'msg': "CAD Agent not available"})
        return

    try:
        await sio.emit('status', {'msg': 'Generating new design...'})
        await sio.emit('cad_status', {'status': 'generating'})
        
        # Use generate_prototype based on prompt with project path
        cad_output_dir = str(audio_loop.project_manager.get_current_project_path() / "cad")
        result = await audio_loop.cad_agent.generate_prototype(prompt, output_dir=cad_output_dir)
        
        if result:
            info = f"{len(result.get('data', ''))} bytes (STL)"
            print(f"Sending newly generated CAD data: {info}")
            await sio.emit('cad_data', result)


            # Save to Project
            if 'file_path' in result:
                saved_path = audio_loop.project_manager.save_cad_artifact(result['file_path'], prompt)
                if saved_path:
                    print(f"[SERVER] Saved generated CAD to {saved_path}")

            await sio.emit('status', {'msg': 'Design generated'})
        else:
            await sio.emit('error', {'msg': 'Failed to generate design'})
            
    except Exception as e:
        print(f"Error generating CAD: {e}")
        await sio.emit('error', {'msg': f"Generation Error: {str(e)}"})

@sio.event
async def prompt_web_agent(sid, data):
    # data: { prompt: "find xyz" }
    prompt = data.get('prompt')
    print(f"Received web agent prompt: '{prompt}'")
    
    if not audio_loop or not audio_loop.web_agent:
        await sio.emit('error', {'msg': "Web Agent not available"})
        return

    try:
        await sio.emit('status', {'msg': 'Web Agent running...'})
        
        # We assume web_agent has a run method or similar.
        # This might block the loop if not strictly async or offloaded.
        # Ideally web_agent.run is async.
        # And it should emit 'browser_snap' and logs automatically via hooks if setup.
        
        # We might need to launch this as a task if it's long running?
        # asyncio.create_task(audio_loop.web_agent.run(prompt))
        # But we want to catch errors here.
        
        # Based on typical agent design, run() is the entry point.
        await audio_loop.web_agent.run(prompt)
        
        await sio.emit('status', {'msg': 'Web Agent finished'})
        
    except Exception as e:
        print(f"Error running Web Agent: {e}")
        await sio.emit('error', {'msg': f"Web Agent Error: {str(e)}"})

@sio.event
async def discover_printers(sid):
    print("Received discover_printers request")
    
    # If audio_loop isn't ready yet, return saved printers from settings
    if not audio_loop or not audio_loop.printer_agent:
        saved_printers = SETTINGS.get("printers", [])
        if saved_printers:
            # Convert saved printers to the expected format
            printer_list = []
            for p in saved_printers:
                printer_list.append({
                    "name": p.get("name", p["host"]),
                    "host": p["host"],
                    "port": p.get("port", 80),
                    "printer_type": p.get("type", "unknown"),
                    "camera_url": p.get("camera_url")
                })
            print(f"[SERVER] Returning {len(printer_list)} saved printers (audio_loop not ready)")
            await sio.emit('printer_list', printer_list)
            return
        else:
            await sio.emit('printer_list', [])
            await sio.emit('status', {'msg': "Connect to A.D.A to enable printer discovery"})
            return
        
    try:
        printers = await audio_loop.printer_agent.discover_printers()
        await sio.emit('printer_list', printers)
        await sio.emit('status', {'msg': f"Found {len(printers)} printers"})
    except Exception as e:
        print(f"Error discovering printers: {e}")
        await sio.emit('error', {'msg': f"Printer Discovery Failed: {str(e)}"})

@sio.event
async def add_printer(sid, data):
    # data: { host: "192.168.1.50", name: "My Printer", type: "moonraker" }
    raw_host = data.get('host')
    name = data.get('name') or raw_host
    ptype = data.get('type', "moonraker")
    
    # Parse port if present
    if ":" in raw_host:
        host, port_str = raw_host.split(":")
        port = int(port_str)
    else:
        host = raw_host
        port = 80
    
    print(f"Received add_printer request: {host}:{port} ({ptype})")
    
    if not audio_loop or not audio_loop.printer_agent:
        await sio.emit('error', {'msg': "Printer Agent not available"})
        return
        
    try:
        # Add manually
        camera_url = data.get('camera_url')
        printer = audio_loop.printer_agent.add_printer_manually(name, host, port=port, printer_type=ptype, camera_url=camera_url)
        
        # Save to settings
        new_printer_config = {
            "name": name,
            "host": host,
            "port": port,
            "type": ptype,
            "camera_url": camera_url
        }
        
        # Check if already exists to avoid duplicates
        exists = False
        for p in SETTINGS.get("printers", []):
            if p["host"] == host and p["port"] == port:
                exists = True
                break
        
        if not exists:
            if "printers" not in SETTINGS:
                SETTINGS["printers"] = []
            SETTINGS["printers"].append(new_printer_config)
            save_settings()
            print(f"[SERVER] Saved printer {name} to settings.")
        
        # Probe to confirm/correct type
        print(f"Probing {host} to confirm type...")
        # Try port 7125 (Moonraker) and 4408 (Fluidd/K1) 
        ports_to_try = [80, 7125, 4408]
        
        actual_type = "unknown"
        for port in ports_to_try:
             found_type = await audio_loop.printer_agent._probe_printer_type(host, port)
             if found_type.value != "unknown":
                 actual_type = found_type
                 # Update port if different
                 if port != 80:
                     printer.port = port
                 break
        
        if actual_type != "unknown" and actual_type != printer.printer_type:
             printer.printer_type = actual_type
             print(f"Corrected type to {actual_type.value} on port {printer.port}")
             
        # Refresh list for everyone
        printers = [p.to_dict() for p in audio_loop.printer_agent.printers.values()]
        await sio.emit('printer_list', printers)
        await sio.emit('status', {'msg': f"Added printer: {name}"})
        
    except Exception as e:
        print(f"Error adding printer: {e}")
        await sio.emit('error', {'msg': f"Failed to add printer: {str(e)}"})

@sio.event
async def print_stl(sid, data):
    print(f"Received print_stl request: {data}")
    # data: { stl_path: "path/to.stl" | "current", printer: "name_or_ip", profile: "optional" }
    
    if not audio_loop or not audio_loop.printer_agent:
        await sio.emit('error', {'msg': "Printer Agent not available"})
        return
        
    try:
        stl_path = data.get('stl_path', 'current')
        printer_name = data.get('printer')
        profile = data.get('profile')
        
        if not printer_name:
             await sio.emit('error', {'msg': "No printer specified"})
             return
             
        await sio.emit('status', {'msg': f"Preparing print for {printer_name}..."})
        
        # Get current project path for resolution
        current_project_path = None
        if audio_loop and audio_loop.project_manager:
            current_project_path = str(audio_loop.project_manager.get_current_project_path())
            print(f"[SERVER DEBUG] Using project path: {current_project_path}")

        # Resolve STL path before slicing so we can preview it
        resolved_stl = audio_loop.printer_agent._resolve_file_path(stl_path, current_project_path)
        
        if resolved_stl and os.path.exists(resolved_stl):
            # Open the STL in the CAD module for preview
            try:
                import base64
                with open(resolved_stl, 'rb') as f:
                    stl_data = f.read()
                stl_b64 = base64.b64encode(stl_data).decode('utf-8')
                stl_filename = os.path.basename(resolved_stl)
                
                print(f"[SERVER] Opening STL in CAD module: {stl_filename}")
                await sio.emit('cad_data', {
                    'format': 'stl',
                    'data': stl_b64,
                    'filename': stl_filename
                })
            except Exception as e:
                print(f"[SERVER] Warning: Could not preview STL: {e}")
        
        # Progress Callback
        async def on_slicing_progress(percent, message):
            await sio.emit('slicing_progress', {
                'printer': printer_name,
                'percent': percent,
                'message': message
            })
            if percent < 100:
                 await sio.emit('status', {'msg': f"Slicing: {percent}%"})

        result = await audio_loop.printer_agent.print_stl(
            stl_path, 
            printer_name, 
            profile,
            progress_callback=on_slicing_progress,
            root_path=current_project_path
        )
        
        await sio.emit('print_result', result)
        await sio.emit('status', {'msg': f"Print Job: {result.get('status', 'unknown')}"})
        
    except Exception as e:
        print(f"Error printing STL: {e}")
        await sio.emit('error', {'msg': f"Print Failed: {str(e)}"})

@sio.event
async def get_slicer_profiles(sid):
    """Get available OrcaSlicer profiles for manual selection."""
    print("Received get_slicer_profiles request")
    if not audio_loop or not audio_loop.printer_agent:
        await sio.emit('error', {'msg': "Printer Agent not available"})
        return
    
    try:
        profiles = audio_loop.printer_agent.get_available_profiles()
        await sio.emit('slicer_profiles', profiles)
    except Exception as e:
        print(f"Error getting slicer profiles: {e}")
        await sio.emit('error', {'msg': f"Failed to get profiles: {str(e)}"})

@sio.event
async def control_music(sid, data):
    # data: { action: "play"|"pause"|"next"|... }
    action = data.get('action')
    print(f"Received music control: {action}")

    if not audio_loop or not audio_loop.music_agent:
        await sio.emit('error', {'msg': "Music Agent not available"})
        return

    try:
        result = await audio_loop.music_agent.control(action)
        # We don't necessarily need to emit status back as the status loop handles it
        # but a confirmation log is nice
        print(f"Music Control Result: {result}")
    except Exception as e:
        print(f"Error controlling music: {e}")
        await sio.emit('error', {'msg': f"Music Control Error: {str(e)}"})

@sio.event
async def control_kasa(sid, data):
    # data: { ip, action: "on"|"off"|"brightness"|"color", value: ... }
    ip = data.get('ip')
    action = data.get('action')
    print(f"Kasa Control: {ip} -> {action}")
    
    try:
        success = False
        if action == "on":
            success = await kasa_agent.turn_on(ip)
        elif action == "off":
            success = await kasa_agent.turn_off(ip)
        elif action == "brightness":
            val = data.get('value')
            success = await kasa_agent.set_brightness(ip, val)
        elif action == "color":
            # value is {h, s, v} - convert to tuple for set_color
            h = data.get('value', {}).get('h', 0)
            s = data.get('value', {}).get('s', 100)
            v = data.get('value', {}).get('v', 100)
            success = await kasa_agent.set_color(ip, (h, s, v))
        
        if success:
            await sio.emit('kasa_update', {
                'ip': ip,
                'is_on': True if action == "on" else (False if action == "off" else None),
                'brightness': data.get('value') if action == "brightness" else None,
            })
 
        else:
             await sio.emit('error', {'msg': f"Failed to control device {ip}"})

    except Exception as e:
         print(f"Error controlling kasa: {e}")
         await sio.emit('error', {'msg': f"Kasa Control Error: {str(e)}"})

@sio.event
async def get_settings(sid):
    await sio.emit('settings', SETTINGS)

@sio.event
async def update_settings(sid, data):
    # Generic update
    print(f"Updating settings: {data}")
    
    # Handle specific keys if needed
    if "tool_permissions" in data:
        SETTINGS["tool_permissions"].update(data["tool_permissions"])
        if audio_loop:
            audio_loop.update_permissions(SETTINGS["tool_permissions"])
            
    if "face_auth_enabled" in data:
        SETTINGS["face_auth_enabled"] = data["face_auth_enabled"]
        # If turned OFF, maybe emit auth status true?
        if not data["face_auth_enabled"]:
             await sio.emit('auth_status', {'authenticated': True})
             # Stop auth loop if running?
             if authenticator:
                 authenticator.stop() 

    if "camera_flipped" in data:
        SETTINGS["camera_flipped"] = data["camera_flipped"]
        print(f"[SERVER] Camera flip set to: {data['camera_flipped']}")

    save_settings()
    # Broadcast new full settings
    await sio.emit('settings', SETTINGS)

@sio.event
async def delete_timer(sid, data):
    """Handles request from frontend to delete a timer or reminder."""
    name = data.get('name')
    if name and audio_loop and audio_loop.timer_agent:
        print(f"Received delete_timer request for: {name}")
        result = audio_loop.timer_agent.delete_entry(name)
        # The broadcast loop in TimerAgent will handle updating clients,
        # but we can send a confirmation or the result back.
        await sio.emit('status', {'msg': result})
    else:
        await sio.emit('error', {'msg': 'Failed to delete timer.'})

@sio.event
async def get_project_config(sid):
    if audio_loop and audio_loop.project_manager:
        config = audio_loop.project_manager.get_project_config()
        await sio.emit('project_config', config)

@sio.event
async def toggle_writing_mode(sid, data):
    if audio_loop and audio_loop.project_manager:
        enable = data.get('enable', False)
        success, msg = audio_loop.project_manager.update_project_config({'mode': 'writing' if enable else 'default'})
        if success:
            await sio.emit('status', {'msg': f"Writing mode {'enabled' if enable else 'disabled'}"})
            config = audio_loop.project_manager.get_project_config()
            await sio.emit('project_config', config)
        else:
            await sio.emit('error', {'msg': msg})

@sio.event
async def update_project_config(sid, data):
    if audio_loop and audio_loop.project_manager:
        success, msg = audio_loop.project_manager.update_project_config(data)
        if success:
            await sio.emit('status', {'msg': 'Project config updated'})
            # Re-emit the updated config to all clients
            config = project_manager.get_project_config()
            await sio.emit('project_config', config)

            # Check if system prompt or voice changed, and if so, reconnect
            if 'system_prompt' in data or 'voice_name' in data:
                if audio_loop:
                    print("[SERVER] System prompt or voice changed, reconnecting audio loop...")
                    audio_loop.reconnect()
        else:
            await sio.emit('error', {'msg': msg})

@sio.event
async def switch_project(sid, data):
    project_name = data.get('project_name')
    if project_name:
        success, msg = project_manager.switch_project(project_name)
        if success:
            await sio.emit('project_update', {'project': project_name})
            await sio.emit('status', {'msg': f"Switched to project: {project_name}"})
            if audio_loop:
                audio_loop.reconnect()
        else:
            await sio.emit('error', {'msg': msg})

@sio.event
async def create_project(sid, data):
    project_name = data.get('project_name')
    if project_name:
        success, msg = project_manager.create_project(project_name)
        if success:
            # Switch to the new project automatically
            project_manager.switch_project(project_name)
            await sio.emit('project_update', {'project': project_name})
            await sio.emit('status', {'msg': f"Created and switched to project: {project_name}"})
            if audio_loop:
                audio_loop.reconnect()
        else:
            await sio.emit('error', {'msg': msg})

async def dashboard_stream_loop():
    """Background task to push dashboard updates."""
    print("[SERVER] Starting Dashboard Stream Loop")
    last_data = None
    try:
        while True:
            if audio_loop:
                data = await audio_loop.get_dashboard_data()
                if data != last_data:
                    await sio.emit('dashboard_update', data)
                    last_data = data
            await asyncio.sleep(2) # Update every 2 seconds
    except asyncio.CancelledError:
        print("[SERVER] Dashboard Stream Cancelled")
    except Exception as e:
        print(f"[SERVER] Dashboard Stream Error: {e}")
        import traceback
        traceback.print_exc()

@sio.event
async def start_dashboard_stream(sid):
    global dashboard_task
    print("[SERVER] Client requested dashboard stream")
    if dashboard_task is None or dashboard_task.done():
        dashboard_task = asyncio.create_task(dashboard_stream_loop())

@sio.event
async def stop_dashboard_stream(sid):
    global dashboard_task
    print("[SERVER] Client stopped dashboard stream")
    if dashboard_task and not dashboard_task.done():
        dashboard_task.cancel()
        dashboard_task = None

@sio.event
async def create_task(sid, data):
    # data: { title, trigger_type, trigger_value, action_type, action_value }
    print(f"[SERVER] Create Task: {data}")
    if audio_loop and audio_loop.task_manager:
        audio_loop.task_manager.create_task(
            title=data.get('title'),
            trigger_type=data.get('trigger_type', 'manual'),
            trigger_value=data.get('trigger_value'),
            action_type=data.get('action_type', 'none'),
            action_value=data.get('action_value')
        )
        await sio.emit('status', {'msg': 'Task created'})
        # Force an immediate push if streaming
        if dashboard_task:
            data = await audio_loop.get_dashboard_data()
            await sio.emit('dashboard_update', data)

@sio.event
async def update_task(sid, data):
    # data: { id, updates: { title, trigger, action, status... } }
    task_id = data.get('id')
    updates = data.get('updates')
    print(f"[SERVER] Update Task: {task_id} with {updates}")

    if audio_loop and audio_loop.task_manager:
        if audio_loop.task_manager.update_task(task_id, updates):
            await sio.emit('status', {'msg': 'Task updated'})
            # Force an immediate push if streaming
            if dashboard_task:
                data = await audio_loop.get_dashboard_data()
                await sio.emit('dashboard_update', data)
        else:
            await sio.emit('error', {'msg': 'Task not found or update failed'})

@sio.event
async def delete_task(sid, data):
    task_id = data.get('id')
    print(f"[SERVER] Delete Task: {task_id}")
    if audio_loop and audio_loop.task_manager:
        if audio_loop.task_manager.delete_task(task_id):
            await sio.emit('status', {'msg': 'Task deleted'})
            # Force update
            if dashboard_task:
                data = await audio_loop.get_dashboard_data()
                await sio.emit('dashboard_update', data)
        else:
             await sio.emit('error', {'msg': 'Task not found'})

@sio.event
async def delete_trello_card(sid, data):
    card_id = data.get('id')
    print(f"[SERVER] Delete Trello Card: {card_id}")
    if audio_loop and getattr(audio_loop, 'trello_agent', None):
        try:
            await audio_loop.trello_agent.delete_card(card_id)
            await sio.emit('status', {'msg': 'Trello card deleted'})
            # Force update
            if dashboard_task:
                data = await audio_loop.get_dashboard_data()
                await sio.emit('dashboard_update', data)
        except Exception as e:
             print(f"[SERVER] Error deleting Trello card: {e}")
             await sio.emit('error', {'msg': f'Error deleting Trello card: {e}'})
    else:
        await sio.emit('error', {'msg': 'Trello Agent not ready'})

@sio.event
async def apply_task_fix(sid, data):
    task_id = data.get('id')
    print(f"[SERVER] Apply Task Fix: {task_id}")
    if automation_engine:
        success, msg = automation_engine.apply_fix(task_id)
        if success:
            await sio.emit('status', {'msg': msg})
            # Force update
            if dashboard_task:
                data = await audio_loop.get_dashboard_data()
                await sio.emit('dashboard_update', data)
        else:
            await sio.emit('error', {'msg': msg})
    else:
        await sio.emit('error', {'msg': "System not ready"})

@sio.event
async def get_fleet_status(sid):
    """Fetches the current status of all git repos via GitHub API."""
    print(f"[SERVER] Client {sid} requested fleet status.")
    if audio_loop and audio_loop.project_manager:
        fleet = audio_loop.project_manager.load_fleet()
        token = audio_loop.project_manager.get_github_token()

        # Emit basic status immediately so UI has *something* fast
        basic_fleet = [{
            "name": f"{r['owner']}/{r['name']}",
            "branch": "unknown",
            "status": "Remote (Loading...)" if token else "Remote (No Auth)",
            "last_commit": None,
            "auto_merge_disabled": r.get('auto_merge_disabled', False)
        } for r in fleet]
        await sio.emit('fleet_status_update', basic_fleet, to=sid)

        if not token:
            await sio.emit('error', {'msg': "No GitHub Token found. Please Authenticate.", 'code': 'AUTH_REQUIRED'})
            return

        from github_client import GitHubClient
        client = GitHubClient(token)

        async def fetch_repo_status(repo):
            owner = repo['owner']
            name = repo['name']

            # Fetch details (basic check if exists and default branch)
            details = await client.get_repo_details(owner, name)
            if not details:
                return {"name": f"{owner}/{name}", "status": "Error accessing repo"}

            default_branch = details.get('default_branch', 'main')

            # Fetch last commit
            commit_info = None
            commit_data = await client.get_commit(owner, name, default_branch)
            if commit_data:
                c = commit_data.get('commit', {})
                author = c.get('author', {}).get('name', 'Unknown')
                date = c.get('author', {}).get('date', '')
                message = c.get('message', '')
                commit_info = {
                    "author": author,
                    "date": date,
                    "message": message
                }

            return {
                "name": f"{owner}/{name}",
                "branch": default_branch,
                "status": "Remote",
                "last_commit": commit_info,
                "auto_merge_disabled": repo.get('auto_merge_disabled', False)
            }

        # Background task to fetch detailed status without blocking the event loop
        async def fetch_all_and_emit():
            # Use a semaphore to allow some concurrency without overwhelming the event loop
            sem = asyncio.Semaphore(5)

            # We'll update the fleet list in place and emit incrementally
            # basic_fleet is already structured
            updated_fleet = list(basic_fleet)

            async def fetch_and_update(idx, repo):
                async with sem:
                    # Yield before starting the network request
                    await asyncio.sleep(0)
                    status = await fetch_repo_status(repo)
                    updated_fleet[idx] = status
                    # Emit partial update so UI doesn't hang forever
                    await sio.emit('fleet_status_update', updated_fleet, to=sid)
                    # Yield after request to ensure audio thread runs
                    await asyncio.sleep(0.01)

            tasks = [asyncio.create_task(fetch_and_update(i, repo)) for i, repo in enumerate(fleet)]

            # Wait for all background fetches to complete
            await asyncio.gather(*tasks)

        # Fire and forget the background fetch
        asyncio.create_task(fetch_all_and_emit())

@sio.event
async def get_repo_branches(sid, data):
    repo_full_name = data.get('repo') # "owner/name"
    if not repo_full_name: return

    print(f"[SERVER] Fetching branches for {repo_full_name}")
    if audio_loop and audio_loop.project_manager:
        token = audio_loop.project_manager.get_github_token()
        if not token: return

        from github_client import GitHubClient
        client = GitHubClient(token)

        parts = repo_full_name.split('/')
        if len(parts) != 2: return
        owner, name = parts

        branches = await client.get_branches(owner, name)
        details = await client.get_repo_details(owner, name)
        default_branch = details.get('default_branch', 'main')

        result = []
        if branches:
            for b in branches:
                b_name = b['name']
                is_default = b_name == default_branch

                # Check ahead/behind against default
                stats = {"ahead": 0, "behind": 0}
                if not is_default:
                    # Compare
                    cmp = await client.compare_commits(owner, name, default_branch, b_name)
                    if cmp:
                        stats["ahead"] = cmp.get("ahead_by", 0)
                        stats["behind"] = cmp.get("behind_by", 0)

                result.append({
                    "name": b_name,
                    "is_default": is_default,
                    "ahead": stats["ahead"],
                    "behind": stats["behind"]
                })

        await sio.emit('repo_branches', {"repo": repo_full_name, "branches": result})

@sio.event
async def get_branch_diff(sid, data):
    repo_full_name = data.get('repo')
    branch = data.get('branch')
    target = data.get('target', 'main')

    print(f"[SERVER] Client {sid} requested diff for {repo_full_name}: {branch} -> {target}")

    if audio_loop and audio_loop.project_manager:
        token = audio_loop.project_manager.get_github_token()
        if not token:
             await sio.emit('error', {'msg': "Authentication Required"})
             return

        from github_client import GitHubClient
        client = GitHubClient(token)

        parts = repo_full_name.split('/')
        if len(parts) != 2: return
        owner, name = parts

        # Use passed target or try to discover it?
        # Ideally the frontend sends the default branch as target.
        # compare_commits expects base...head (base=target, head=branch)

        diff_data = await client.compare_commits(owner, name, target, branch)
        if diff_data:
            files = diff_data.get('files', [])
            changes = []
            for f in files:
                changes.append({
                    "filename": f.get('filename'),
                    "status": f.get('status'),
                    "additions": f.get('additions'),
                    "deletions": f.get('deletions'),
                    "patch": f.get('patch', '')
                })

            await sio.emit('branch_diff_data', {
                "repo": repo_full_name,
                "branch": branch,
                "target": target,
                "files": changes
            })
        else:
             await sio.emit('error', {'msg': "Failed to fetch diff."})

@sio.event
async def perform_git_merge(sid, data):
    """Merges a specific repo's branch into main/master via GitHub API."""
    repo_full_name = data.get('repo')
    branch = data.get('branch')
    target = data.get('target')
    delete_source_branch = data.get('delete_source_branch', False)

    print(f"[SERVER] Client {sid} requested remote merge for {repo_full_name}: {branch} -> {target or 'DEFAULT'} (Delete: {delete_source_branch})")

    if audio_loop and audio_loop.project_manager:
        token = audio_loop.project_manager.get_github_token()
        if not token:
             await sio.emit('error', {'msg': "Authentication Required"})
             return

        from github_client import GitHubClient
        client = GitHubClient(token)

        parts = repo_full_name.split('/')
        if len(parts) != 2: return
        owner, name = parts

        # Resolve target if missing
        if not target:
            details = await client.get_repo_details(owner, name)
            if details:
                target = details.get('default_branch', 'main')
                print(f"[SERVER] Resolved default branch for {repo_full_name} to {target}")
            else:
                target = 'main' # Fallback
                print(f"[SERVER] Could not resolve default branch, falling back to {target}")

        result = await client.merge_branch(owner, name, target, branch)

        if result:
            msg = f"Merged {branch} into {target} successfully."
            if delete_source_branch:
                try:
                    del_res = await client.delete_branch(owner, name, branch)
                    if del_res:
                        msg += " Branch deleted."
                    else:
                        msg += " Failed to delete branch."
                except Exception as e:
                    msg += f" Error deleting branch: {str(e)}"

            await sio.emit('status', {'msg': msg})
            # Trigger refresh of branches
            await get_repo_branches(sid, data)
        else:
            await sio.emit('error', {'msg': "Merge failed via API."})


@sio.event
async def run_task(sid, data):
    task_id = data.get('id')
    print(f"[SERVER] Run Task: {task_id}")
    if not (audio_loop and audio_loop.task_manager):
        await sio.emit('error', {'msg': "System not ready"})
        return

    # Find the task
    tasks = audio_loop.task_manager.list_tasks()
    task = next((t for t in tasks if t['id'] == task_id), None)

    if not task:
        await sio.emit('error', {'msg': "Task not found"})
        return

    # Execute Action
    action = task.get('action', {})
    act_type = action.get('type')
    act_value = action.get('value')

    try:
        if act_type == 'notify':
            # Send notification
            msg = f"Task '{task['title']}' triggered notification: {act_value}"
            await sio.emit('status', {'msg': msg})
            if audio_loop.slack_agent and SETTINGS.get("jules_slack_notifications"):
                 asyncio.create_task(audio_loop.slack_agent.send_message(msg))

        elif act_type == 'jules_task':
            # Run Jules Agent
            # Value might be JSON string or dict
            prompt = ""
            source = None

            if isinstance(act_value, dict):
                prompt = act_value.get('prompt')
                source = act_value.get('source')
            else:
                # Legacy or string
                prompt = str(act_value)
                # Try to parse if it looks like JSON
                try:
                    parsed = json.loads(prompt)
                    if isinstance(parsed, dict):
                        prompt = parsed.get('prompt', prompt)
                        source = parsed.get('source')
                except:
                    pass

            await sio.emit('status', {'msg': f"Starting Jules Task: {task['title']}..."})
            result = await audio_loop.handle_jules_request(prompt, source)
            # handle_jules_request returns a string message about starting
            # Note: It launches a background task for the actual session creation
            await sio.emit('status', {'msg': f"Jules Agent: {result}"})

        elif act_type == 'run_script':
            script_path = act_value
            # If relative, resolve to project path
            target_path = Path(audio_loop.project_manager.get_current_project_path())
            if not os.path.isabs(script_path):
                script_path = str(target_path / script_path)

            print(f"[SERVER] ACTION: Run Script - {script_path}")

            if not os.path.exists(script_path):
                await sio.emit('error', {'msg': f"Script not found: {script_path}"})
            else:
                # Determine runner based on extension
                if script_path.endswith('.py'):
                    cmd = ["python", script_path]
                elif script_path.endswith('.sh'):
                    cmd = ["bash", script_path]
                elif script_path.endswith('.js'):
                    cmd = ["node", script_path]
                else:
                    cmd = [script_path]

                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()

                if process.returncode != 0:
                    error_log = stderr.decode().strip() or stdout.decode().strip() or "Unknown Error"
                    await sio.emit('error', {'msg': f"Script failed with code {process.returncode}:\n{error_log}"})
                else:
                    out_text = stdout.decode().strip()
                    msg = f"Script Success: {out_text[:100]}..." if out_text else "Script executed successfully."
                    await sio.emit('status', {'msg': msg})

        # Update last run time
        if act_type == 'run_script':
            updates = {"last_run": time.time()}
            audio_loop.task_manager.update_task(task['id'], updates)


    except Exception as e:
        print(f"Error executing task: {e}")
        await sio.emit('error', {'msg': f"Task Execution Failed: {str(e)}"})

@sio.event
async def dismiss_jules_session(sid, data):
    session_id = data.get('id')
    print(f"[SERVER] Dismiss Jules Session: {session_id}")
    if audio_loop and audio_loop.project_manager:
        success, msg = audio_loop.project_manager.dismiss_jules_session(session_id)
        await sio.emit('status', {'msg': msg})
        # Force dashboard update
        if dashboard_task:
            data = await audio_loop.get_dashboard_data()
            await sio.emit('dashboard_update', data)
    else:
        await sio.emit('error', {'msg': "System not ready"})

@sio.event
async def get_jules_activities(sid, data):
    session_id = data.get('id')
    if audio_loop:
        response = await audio_loop.jules_agent.list_activities(session_id)
        if response and isinstance(response, dict) and "activities" in response:
            await sio.emit('jules_activities', {'id': session_id, 'activities': response["activities"]})
        else:
            await sio.emit('error', {'msg': str(response)})
    else:
        await sio.emit('error', {'msg': "System not ready"})

@sio.event
async def send_jules_message(sid, data):
    session_id = data.get('id')
    message = data.get('message')
    if audio_loop:
        result = await audio_loop.handle_jules_feedback(session_id, message)
        await sio.emit('status', {'msg': result})
        # Re-fetch activities to update UI
        activities = await audio_loop.handle_list_jules_activities(session_id)
        if isinstance(activities, list):
            await sio.emit('jules_activities', {'id': session_id, 'activities': activities})
    else:
        await sio.emit('error', {'msg': "System not ready"})

@sio.event
async def set_focused_session(sid, data):
    session_id = data.get('id')
    if audio_loop:
        asyncio.create_task(audio_loop.handle_focused_session(session_id))

@sio.event
async def clear_focused_session(sid):
    if audio_loop:
        asyncio.create_task(audio_loop.handle_clear_focused_session())

@sio.event
async def list_projects(sid):
    """Returns a list of all available projects."""
    projects = project_manager.list_projects()
    await sio.emit('project_list', projects)

@sio.event
async def get_jules_sources(sid):
    """Fetches available Jules sources and emits them back to the client."""
    print("[SERVER] Fetching Jules sources...")
    if audio_loop:
        response = await audio_loop.jules_agent.list_sources()
        if response and isinstance(response, dict) and "sources" in response:
             await sio.emit('jules_sources', response["sources"])
        elif isinstance(response, list):
             # Fallback if list returned directly (unlikely but safe)
             await sio.emit('jules_sources', response)
        else:
            await sio.emit('error', {'msg': f"Failed to fetch sources: {response}"})
    else:
        await sio.emit('error', {'msg': "System not ready"})

# Deprecated/Mapped for compatibility if frontend still uses specific events
@sio.event
async def get_tool_permissions(sid):
    await sio.emit('tool_permissions', SETTINGS["tool_permissions"])

@sio.event
async def update_tool_permissions(sid, data):
    print(f"Updating permissions (legacy event): {data}")
    SETTINGS["tool_permissions"].update(data)
    save_settings()
    
    if audio_loop:
        audio_loop.update_permissions(SETTINGS["tool_permissions"])
    # Broadcast update to all
    await sio.emit('tool_permissions', SETTINGS["tool_permissions"])

@sio.event
async def save_github_token(sid, data):
    token = data.get('token')
    if token:
        SETTINGS["github_token"] = token
        save_settings()
        await sio.emit('status', {'msg': "GitHub token saved securely."})
    else:
        await sio.emit('error', {'msg': "No token provided."})

@sio.event
async def update_repo_config(sid, data):
    repo_name = data.get("repo")
    config = data.get("config", {})
    if not repo_name:
        return

    pm = audio_loop.project_manager if (audio_loop and audio_loop.project_manager) else project_manager
    if not pm:
        return

    fleet = pm.load_fleet()
    updated = False
    for r in fleet:
        full_name = f"{r.get('owner')}/{r.get('name')}"
        if full_name == repo_name:
            for k, v in config.items():
                r[k] = v
            updated = True
            break

    if updated:
        pm.save_fleet(fleet)
        await get_fleet_status(sid)

@sio.event
async def sync_fleet(sid):
    """Syncs local repositories with Jules Agent sources."""
    print(f"[SERVER] Client {sid} requested fleet sync.")
    if not audio_loop:
        await sio.emit('error', {'msg': "System not ready"})
        return

    # 1. Fetch sources from Jules
    response = await audio_loop.jules_agent.list_sources()
    sources = []
    if response and isinstance(response, dict) and "sources" in response:
        sources = response["sources"]
    elif isinstance(response, list):
        sources = response
    else:
        await sio.emit('error', {'msg': f"Failed to fetch sources: {response}"})
        return

    await sio.emit('status', {'msg': f"Found {len(sources)} sources. Syncing..."})

    # 2. Sync (Clone missing)
    # Use executor to prevent blocking
    results, status = await asyncio.to_thread(project_manager.sync_jules_repos, sources)

    if status == "AUTH_REQUIRED":
        await sio.emit('error', {'code': 'AUTH_REQUIRED', 'msg': "GitHub Authentication Failed. Please provide a token."})
    else:
        # Report results
        summary = ", ".join(results) if results else "All up to date."
        await sio.emit('status', {'msg': f"Sync Complete: {summary}"})
        # Refresh fleet view
        await get_fleet_status(sid)

@sio.event
async def get_swarms(sid):
    """Fetches all active swarms."""
    print(f"[SERVER] Client {sid} requested swarms.")
    # Use global project_manager if audio_loop is not ready
    pm = audio_loop.project_manager if (audio_loop and audio_loop.project_manager) else project_manager
    if pm:
        swarms = pm.get_swarms()
        await sio.emit('swarms_update', swarms)
    else:
        await sio.emit('error', {'msg': "System not ready"})

# --- Fleet Accounts Socket.IO Events ---

@sio.event
async def get_accounts(sid):
    try:
        accounts = get_all_accounts()
        await sio.emit('accounts_update', accounts, to=sid)
    except Exception as e:
        await sio.emit('account_error', {'message': f"Failed to fetch accounts: {str(e)}"}, to=sid)

@sio.on('add_account')
async def add_account_event(sid, data):
    try:
        api_key = data.get('api_key')
        name = data.get('name')
        concurrent = data.get('concurrent_sessions_limit')
        total = data.get('total_sessions_limit')

        if not api_key:
            await sio.emit('account_error', {'message': "API Key is required."}, to=sid)
            return

        account_id = add_account(api_key, name, concurrent, total)
        if account_id is None:
             await sio.emit('account_error', {'message': "API Key already exists."}, to=sid)
        else:
             sync_fleet_agent_pool()
             accounts = get_all_accounts()
             await sio.emit('accounts_update', accounts)
             await sio.emit('fleet_state_update', fleet_manager.get_state())
    except Exception as e:
        await sio.emit('account_error', {'message': f"Failed to add account: {str(e)}"}, to=sid)

@sio.on('update_account')
async def update_account_event(sid, data):
    try:
        account_id = data.get('id')
        api_key = data.get('api_key')
        name = data.get('name')
        concurrent = data.get('concurrent_sessions_limit')
        total = data.get('total_sessions_limit')

        if not account_id or not api_key:
             await sio.emit('account_error', {'message': "Account ID and API Key are required."}, to=sid)
             return

        update_account(account_id, api_key, name, concurrent, total)
        sync_fleet_agent_pool()
        accounts = get_all_accounts()
        await sio.emit('accounts_update', accounts)
        await sio.emit('fleet_state_update', fleet_manager.get_state())
    except Exception as e:
        await sio.emit('account_error', {'message': f"Failed to update account: {str(e)}"}, to=sid)

@sio.on('delete_account')
async def delete_account_event(sid, data):
    try:
        account_id = data.get('id')
        if not account_id:
            await sio.emit('account_error', {'message': "Account ID is required."}, to=sid)
            return

        delete_account(account_id)
        sync_fleet_agent_pool()
        accounts = get_all_accounts()
        await sio.emit('accounts_update', accounts)
        await sio.emit('fleet_state_update', fleet_manager.get_state())
    except Exception as e:
        await sio.emit('account_error', {'message': f"Failed to delete account: {str(e)}"}, to=sid)

# --- Fleet Manager Socket.IO Events ---

fleet_account_active_sessions = {} # api_key -> count

@sio.event
async def get_fleet_state(sid):
    state = fleet_manager.get_state()
    await sio.emit('fleet_state_update', state, to=sid)

async def check_and_start_next_task(repo_name, agent_id=None):
    """Helper to check if there are tasks and idle agents in a repo and start one."""
    if not audio_loop:
        return

    while True:
        task = fleet_manager.get_next_task(repo_name)
        if not task:
            break

        current_agent_id = agent_id
        if current_agent_id is None:
            state = fleet_manager.get_state()
            idle_agent = next((a for a in state["agents"] if a["current_repo"] == repo_name and a["status"] == "idle"), None)
            if not idle_agent:
                break
            current_agent_id = idle_agent["id"]

        # We only use the passed agent_id for the first iteration
        agent_id = None

        fleet_manager.update_agent_session(current_agent_id, None, "working")
        fleet_manager.update_task_status(repo_name, task["id"], "in_progress", current_agent_id)
        await sio.emit('fleet_state_update', fleet_manager.get_state())

        prompt = f"Context: Repo {repo_name}\nTask: {task['prompt']}"
        source = f"github.com/{repo_name}"
        await sio.emit('status', {'msg': f"Agent {current_agent_id} picking up task in {repo_name}..."})

        # We need to capture variables for the closure, so we create a factory function
        def create_spawn_task(current_task, current_agent_id, current_prompt, current_source):
            selected_api_key = None

            async def _on_jules_finished(message):
                # Callback wrapper that looks for completion/failure signals
                # JulesAgent sends generic messages through callback
                # NOTE: We look for exact specific signal strings that JulesAgent emits
                if "Jules has completed the session" in message or "Session Completed." in message:
                    print(f"[SERVER] Jules session completed for task {current_task['id']}")
                    if selected_api_key and selected_api_key in fleet_account_active_sessions:
                        fleet_account_active_sessions[selected_api_key] = max(0, fleet_account_active_sessions[selected_api_key] - 1)
                    fleet_manager.update_task_status(repo_name, current_task["id"], "completed")
                    fleet_manager.update_agent_session(current_agent_id, None, "idle")
                    await sio.emit('fleet_state_update', fleet_manager.get_state())
                    # Check for next task recursively now that an agent is free
                    await check_and_start_next_task(repo_name, current_agent_id)
                elif "Error polling" in message or "failed" in message.lower() and ("Task Execution Failed" in message or "Exception" in message):
                    print(f"[SERVER] Jules session failed for task {current_task['id']}")
                    if selected_api_key and selected_api_key in fleet_account_active_sessions:
                        fleet_account_active_sessions[selected_api_key] = max(0, fleet_account_active_sessions[selected_api_key] - 1)
                    fleet_manager.update_task_status(repo_name, current_task["id"], "failed")
                    fleet_manager.update_agent_session(current_agent_id, None, "idle")
                    await sio.emit('fleet_state_update', fleet_manager.get_state())
                    # Still check next task
                    await check_and_start_next_task(repo_name, current_agent_id)

            async def run_spawn():
                nonlocal selected_api_key
                try:
                    # Pick a fleet account that has available capacity
                    accounts = get_all_accounts()
                    agent_instance = None
                    if accounts:
                        for account in accounts:
                            api_key = account.get("api_key")
                            limit = account.get("concurrent_sessions_limit")
                            current_active = fleet_account_active_sessions.get(api_key, 0)
                            if limit is None or current_active < limit:
                                selected_api_key = api_key
                                fleet_account_active_sessions[selected_api_key] = current_active + 1
                                print(f"[SERVER] Spawning task using Fleet Account: {account.get('name', 'Unnamed')} (Active: {fleet_account_active_sessions[selected_api_key]}/{limit if limit else '∞'})")
                                agent_instance = JulesAgent(api_key=selected_api_key, project_manager=audio_loop.project_manager)
                                break

                    if not agent_instance:
                        # Fallback to default agent if no fleet accounts have capacity or none exist
                        print("[SERVER] Falling back to default environment API key for task.")
                        agent_instance = audio_loop.jules_agent

                    session = await agent_instance.spawn_agent(
                        prompt=current_prompt,
                        source=current_source,
                        callback=_on_jules_finished,
                        role="DEFAULT"
                    )
                    if session:
                        session_id = session.get('name')
                        fleet_manager.update_agent_session(current_agent_id, session_id, "working")
                        await sio.emit('fleet_state_update', fleet_manager.get_state())
                    else:
                        if selected_api_key and selected_api_key in fleet_account_active_sessions:
                            fleet_account_active_sessions[selected_api_key] = max(0, fleet_account_active_sessions[selected_api_key] - 1)
                        fleet_manager.update_task_status(repo_name, current_task["id"], "failed")
                        fleet_manager.update_agent_session(current_agent_id, None, "error")
                        await sio.emit('fleet_state_update', fleet_manager.get_state())
                except Exception as e:
                    if selected_api_key and selected_api_key in fleet_account_active_sessions:
                        fleet_account_active_sessions[selected_api_key] = max(0, fleet_account_active_sessions[selected_api_key] - 1)
                    fleet_manager.update_task_status(repo_name, current_task["id"], "failed")
                    fleet_manager.update_agent_session(current_agent_id, None, "error")
                    await sio.emit('error', {'msg': f"Failed to start task for {current_agent_id}: {e}"})
                    await sio.emit('fleet_state_update', fleet_manager.get_state())

            return run_spawn

        spawn_task = create_spawn_task(task, current_agent_id, prompt, source)
        asyncio.create_task(spawn_task())


@sio.event
async def set_repo_active_state(sid, data):
    repo_name = data.get('repo_name')
    is_active = data.get('is_active')
    if repo_name is not None and is_active is not None:
        fleet_manager.set_repo_active(repo_name, is_active)
        await sio.emit('fleet_state_update', fleet_manager.get_state())

@sio.event
async def assign_agent_to_repo(sid, data):
    agent_id = data.get('agent_id')
    repo_name = data.get('repo_name')
    if fleet_manager.assign_agent(agent_id, repo_name):
        await sio.emit('fleet_state_update', fleet_manager.get_state())
        await check_and_start_next_task(repo_name, agent_id)

@sio.event
async def unassign_agent(sid, data):
    agent_id = data.get('agent_id')
    if fleet_manager.unassign_agent(agent_id):
        await sio.emit('fleet_state_update', fleet_manager.get_state())

@sio.event
async def add_task_to_repo_queue(sid, data):
    repo_name = data.get('repo_name')
    prompt = data.get('prompt')
    depends_on = data.get('depends_on')
    fleet_manager.add_task_to_queue(repo_name, prompt, depends_on)
    await sio.emit('fleet_state_update', fleet_manager.get_state())

    await check_and_start_next_task(repo_name)

@sio.event
async def clear_completed_tasks(sid, data):
    repo_name = data.get('repo_name')
    fleet_manager.clear_completed_tasks(repo_name)
    await sio.emit('fleet_state_update', fleet_manager.get_state())

@sio.event
async def remove_task_from_queue(sid, data):
    repo_name = data.get('repo_name')
    task_id = data.get('task_id')
    fleet_manager.remove_task_from_queue(repo_name, task_id)
    await sio.emit('fleet_state_update', fleet_manager.get_state())

if __name__ == "__main__":
    port = int(os.getenv("SERVER_PORT", 8180))
    print(f"[SERVER] Starting server on port {port}")
    uvicorn.run(
        "server:app_socketio",
        host="127.0.0.1",
        port=port,
        reload=False, # Reload enabled causes spawn of worker which might miss the event loop policy patch
        loop="asyncio",
        reload_excludes=["temp_cad_gen.py", "output.stl", "*.stl"]
    )
