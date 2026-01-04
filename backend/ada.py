import asyncio
import base64
import io
import json
import os
import sys
import traceback
from dotenv import load_dotenv
import cv2
import pyaudio
import PIL.Image
import mss
import argparse
import math
import struct
import time
import random
import httpx
from giphy_client.apis.default_api import DefaultApi
from giphy_client.api_client import ApiClient

from time_utils import set_time_format_tool, get_datetime_tool, format_datetime, get_local_time
from google import genai
from google.genai import types

if sys.version_info < (3, 11, 0):
    import taskgroup, exceptiongroup
    asyncio.TaskGroup = taskgroup.TaskGroup
    asyncio.ExceptionGroup = exceptiongroup.ExceptionGroup

from tools import tools_list

FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

MODEL = "models/gemini-2.5-flash-native-audio-preview-12-2025"
DEFAULT_MODE = "camera"
load_dotenv()
INCLUDE_RAW_LOGS = os.getenv("INCLUDE_RAW_LOGS", "True").lower() == "true"
os.environ["INCLUDE_RAW_LOGS"] = str(INCLUDE_RAW_LOGS)
client = genai.Client(http_options={"api_version": "v1beta"}, api_key=os.getenv("GEMINI_API_KEY"))

# Function definitions
generate_cad = {
    "name": "generate_cad",
    "description": "Generates a 3D CAD model based on a prompt.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "prompt": {"type": "STRING", "description": "The description of the object to generate."}
        },
        "required": ["prompt"]
    },
    "behavior": "NON_BLOCKING"
}

run_web_agent = {
    "name": "run_web_agent",
    "description": "Opens a web browser and performs a task according to the prompt.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "prompt": {"type": "STRING", "description": "The detailed instructions for the web browser agent."}
        },
        "required": ["prompt"]
    },
    "behavior": "NON_BLOCKING"
}

create_project_tool = {
    "name": "create_project",
    "description": "Creates a new project folder to organize files.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING", "description": "The name of the new project."}
        },
        "required": ["name"]
    }
}

modify_timer_tool = {
    "name": "modify_timer",
    "description": "Modifies an existing timer or reminder.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING", "description": "The name of the timer or reminder to modify."},
            "new_duration": {"type": "INTEGER", "description": "The new duration of the timer in seconds."},
            "new_timestamp": {"type": "STRING", "description": "The new time for the reminder in ISO format (e.g., 'YYYY-MM-DDTHH:MM:SS')."}
        },
        "required": ["name"]
    }
}

switch_project_tool = {
    "name": "switch_project",
    "description": "Switches the current active project context.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING", "description": "The name of the project to switch to."}
        },
        "required": ["name"]
    }
}

list_projects_tool = {
    "name": "list_projects",
    "description": "Lists all available projects.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
    }
}

list_smart_devices_tool = {
    "name": "list_smart_devices",
    "description": "Lists all available smart home devices (lights, plugs, etc.) on the network.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
    }
}

control_light_tool = {
    "name": "control_light",
    "description": "Controls a smart light device.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "target": {
                "type": "STRING",
                "description": "The IP address of the device to control. Always prefer the IP address over the alias for reliability."
            },
            "action": {
                "type": "STRING",
                "description": "The action to perform: 'turn_on', 'turn_off', or 'set'."
            },
            "brightness": {
                "type": "INTEGER",
                "description": "Optional brightness level (0-100)."
            },
            "color": {
                "type": "STRING",
                "description": "Optional color name (e.g., 'red', 'cool white') or 'warm'."
            }
        },
        "required": ["target", "action"]
    }
}

discover_printers_tool = {
    "name": "discover_printers",
    "description": "Discovers 3D printers available on the local network.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
    }
}

print_stl_tool = {
    "name": "print_stl",
    "description": "Prints an STL file to a 3D printer. Handles slicing the STL to G-code and uploading to the printer.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "stl_path": {"type": "STRING", "description": "Path to STL file, or 'current' for the most recent CAD model."},
            "printer": {"type": "STRING", "description": "Printer name or IP address."},
            "profile": {"type": "STRING", "description": "Optional slicer profile name."}
        },
        "required": ["stl_path", "printer"]
    }
}

get_print_status_tool = {
    "name": "get_print_status",
    "description": "Gets the current status of a 3D printer including progress, time remaining, and temperatures.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "printer": {"type": "STRING", "description": "Printer name or IP address."}
        },
        "required": ["printer"]
    }
}

iterate_cad_tool = {
    "name": "iterate_cad",
    "description": "Modifies or iterates on the current CAD design based on user feedback. Use this when the user asks to adjust, change, modify, or iterate on the existing 3D model (e.g., 'make it taller', 'add a handle', 'reduce the thickness').",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "prompt": {"type": "STRING", "description": "The changes or modifications to apply to the current design."}
        },
        "required": ["prompt"]
    },
    "behavior": "NON_BLOCKING"
}

set_timer_tool = {
    "name": "set_timer",
    "description": "Sets a timer for a specified duration.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "duration": {"type": "INTEGER", "description": "The duration of the timer in seconds."},
            "name": {"type": "STRING", "description": "The name of the timer."}
        },
        "required": ["duration", "name"]
    }
}

set_reminder_tool = {
    "name": "set_reminder",
    "description": "Sets a reminder for a specific time.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "timestamp": {"type": "STRING", "description": "The time for the reminder in ISO format (e.g., 'YYYY-MM-DDTHH:MM:SS')."},
            "name": {"type": "STRING", "description": "The name of the reminder."}
        },
        "required": ["timestamp", "name"]
    }
}

list_timers_tool = {
    "name": "list_timers",
    "description": "Lists all active timers and reminders.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
    }
}

delete_entry_tool = {
    "name": "delete_entry",
    "description": "Deletes a timer or reminder by name.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING", "description": "The name of the timer or reminder to delete."}
        },
        "required": ["name"]
    }
}

check_for_updates_tool = {
    "name": "check_for_updates",
    "description": "Checks if a new version of the application is available from the GitHub repository.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
    }
}

apply_update_tool = {
    "name": "apply_update",
    "description": "Downloads the latest version of the application from GitHub and restarts the application to apply the changes.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
    }
}

tools = [{'google_search': {}}, {"function_declarations": [
    generate_cad, run_web_agent, create_project_tool, switch_project_tool,
    list_projects_tool, list_smart_devices_tool, control_light_tool,
    discover_printers_tool, print_stl_tool, get_print_status_tool,
    iterate_cad_tool, set_timer_tool, set_reminder_tool, list_timers_tool,
    delete_entry_tool, modify_timer_tool, check_for_updates_tool, apply_update_tool,
    set_time_format_tool, get_datetime_tool,
] + tools_list[0]['function_declarations'][1:]}]

pya = pyaudio.PyAudio()

from cad_agent import CadAgent
from web_agent import WebAgent
from kasa_agent import KasaAgent
from printer_agent import PrinterAgent
from trello_agent import TrelloAgent
from jules_agent import JulesAgent
from timer_agent import TimerAgent
from update_agent import UpdateAgent
from search_agent import SearchAgent
from proactive_agent import ProactiveAgent

class AudioLoop:
    def __init__(self, sio=None, video_mode=DEFAULT_MODE, on_audio_data=None, on_video_frame=None, on_cad_data=None, on_web_data=None, on_transcription=None, on_tool_confirmation=None, on_cad_status=None, on_cad_thought=None, on_project_update=None, on_device_update=None, on_error=None, input_device_index=None, input_device_name=None, output_device_index=None, kasa_agent=None, project_manager=None, on_display_content=None, slack_agent=None):
        self.sio = sio
        self.slack_agent = slack_agent
        self.video_mode = video_mode
        self.on_audio_data = on_audio_data
        self.on_video_frame = on_video_frame
        self.on_cad_data = on_cad_data
        self.on_web_data = on_web_data
        self.on_display_content = on_display_content
        self.on_transcription = on_transcription
        self.on_tool_confirmation = on_tool_confirmation
        self.on_cad_status = on_cad_status
        self.on_cad_thought = on_cad_thought
        self.on_project_update = on_project_update
        self.on_device_update = on_device_update
        self.on_error = on_error
        self.input_device_index = input_device_index
        self.input_device_name = input_device_name
        self.output_device_index = output_device_index

        self.audio_in_queue = None
        self.out_queue = None
        self.paused = False

        self.message_source = None
        self.chat_buffer = {"sender": None, "text": ""} # For aggregating chunks
        
        # Track last transcription text to calculate deltas (Gemini sends cumulative text)
        self._last_input_transcription = ""
        self._last_output_transcription = ""

        self.audio_in_queue = None
        self.out_queue = None
        self.paused = False

        self.session = None
        
        # Create CadAgent with thought callback
        def handle_cad_thought(thought_text):
            if self.on_cad_thought:
                self.on_cad_thought(thought_text)
        
        def handle_cad_status(status_info):
            if self.on_cad_status:
                self.on_cad_status(status_info)
        
        self.cad_agent = CadAgent(on_thought=handle_cad_thought, on_status=handle_cad_status)
        self.web_agent = WebAgent()
        self.kasa_agent = kasa_agent if kasa_agent else KasaAgent()
        self.printer_agent = PrinterAgent()
        self.trello_agent = TrelloAgent()
        self.timer_agent = TimerAgent(sio=self.sio)
        self.giphy_client = DefaultApi(ApiClient())
        
        def handle_update_log(message):
            # Always print to console from the main thread context
            print(f"[ADA DEBUG] {message}", flush=True)

        self.update_agent = UpdateAgent(on_log=handle_update_log)

        # Instantiate JulesAgent for session management and monitoring
        self.jules_agent = JulesAgent()

        # Dictionary to keep track of active polling tasks
        self.jules_polling_tasks = {}

        self.send_text_task = None
        self.stop_event = asyncio.Event()
        self._reconnect_needed = asyncio.Event()
        
        self.permissions = {} # Default Empty (Will treat unset as True)
        self._pending_confirmations = {}

        # Video buffering state
        self._latest_image_payload = None
        # VAD State
        self._is_speaking = False
        self._silence_start_time = None
        
        # Initialize ProjectManager
        if project_manager:
            self.project_manager = project_manager
        else:
            from project_manager import ProjectManager
            # Assuming we are running from backend/ or root?
            # Using abspath of current file to find root
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # If ada.py is in backend/, project root is one up
            project_root = os.path.dirname(current_dir)
            self.project_manager = ProjectManager(project_root)
        
        self.search_agent = SearchAgent(self.trello_agent, self.project_manager)
        self.proactive_agent = ProactiveAgent(session=None, project_manager=self.project_manager)

        # Sync Initial Project State
        if self.on_project_update:
            # We need to defer this slightly or just call it. 
            # Since this is init, loop might not be running, but on_project_update in server.py uses asyncio.create_task which needs a loop.
            # We will handle this by calling it in run() or just print for now.
            pass

    def flush_chat(self):
        """Forces the current chat buffer to be written to log."""
        if self.chat_buffer["sender"] and self.chat_buffer["text"].strip():
            self.project_manager.log_chat(self.chat_buffer["sender"], self.chat_buffer["text"])
            self.chat_buffer = {"sender": None, "text": ""}
        # Reset transcription tracking for new turn
        self._last_input_transcription = ""
        self._last_output_transcription = ""

    def update_permissions(self, new_perms):
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [CONFIG] Updating tool permissions: {new_perms}")
        self.permissions.update(new_perms)

    def set_paused(self, paused):
        self.paused = paused

    def stop(self):
        self.stop_event.set()
        if INCLUDE_RAW_LOGS:
            print("[ADA DEBUG] [SHUTDOWN] Stopping all Jules polling tasks...")
        for session_id, task_info in self.jules_polling_tasks.items():
            if INCLUDE_RAW_LOGS:
                print(f"[ADA DEBUG] [SHUTDOWN] Signaling stop for session: {session_id}")
            task_info["stop_event"].set()

    def reconnect(self):
        """Signals the main loop to reconnect."""
        if INCLUDE_RAW_LOGS:
            print("[ADA DEBUG] [RECONNECT] Reconnect signaled.")
        self._reconnect_needed.set()

    def _cleanup_jules_task(self, session_id, task):
        """Callback to remove a completed Jules polling task."""
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [JULES] Cleaning up polling task for session: {session_id}")
        self.jules_polling_tasks.pop(session_id, None)

    async def _handle_jules_status_change(self, title, new_state):
        """Handles UI and voice notifications for Jules session status changes."""
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [JULES_NOTIFY] Received status change: '{title}' -> {new_state}")

        notification_text = f"Jules task '{title}' has moved to {new_state}."

        # 1. Send UI Notification
        if self.on_display_content:
            self.on_display_content({
                "content_type": "notification",
                "data": {"text": notification_text},
                "duration": 20000  # 20 seconds
            })
            if INCLUDE_RAW_LOGS:
                print(f"[ADA DEBUG] [JULES_NOTIFY] Sent UI notification.")

        # 2. Send Voice Notification
        if self.session:
            try:
                # Use a system notification prefix to frame the message for the model
                await asyncio.wait_for(
                    self.session.send(input=f"System Notification: {notification_text}", end_of_turn=False),
                    timeout=10.0
                )
                if INCLUDE_RAW_LOGS:
                    print(f"[ADA DEBUG] [JULES_NOTIFY] Sent voice notification message to model.")
            except asyncio.TimeoutError:
                if INCLUDE_RAW_LOGS:
                    print(f"[ADA DEBUG] [ERR] [JULES_NOTIFY] Timeout sending voice notification.")
            except Exception as e:
                if INCLUDE_RAW_LOGS:
                    print(f"[ADA DEBUG] [ERR] [JULES_NOTIFY] Failed to send voice notification: {e}")

        # 3. Send Slack Notification
        if self.slack_agent:
            asyncio.create_task(self.slack_agent.send_message(notification_text))
        
    def resolve_tool_confirmation(self, request_id, confirmed):
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [RESOLVE] resolve_tool_confirmation called. ID: {request_id}, Confirmed: {confirmed}")
        if request_id in self._pending_confirmations:
            future = self._pending_confirmations[request_id]
            if not future.done():
                if INCLUDE_RAW_LOGS:
                    print(f"[ADA DEBUG] [RESOLVE] Future found and pending. Setting result to: {confirmed}")
                future.set_result(confirmed)
            else:
                if INCLUDE_RAW_LOGS:
                    print(f"[ADA DEBUG] [WARN] Request {request_id} future already done. Result: {future.result()}")
        else:
            if INCLUDE_RAW_LOGS:
                print(f"[ADA DEBUG] [WARN] Confirmation Request {request_id} not found in pending dict. Keys: {list(self._pending_confirmations.keys())}")

    def clear_audio_queue(self):
        """Clears the queue of pending audio chunks to stop playback immediately."""
        try:
            count = 0
            while not self.audio_in_queue.empty():
                self.audio_in_queue.get_nowait()
                count += 1
            if count > 0:
                if INCLUDE_RAW_LOGS:
                    print(f"[ADA DEBUG] [AUDIO] Cleared {count} chunks from playback queue due to interruption.")
        except Exception as e:
            if INCLUDE_RAW_LOGS:
                print(f"[ADA DEBUG] [ERR] Failed to clear audio queue: {e}")

    async def send_frame(self, frame_data):
        # Update the latest frame payload
        if isinstance(frame_data, bytes):
            b64_data = base64.b64encode(frame_data).decode('utf-8')
        else:
            b64_data = frame_data 

        # Store as the designated "next frame to send"
        self._latest_image_payload = {"mime_type": "image/jpeg", "data": b64_data}
        # No event signal needed - listen_audio pulls it

    async def send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send(input=msg, end_of_turn=False)

    async def listen_audio(self):
        mic_info = pya.get_default_input_device_info()

        # Resolve Input Device by Name if provided
        resolved_input_device_index = None
        
        if self.input_device_name:
            if INCLUDE_RAW_LOGS:
                print(f"[ADA] Attempting to find input device matching: '{self.input_device_name}'")
            count = pya.get_device_count()
            best_match = None
            
            for i in range(count):
                try:
                    info = pya.get_device_info_by_index(i)
                    if info['maxInputChannels'] > 0:
                        name = info.get('name', '')
                        # Simple case-insensitive check
                        if self.input_device_name.lower() in name.lower() or name.lower() in self.input_device_name.lower():
                             if INCLUDE_RAW_LOGS:
                                 print(f"   Candidate {i}: {name}")
                             # Prioritize exact match or very close match if possible, but first match is okay for now
                             resolved_input_device_index = i
                             best_match = name
                             break
                except Exception:
                    continue
            
            if resolved_input_device_index is not None:
                if INCLUDE_RAW_LOGS:
                    print(f"[ADA] Resolved input device '{self.input_device_name}' to index {resolved_input_device_index} ({best_match})")
            else:
                if INCLUDE_RAW_LOGS:
                    print(f"[ADA] Could not find device matching '{self.input_device_name}'. Checking index...")

        # Fallback to index if Name lookup failed or wasn't provided
        if resolved_input_device_index is None and self.input_device_index is not None:
             try:
                 resolved_input_device_index = int(self.input_device_index)
                 if INCLUDE_RAW_LOGS:
                     print(f"[ADA] Requesting Input Device Index: {resolved_input_device_index}")
             except ValueError:
                 if INCLUDE_RAW_LOGS:
                     print(f"[ADA] Invalid device index '{self.input_device_index}', reverting to default.")
                 resolved_input_device_index = None

        if resolved_input_device_index is None:
             if INCLUDE_RAW_LOGS:
                 print("[ADA] Using Default Input Device")

        # Determine actual channels to use
        actual_input_device_index = resolved_input_device_index if resolved_input_device_index is not None else mic_info["index"]
        
        # Try to open with requested CHANNELS, fallback if needed
        self.audio_stream = None
        stream_channels = CHANNELS
        
        try:
            self.audio_stream = await asyncio.to_thread(
                pya.open,
                format=FORMAT,
                channels=CHANNELS,
                rate=SEND_SAMPLE_RATE,
                input=True,
                input_device_index=actual_input_device_index,
                frames_per_buffer=CHUNK_SIZE,
            )
        except OSError:
            if INCLUDE_RAW_LOGS:
                print(f"[ADA] Failed to open stream with {CHANNELS} channels. Trying to detect supported channels...")
            try:
                device_info = pya.get_device_info_by_index(actual_input_device_index)
                max_channels = int(device_info.get('maxInputChannels', 0))
                
                # Try common counts up to max_channels
                for c in [1, 2, 4, 8]:
                    if c == CHANNELS: continue
                    if c > max_channels and max_channels > 0: continue
                    try:
                        self.audio_stream = await asyncio.to_thread(
                            pya.open,
                            format=FORMAT,
                            channels=c,
                            rate=SEND_SAMPLE_RATE,
                            input=True,
                            input_device_index=actual_input_device_index,
                            frames_per_buffer=CHUNK_SIZE,
                        )
                        stream_channels = c
                        if INCLUDE_RAW_LOGS:
                            print(f"[ADA] Successfully opened audio stream with {c} channels.")
                        break
                    except OSError:
                        continue
            except Exception as e:
                if INCLUDE_RAW_LOGS:
                    print(f"[ADA] [ERR] Device info lookup failed: {e}")

        if not self.audio_stream:
            if INCLUDE_RAW_LOGS:
                print(f"[ADA] [ERR] Failed to open audio input stream: Invalid number of channels or device unavailable.")
                print("[ADA] [WARN] Audio features will be disabled. Please check microphone permissions.")
            return

        if __debug__:
            kwargs = {"exception_on_overflow": False}
        else:
            kwargs = {}
        
        # VAD Constants
        VAD_THRESHOLD = 800 # Adj based on mic sensitivity (800 is conservative for 16-bit)
        SILENCE_DURATION = 0.5 # Seconds of silence to consider "done speaking"
        
        while True:
            if self.paused:
                await asyncio.sleep(0.1)
                continue

            try:
                data = await asyncio.to_thread(self.audio_stream.read, CHUNK_SIZE, **kwargs)
                
                # Downmix if needed (Gemini expects Mono)
                if stream_channels > 1:
                    count = len(data) // (2 * stream_channels)
                    if count > 0:
                        shorts = struct.unpack(f"<{count * stream_channels}h", data)
                        # Take the first channel (left)
                        mono_shorts = shorts[::stream_channels]
                        data = struct.pack(f"<{count}h", *mono_shorts)

                # 1. Send Audio
                if self.out_queue:
                    await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})
                
                # 2. VAD Logic for Video
                # rms = audioop.rms(data, 2)
                # Replacement for audioop.rms(data, 2)
                count = len(data) // 2
                if count > 0:
                    shorts = struct.unpack(f"<{count}h", data)
                    sum_squares = sum(s**2 for s in shorts)
                    rms = int(math.sqrt(sum_squares / count))
                else:
                    rms = 0
                
                if rms > VAD_THRESHOLD:
                    # Speech Detected
                    self._silence_start_time = None
                    
                    if not self._is_speaking:
                        # NEW Speech Utterance Started
                        self._is_speaking = True
                        if INCLUDE_RAW_LOGS:
                            print(f"[ADA DEBUG] [VAD] Speech Detected (RMS: {rms}). Sending Video Frame.")
                        
                        # Send ONE frame
                        if self._latest_image_payload and self.out_queue:
                            await self.out_queue.put(self._latest_image_payload)
                        else:
                            if INCLUDE_RAW_LOGS:
                                print(f"[ADA DEBUG] [VAD] No video frame available to send.")
                            
                else:
                    # Silence
                    if self._is_speaking:
                        if self._silence_start_time is None:
                            self._silence_start_time = time.time()
                        
                        elif time.time() - self._silence_start_time > SILENCE_DURATION:
                            # Silence confirmed, reset state
                            if INCLUDE_RAW_LOGS:
                                print(f"[ADA DEBUG] [VAD] Silence detected. Resetting speech state.")
                            self._is_speaking = False
                            self._silence_start_time = None

            except Exception as e:
                if INCLUDE_RAW_LOGS:
                    print(f"Error reading audio: {e}")
                await asyncio.sleep(0.1)

    async def handle_cad_request(self, prompt):
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [CAD] Background Task Started: handle_cad_request('{prompt}')")
        if self.on_cad_status:
            self.on_cad_status("generating")
            
        # Auto-create project if stuck in temp
        if self.project_manager.current_project == "temp":
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            new_project_name = f"Project_{timestamp}"
            if INCLUDE_RAW_LOGS:
                print(f"[ADA DEBUG] [CAD] Auto-creating project: {new_project_name}")
            
            success, msg = self.project_manager.create_project(new_project_name)
            if success:
                self.project_manager.switch_project(new_project_name)
                # Notify User (Optional, or rely on update)
                try:
                    await self.session.send(input=f"System Notification: Automatic Project Creation. Switched to new project '{new_project_name}'.", end_of_turn=False)
                    if self.on_project_update:
                         self.on_project_update(new_project_name)
                except Exception as e:
                    if INCLUDE_RAW_LOGS:
                        print(f"[ADA DEBUG] [ERR] Failed to notify auto-project: {e}")
        
        # Get project cad folder path
        cad_output_dir = str(self.project_manager.get_current_project_path() / "cad")
        
        # Call the secondary agent with project path
        cad_data = await self.cad_agent.generate_prototype(prompt, output_dir=cad_output_dir)
        
        if cad_data:
            if INCLUDE_RAW_LOGS:
                print(f"[ADA DEBUG] [OK] CadAgent returned data successfully.")
                print(f"[ADA DEBUG] [INFO] Data Check: {len(cad_data.get('vertices', []))} vertices, {len(cad_data.get('edges', []))} edges.")
            
            if self.on_cad_data:
                if INCLUDE_RAW_LOGS:
                    print(f"[ADA DEBUG] [SEND] Dispatching data to frontend callback...")
                self.on_cad_data(cad_data)
                if INCLUDE_RAW_LOGS:
                    print(f"[ADA DEBUG] [SENT] Dispatch complete.")
            
            # Save to Project
            if 'file_path' in cad_data:
                self.project_manager.save_cad_artifact(cad_data['file_path'], prompt)
            else:
                 # Fallback (legacy support)
                 self.project_manager.save_cad_artifact("output.stl", prompt)

            # Notify the model that the task is done - this triggers speech about completion
            completion_msg = "System Notification: CAD generation is complete! The 3D model is now displayed for the user. Let them know it's ready."
            try:
                await self.session.send(input=completion_msg, end_of_turn=True)
                if INCLUDE_RAW_LOGS:
                    print(f"[ADA DEBUG] [NOTE] Sent completion notification to model.")
            except Exception as e:
                 if INCLUDE_RAW_LOGS:
                    print(f"[ADA DEBUG] [ERR] Failed to send completion notification: {e}")

        else:
            if INCLUDE_RAW_LOGS:
                print(f"[ADA DEBUG] [ERR] CadAgent returned None.")
            # Optionally notify failure
            try:
                await self.session.send(input="System Notification: CAD generation failed.", end_of_turn=True)
            except Exception:
                pass



    async def handle_write_file(self, path, content):
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [FS] Writing file: '{path}'")
        
        # Auto-create project if stuck in temp
        if self.project_manager.current_project == "temp":
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            new_project_name = f"Project_{timestamp}"
            if INCLUDE_RAW_LOGS:
                print(f"[ADA DEBUG] [FS] Auto-creating project: {new_project_name}")
            
            success, msg = self.project_manager.create_project(new_project_name)
            if success:
                self.project_manager.switch_project(new_project_name)
                # Notify User
                try:
                    await self.session.send(input=f"System Notification: Automatic Project Creation. Switched to new project '{new_project_name}'.", end_of_turn=False)
                    if self.on_project_update:
                         self.on_project_update(new_project_name)
                except Exception as e:
                    if INCLUDE_RAW_LOGS:
                        print(f"[ADA DEBUG] [ERR] Failed to notify auto-project: {e}")
        
        # Force path to be relative to current project
        # If absolute path is provided, we try to strip it or just ignore it and use basename
        filename = os.path.basename(path)
        
        # If path contained subdirectories (e.g. "backend/server.py"), preserving that structure might be desired IF it's within the project.
        # But for safety, and per user request to "always create the file in the project", 
        # we will root it in the current project path.
        
        current_project_path = self.project_manager.get_current_project_path()
        final_path = current_project_path / filename # Simple flat structure for now, or allow relative?
        
        # If the user specifically wanted a subfolder, they might have provided "sub/file.txt".
        # Let's support relative paths if they don't start with /
        if not os.path.isabs(path):
             final_path = current_project_path / path
        
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [FS] Resolved path: '{final_path}'")

        try:
            # Ensure parent exists
            os.makedirs(os.path.dirname(final_path), exist_ok=True)
            with open(final_path, 'w', encoding='utf-8') as f:
                f.write(content)
            result = f"File '{final_path}' written successfully to project '{self.project_manager.current_project}'."
        except Exception as e:
            result = f"Failed to write file '{path}': {str(e)}"

        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [FS] Result: {result}")
        try:
             await self.session.send(input=f"System Notification: {result}", end_of_turn=True)
        except Exception as e:
             if INCLUDE_RAW_LOGS:
                print(f"[ADA DEBUG] [ERR] Failed to send fs result: {e}")

    async def handle_read_directory(self, path):
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [FS] Reading directory: '{path}'")
        
        # Resolve path relative to current project
        current_project_path = self.project_manager.get_current_project_path()
        final_path = current_project_path / path if not os.path.isabs(path) else path
        
        try:
            if not os.path.exists(final_path):
                result = f"Directory '{final_path}' does not exist."
            else:
                items = os.listdir(final_path)
                result = f"Contents of '{final_path}': {', '.join(items)}"
        except Exception as e:
            result = f"Failed to read directory '{path}': {str(e)}"

        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [FS] Result: {result}")
        try:
             await self.session.send(input=f"System Notification: {result}", end_of_turn=True)
        except Exception as e:
             if INCLUDE_RAW_LOGS:
                print(f"[ADA DEBUG] [ERR] Failed to send fs result: {e}")

    async def handle_read_file(self, path):
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [FS] Reading file: '{path}'")
        
        # Resolve path relative to current project
        current_project_path = self.project_manager.get_current_project_path()
        final_path = current_project_path / path if not os.path.isabs(path) else path

        try:
            if not os.path.exists(final_path):
                result = f"File '{final_path}' does not exist."
            else:
                with open(final_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                result = f"Content of '{final_path}':\n{content}"
        except Exception as e:
            result = f"Failed to read file '{path}': {str(e)}"

        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [FS] Result: {result}")
        try:
             await self.session.send(input=f"System Notification: {result}", end_of_turn=True)
        except Exception as e:
             if INCLUDE_RAW_LOGS:
                print(f"[ADA DEBUG] [ERR] Failed to send fs result: {e}")

    async def handle_get_weather(self, location, forecast_days=7, past_days=0, hourly=None, daily=None):
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [WEATHER] Getting weather for: '{location}' with params: forecast_days={forecast_days}, past_days={past_days}, hourly={hourly}, daily={daily}")

        try:
            # Step 1: Geocoding
            parts = [p.strip() for p in location.split(',')]
            city = parts[0]
            state = parts[1] if len(parts) > 1 else None
            country = parts[2] if len(parts) > 2 else None

            async with httpx.AsyncClient() as client:
                params = {"name": city, "count": 15, "language": "en", "format": "json"}
                url = "https://geocoding-api.open-meteo.com/v1/search"

                if INCLUDE_RAW_LOGS:
                    print(f"[ADA DEBUG] [WEATHER] Requesting Geocoding URL: {url} with params: {params}")

                geo_response = await client.get(url, params=params)

                if INCLUDE_RAW_LOGS:
                    print(f"[ADA DEBUG] [WEATHER] Geocoding Response Status: {geo_response.status_code}")
                    print(f"[ADA DEBUG] [WEATHER] Geocoding Response Text: {geo_response.text}")

                geo_response.raise_for_status()
                geo_data = geo_response.json()
                results = geo_data.get("results")

                if not results:
                    if INCLUDE_RAW_LOGS:
                        print(f"[ADA DEBUG] [WEATHER] Geocoding returned no results. Raw response: {geo_response.text}")
                    return f"Could not find location: {location}"

                # Step 2: Filter results if state/country was provided
                if state or country:
                    filtered_results = []
                    for r in results:
                        match = True
                        # State/Admin1 must match if provided
                        if state and not (r.get('admin1') and state.lower() in r.get('admin1').lower()):
                            match = False
                        # Country must match if provided
                        if country and not (r.get('country') and country.lower() in r.get('country').lower()):
                            match = False

                        if match:
                            filtered_results.append(r)

                    # If we found any matches, use the filtered list. Otherwise, stick with the original broad list.
                    if filtered_results:
                        results = filtered_results

                # Step 3: Handle ambiguity
                if len(results) > 1:
                    locations = [
                        f"{i+1}. {r.get('name', 'N/A')}, {r.get('admin1', 'N/A')}, {r.get('country', 'N/A')}"
                        for i, r in enumerate(results)
                    ]
                    return f"Multiple locations found. Please be more specific:\n" + "\n".join(locations)

                lat = results[0]["latitude"]
                lon = results[0]["longitude"]

            # Step 2: Weather Forecast
            params = {
                "latitude": lat,
                "longitude": lon,
                "timezone": "auto"
            }
            if forecast_days is not None:
                params["forecast_days"] = forecast_days
            if past_days is not None:
                params["past_days"] = past_days
            if hourly:
                params["hourly"] = ",".join(hourly)
            if daily:
                params["daily"] = ",".join(daily)

            # Add default daily if nothing is specified
            if not hourly and not daily:
                params["daily"] = "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum"


            async with httpx.AsyncClient() as client:
                forecast_response = await client.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params=params
                )
                forecast_response.raise_for_status()
                weather_data = forecast_response.json()

                # The widget expects a simple daily forecast structure.
                # If daily data is present, format it for the widget.
                # Otherwise, return the full JSON for the model to interpret.
                daily_data = weather_data.get('daily', {})
                if 'time' in daily_data and daily_data['time']:
                    forecast = []
                    num_days = len(daily_data['time'])
                    weather_codes = daily_data.get('weather_code', [None] * num_days)
                    temp_maxes = daily_data.get('temperature_2m_max', [None] * num_days)
                    temp_mins = daily_data.get('temperature_2m_min', [None] * num_days)
                    precipitations = daily_data.get('precipitation_sum', [None] * num_days)

                    for i in range(num_days):
                        forecast.append({
                            "date": daily_data['time'][i],
                            "weather_code": weather_codes[i],
                            "temp_max": temp_maxes[i],
                            "temp_min": temp_mins[i],
                            "precipitation": precipitations[i]
                        })
                    return forecast
                else:
                    return weather_data

        except httpx.HTTPStatusError as e:
            if INCLUDE_RAW_LOGS:
                print(f"[ADA DEBUG] [ERR] HTTP error in weather tool: {e}")
            return f"Error processing weather request: {e.response.status_code}"
        except Exception as e:
            if INCLUDE_RAW_LOGS:
                print(f"[ADA DEBUG] [ERR] Failed to get weather: {e}")
                traceback.print_exc()
            return "Failed to get weather data."

    async def handle_search_gifs(self, query):
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [GIF] Searching for GIFs with query: '{query}'")
        try:
            # Use Giphy's search endpoint
            response = self.giphy_client.gifs_search_get(os.getenv("GIPHY_API_KEY"), query, limit=5)
            if response.data:
                # Get the URL of the first GIF
                image_url = response.data[0].images.original.url
                return f"Found image: {image_url}"
            else:
                return "No images found."
        except Exception as e:
            if INCLUDE_RAW_LOGS:
                print(f"[ADA DEBUG] [ERR] Failed to search for images: {e}")
            return "Failed to search for images."

    async def handle_display_content(self, content_type, url=None, widget_type=None, data=None, duration=None):
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [DISPLAY] Displaying content: {content_type}")

        # If data is a string, assume it's JSON and parse it.
        # This handles the case where the model passes the result of one tool (get_weather)
        # as a stringified argument to another tool (display_content).
        parsed_data = data
        if isinstance(data, str):
            try:
                parsed_data = json.loads(data)
            except json.JSONDecodeError:
                if INCLUDE_RAW_LOGS:
                    print(f"[ADA DEBUG] [WARN] Could not decode JSON string for display content: {data}")
                pass # Leave it as a string if it's not valid JSON

        # More robust check for wrapped data, especially for weather widgets.
        # Handles cases where the model wraps the list in a dict like {'forecast': [...]} or {'daily': [...]}.
        if widget_type == 'weather' and isinstance(parsed_data, dict) and len(parsed_data) == 1:
            key = list(parsed_data.keys())[0]
            if isinstance(parsed_data[key], list):
                if INCLUDE_RAW_LOGS:
                    print(f"[ADA DEBUG] [WEATHER WIDGET] Detected single-key dictionary wrapping the data with key '{key}'. Extracting the list.")
                parsed_data = parsed_data[key]

        if self.on_display_content:
            self.on_display_content({
                "content_type": content_type,
                "url": url,
                "widget_type": widget_type,
                "data": parsed_data,
                "duration": duration
            })
            return "Content displayed."
        else:
            return "No display content handler registered."

    async def handle_restart_application(self):
        if INCLUDE_RAW_LOGS:
            print("[ADA DEBUG] [RESTART] Emitting restart signal to frontend...")
        if self.sio:
            await self.sio.emit('initiate_restart')
            return "Restart signal sent to frontend."
        else:
            return "Cannot send restart signal: not connected to server."

    async def handle_web_agent_request(self, prompt):
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [WEB] Background Task Started: handle_web_agent_request('{prompt}')")
        
        async def update_frontend(image_b64, log_text):
            if self.on_web_data:
                 self.on_web_data({"image": image_b64, "log": log_text})
                 
        # Run the web agent and wait for it to return
        result = await self.web_agent.run_task(prompt, update_callback=update_frontend)
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [WEB] Web Agent Task Returned: {result}")
        
        # Send the final result back to the main model
        try:
             await self.session.send(input=f"System Notification: Web Agent has finished.\nResult: {result}", end_of_turn=True)
        except Exception as e:
             if INCLUDE_RAW_LOGS:
                print(f"[ADA DEBUG] [ERR] Failed to send web agent result to model: {e}")

    async def handle_jules_request(self, prompt, source=None):
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [JULES] Jules Agent Task: '{prompt}'")

        project_config = self.project_manager.get_project_config()
        api_key = project_config.get("jules_api_key")
        jules_agent = JulesAgent(session=self.session, api_key=api_key)

        if not source:
            if INCLUDE_RAW_LOGS:
                print("[ADA DEBUG] [JULES] No source provided, fetching available sources.")
            
            async def fetch_sources_and_notify():
                sources_response = await jules_agent.list_sources()
                if sources_response and "sources" in sources_response:
                    sources = [s["name"] for s in sources_response["sources"]]
                    sources_str = "\n".join(sources)
                    msg = f"System Notification: Available Jules sources:\n{sources_str}\n\nPlease ask the user to select one."
                else:
                    msg = "System Notification: Failed to fetch Jules sources."
                
                try:
                    await self.session.send(input=msg, end_of_turn=True)
                except Exception as e:
                    if INCLUDE_RAW_LOGS:
                        print(f"[ADA DEBUG] [ERR] Failed to send jules sources notification: {e}")

            asyncio.create_task(fetch_sources_and_notify())
            return "Fetching available Jules sources. I will notify you shortly."

        async def run_jules_task():
            session = await jules_agent.create_session(prompt, source)
            if session:
                session_id = session['name']
                if INCLUDE_RAW_LOGS:
                    print(f"[ADA DEBUG] [JULES] Session created: {session_id}")

                stop_event = asyncio.Event()
                polling_task = asyncio.create_task(
                    jules_agent.poll_for_updates(session_id, stop_event)
                )
                self.jules_polling_tasks[session_id] = {"task": polling_task, "stop_event": stop_event}
                title = session.get('title', f"Jules: {prompt[:50]}")
                self.project_manager.save_jules_session(session_id, title)
                polling_task.add_done_callback(
                    lambda task: self._cleanup_jules_task(session_id, task)
                )

                try:
                    title = session.get('title', session_id)
                    await self.session.send(input=f"System Notification: Jules session created: '{title}'", end_of_turn=True)
                except Exception as e:
                    if INCLUDE_RAW_LOGS:
                        print(f"[ADA DEBUG] [ERR] Failed to send jules session creation notification: {e}")
            else:
                if INCLUDE_RAW_LOGS:
                    print("[ADA DEBUG] [JULES] Failed to create session.")
                try:
                    await self.session.send(input="System Notification: Failed to start Jules task.", end_of_turn=True)
                except Exception as e:
                    if INCLUDE_RAW_LOGS:
                        print(f"[ADA DEBUG] [ERR] Failed to send jules failure notification: {e}")

        asyncio.create_task(run_jules_task())
        return "Jules task starting. I will notify you once the session is created."

    async def handle_jules_feedback(self, session_id, feedback):
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [JULES] Sending feedback to session: {session_id}")
        
        project_config = self.project_manager.get_project_config()
        api_key = project_config.get("jules_api_key")
        jules_agent = JulesAgent(session=self.session, api_key=api_key)

        if session_id not in self.jules_polling_tasks:
            if INCLUDE_RAW_LOGS:
                print(f"[ADA DEBUG] [JULES] Starting polling for existing session: {session_id}")
            stop_event = asyncio.Event()
            polling_task = asyncio.create_task(
                jules_agent.poll_for_updates(session_id, stop_event)
            )
            self.jules_polling_tasks[session_id] = {"task": polling_task, "stop_event": stop_event}
            polling_task.add_done_callback(
                lambda task: self._cleanup_jules_task(session_id, task)
            )

        response = await jules_agent.send_message(session_id, feedback)
        if response:
            return "Feedback sent successfully."
        else:
            return "Failed to send feedback."

    async def handle_list_jules_sources(self):
        if INCLUDE_RAW_LOGS:
            print("[ADA DEBUG] [JULES] Listing all sources")
        project_config = self.project_manager.get_project_config()
        api_key = project_config.get("jules_api_key")
        jules_agent = JulesAgent(api_key=api_key)
        response = await jules_agent.list_sources()
        if response and "sources" in response:
            return response["sources"]
        else:
            return "Failed to list Jules sources."

    async def handle_list_jules_sessions(self):
        if INCLUDE_RAW_LOGS:
            print("[ADA DEBUG] [JULES] Listing saved sessions from local memory")
        sessions = self.project_manager.get_jules_sessions()
        if sessions:
            return sessions
        else:
            return "No Jules sessions found in local memory for this project."

    async def handle_list_jules_activities(self, session_id):
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [JULES] Listing activities for session: {session_id}")
        project_config = self.project_manager.get_project_config()
        api_key = project_config.get("jules_api_key")
        jules_agent = JulesAgent(api_key=api_key)
        response = await jules_agent.list_activities(session_id)
        if response and "activities" in response:
            return response["activities"]
        else:
            return "Failed to list Jules activities."

    def _get_live_connect_config(self):
        project_config = self.project_manager.get_project_config()

        # Hardcoded mandatory instructions for tool usage
        tool_prompt = """
**Primary Directive: Use Tools for Visuals**
Your primary mode of communication is visual. When the user asks for any information that can be displayed, you **must** use the available tools to show it first. This includes weather, images, etc. Speaking the information is secondary to displaying it.

**Weather Request Workflow (MANDATORY):**
This is a strict, multi-step tool use process. You must follow it exactly.
1.  When the user asks about the weather, your first and only goal is to get the data for the visual widget.
2.  Call the `get_weather` tool.
3.  If `get_weather` returns a numbered list of locations, you **must** ask the user to clarify by selecting a number.
4.  If `get_weather` returns weather data, your next action **must** be to call `display_content` to show the widget.
5.  Only after the `display_content` tool call is complete may you speak a summary of the weather.

**Example 1: Ambiguous Location**
User: "What's the weather in Paris?"
1.  **You call:** `get_weather(location='Paris')`.
2.  **You receive:** "1. Paris, France; 2. Paris, Texas".
3.  **You respond:** "I found a few places named Paris. Which one did you mean? 1. Paris, France or 2. Paris, Texas?"

**Example 2: Unambiguous Location**
User: "What's the weather in London?"
1.  **You call:** `get_weather(location='London')`.
2.  **You receive:** (forecast data object)
3.  **You call:** `display_content(content_type='widget', widget_type='weather', data=<forecast_data>)`.
4.  **You respond:** "I've pulled up the weather for London for you."
"""

        # Load personality prompt from project config, with a default
        personality_prompt = project_config.get("system_prompt", "Your name is James and you speak with a british accent at all times.. You have a witty and professional personality, like a cheeky butler. Sarcasm is welcome. Your creator is Chad, and you address him as 'Sir'. When answering, respond using complete and concise sentences to keep a quick pacing and keep the conversation flowing. You are a professional assistant.")

        # Combine prompts
        system_prompt = f"{personality_prompt}\\n{tool_prompt}"

        voice_name = project_config.get("voice_name", "Sadaltager")

        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [CONFIG] Using Project: '{self.project_manager.current_project}'")
            print(f"[ADA DEBUG] [CONFIG] Using System Prompt: '{system_prompt[:80]}...'")
            print(f"[ADA DEBUG] [CONFIG] Using Voice: '{voice_name}'")

        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            input_audio_transcription={},
            system_instruction=system_prompt,
            tools=tools,
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            )
        )

    async def receive_audio(self):
        "Background task to reads from the websocket and write pcm chunks to the output queue"
        service_info = f"Service: Gemini Multimodal Live API, Endpoint: {MODEL}"
        try:
            if INCLUDE_RAW_LOGS:
                print(f"[ADA DEBUG] [RECEIVE] Starting receive loop. {service_info}")
            while True:
                try:
                    turn = self.session.receive()
                except Exception as e:
                    if INCLUDE_RAW_LOGS:
                        print(f"[ADA DEBUG] [ERR] Session receive error ({service_info}): {e}")
                    raise e

                full_turn_text_response = ""
                async for response in turn:
                    # Access parts directly to avoid 'non-data parts' / 'non-text parts' warnings 
                    # from the SDK's lazy properties (.text, .data, .thought)
                    if response.server_content and response.server_content.model_turn:
                        parts = response.server_content.model_turn.parts
                        if parts:
                            for part in parts:
                                if hasattr(part, 'thought') and part.thought:
                                    thought_text = part.thought
                                    if INCLUDE_RAW_LOGS:
                                        print(f"[ADA DEBUG] [THOUGHT] {thought_text}")
                                    if self.on_cad_thought:
                                        self.on_cad_thought(thought_text)
                                
                                if hasattr(part, 'text') and part.text:
                                    text_content = part.text
                                    if INCLUDE_RAW_LOGS:
                                        print(f"[ADA DEBUG] [TEXT] {text_content}")
                                    if self.on_transcription:
                                        self.on_transcription({"sender": "ADA", "text": text_content})
                                    
                                    # If the message is from Slack, accumulate the response
                                    if self.message_source == 'slack':
                                        full_turn_text_response += text_content + " "

                                    # Update chat buffer for logging
                                    if self.chat_buffer["sender"] != "ADA":
                                        if self.chat_buffer["sender"] and self.chat_buffer["text"].strip():
                                            self.project_manager.log_chat(self.chat_buffer["sender"], self.chat_buffer["text"])
                                        self.chat_buffer = {"sender": "ADA", "text": text_content}
                                    else:
                                        self.chat_buffer["text"] += text_content

                                if hasattr(part, 'inline_data') and part.inline_data:
                                    self.audio_in_queue.put_nowait(part.inline_data.data)

                                if hasattr(part, 'call') and part.call:
                                    if INCLUDE_RAW_LOGS:
                                        print(f"[ADA DEBUG] [TOOL] Tool call in Part: {part.call.name}, Args: {part.call.args}", flush=True)

                    # 1. Handle Audio Data (Fallback if not handled in parts loop, though parts loop is preferred)
                    # We only use this if we didn't find inline_data in the parts loop to avoid duplicates
                    # But actually, response.data is just a shortcut. 
                    # To avoid the warning completely, we should NOT access response.data if we already processed parts.
                    
                    # 2. Handle Transcription (User & Model)
                    if response.server_content:
                        if response.server_content.input_transcription:
                            transcript = response.server_content.input_transcription.text
                            if transcript:
                                # Skip if this is an exact duplicate event
                                if transcript != self._last_input_transcription:
                                    # Calculate delta (Gemini may send cumulative or chunk-based text)
                                    delta = transcript
                                    if transcript.startswith(self._last_input_transcription):
                                        delta = transcript[len(self._last_input_transcription):]
                                    self._last_input_transcription = transcript
                                    
                                    # Only send if there's new text
                                    if delta:
                                        # User is speaking, so interrupt model playback!
                                        self.clear_audio_queue()

                                        # Send to frontend (Streaming)
                                        if self.on_transcription:
                                             self.on_transcription({"sender": "User", "text": delta})
                                        
                                        # Buffer for Logging
                                        if self.chat_buffer["sender"] != "User":
                                            # Flush previous if exists
                                            if self.chat_buffer["sender"] and self.chat_buffer["text"].strip():
                                                self.project_manager.log_chat(self.chat_buffer["sender"], self.chat_buffer["text"])
                                            # Start new
                                            self.chat_buffer = {"sender": "User", "text": delta}
                                        else:
                                            # Append
                                            self.chat_buffer["text"] += delta
                        
                        if response.server_content.output_transcription:
                            transcript = response.server_content.output_transcription.text
                            if transcript:
                                # Skip if this is an exact duplicate event
                                if transcript != self._last_output_transcription:
                                    # Calculate delta (Gemini may send cumulative or chunk-based text)
                                    delta = transcript
                                    if transcript.startswith(self._last_output_transcription):
                                        delta = transcript[len(self._last_output_transcription):]
                                    self._last_output_transcription = transcript
                                    
                                    # Only send if there's new text
                                    if delta:
                                        # Send to frontend (Streaming)
                                        if self.on_transcription:
                                             self.on_transcription({"sender": "ADA", "text": delta})
                                        
                                        # Buffer for Logging
                                        if self.chat_buffer["sender"] != "ADA":
                                            # Flush previous
                                            if self.chat_buffer["sender"] and self.chat_buffer["text"].strip():
                                                self.project_manager.log_chat(self.chat_buffer["sender"], self.chat_buffer["text"])
                                            # Start new
                                            self.chat_buffer = {"sender": "ADA", "text": delta}
                                        else:
                                            # Append
                                            self.chat_buffer["text"] += delta
                        
                        # Flush buffer on turn completion if needed, 
                        # but usually better to wait for sender switch or explicit end.
                        # We can also check turn_complete signal if available in response.server_content.model_turn etc

                    # 3. Handle Tool Calls
                    if response.tool_call:
                        # print("The tool was called")
                        function_responses = []
                        for fc in response.tool_call.function_calls:
                            if INCLUDE_RAW_LOGS:
                                print(f"[ADA DEBUG] [TOOL] Tool call: {fc.name}, Args: {fc.args}, Endpoint: {MODEL}", flush=True)
                            else:
                                # Basic log as requested: tool, endpoint, status
                                print(f"[ADA DEBUG] [TOOL] Tool: {fc.name}, Endpoint: {MODEL}, Status: 200", flush=True)

                            # Unified confirmation logic
                            destructive_keywords = ['delete', 'remove', 'wipe', 'destroy']
                            confirmation_required = any(keyword in fc.name.lower() for keyword in destructive_keywords)

                            confirmed = True
                            if confirmation_required:
                                if self.on_tool_confirmation:
                                    import uuid
                                    request_id = str(uuid.uuid4())
                                    if INCLUDE_RAW_LOGS:
                                        print(f"[ADA DEBUG] [STOP] Requesting confirmation for '{fc.name}' (ID: {request_id})")

                                    future = asyncio.Future()
                                    self._pending_confirmations[request_id] = future

                                    self.on_tool_confirmation({
                                        "id": request_id,
                                        "tool": fc.name,
                                        "args": fc.args
                                    })

                                    try:
                                        confirmed = await future
                                    finally:
                                        self._pending_confirmations.pop(request_id, None)

                                    if INCLUDE_RAW_LOGS:
                                        print(f"[ADA DEBUG] [CONFIRM] Request {request_id} resolved. Confirmed: {confirmed}")
                                else:
                                    if INCLUDE_RAW_LOGS:
                                        print(f"[ADA DEBUG] [WARN] Confirmation required for '{fc.name}' but no confirmation handler is registered. Denying.")
                                    confirmed = False

                            if not confirmed:
                                if INCLUDE_RAW_LOGS:
                                    print(f"[ADA DEBUG] [DENY] Tool call '{fc.name}' denied by user.")
                                function_response = types.FunctionResponse(
                                    id=fc.id,
                                    name=fc.name,
                                    response={
                                        "result": "User denied the request to use this tool.",
                                    }
                                )
                                function_responses.append(function_response)
                                continue

                            # If confirmed, proceed with execution
                            if fc.name.startswith("trello_"):
                                tool_name = fc.name.replace("trello_", "")
                                trello_func = getattr(self.trello_agent, tool_name)
                                result = await trello_func(**fc.args)
                                function_response = types.FunctionResponse(
                                    id=fc.id,
                                    name=fc.name,
                                    response={"result": result}
                                )
                                function_responses.append(function_response)
                            elif fc.name in ["generate_cad", "generate_cad_prototype", "run_web_agent", "run_jules_agent", "send_jules_feedback", "list_jules_sources", "list_jules_activities", "write_file", "read_directory", "read_file", "create_project", "switch_project", "list_projects", "list_smart_devices", "control_light", "discover_printers", "print_stl", "get_print_status", "iterate_cad", "set_timer", "set_reminder", "list_timers", "delete_entry", "modify_timer", "check_for_updates", "apply_update", "search_gifs", "display_content", "get_weather", "set_time_format", "get_datetime", "restart_application", "search", "proactive_suggestion", "send_slack_message"]:
                                prompt = fc.args.get("prompt", "") # Prompt is not present for all tools

                                if fc.name == "send_slack_message":
                                    message = fc.args["message"]
                                    if self.slack_agent:
                                        asyncio.create_task(self.slack_agent.send_message(message))
                                        result = "Message sent to Slack."
                                    else:
                                        result = "Slack agent not available."
                                    function_response = types.FunctionResponse(
                                        id=fc.id,
                                        name=fc.name,
                                        response={"result": result},
                                    )
                                    function_responses.append(function_response)
                                elif fc.name == "proactive_suggestion":
                                    suggestion = fc.args["suggestion"]
                                    if self.on_display_content:
                                        self.on_display_content({
                                            "content_type": "suggestion",
                                            "suggestion": suggestion,
                                        })
                                    function_response = types.FunctionResponse(
                                        id=fc.id,
                                        name=fc.name,
                                        response={"result": "Suggestion displayed."},
                                    )
                                    function_responses.append(function_response)
                                elif fc.name == "search":
                                    query = fc.args["query"]
                                    result = await self.search_agent.search(query)
                                    function_response = types.FunctionResponse(
                                        id=fc.id,
                                        name=fc.name,
                                        response={"result": result},
                                    )
                                    function_responses.append(function_response)
                                elif fc.name == "restart_application":
                                    result = await self.handle_restart_application()
                                    function_response = types.FunctionResponse(
                                        id=fc.id,
                                        name=fc.name,
                                        response={"result": result},
                                    )
                                    function_responses.append(function_response)
                                elif fc.name == "set_time_format":
                                    time_format = fc.args["format"]
                                    success, msg = self.project_manager.set_time_format(time_format)
                                    function_response = types.FunctionResponse(
                                        id=fc.id,
                                        name=fc.name,
                                        response={"result": msg}
                                    )
                                    function_responses.append(function_response)
                                elif fc.name == "get_datetime":
                                    time_format = self.project_manager.get_project_config().get("time_format", "12h")
                                    current_time = get_local_time()
                                    formatted_time = format_datetime(current_time, time_format)
                                    function_response = types.FunctionResponse(
                                        id=fc.id,
                                        name=fc.name,
                                        response={"result": f"The current date and time is {formatted_time}."}
                                    )
                                    function_responses.append(function_response)
                                elif fc.name == "get_weather":
                                    location = fc.args["location"]
                                    result = await self.handle_get_weather(location)
                                    function_response = types.FunctionResponse(
                                        id=fc.id,
                                        name=fc.name,
                                        response={"result": result},
                                    )
                                    function_responses.append(function_response)
                                elif fc.name == "search_gifs":
                                    query = fc.args["query"]
                                    result = await self.handle_search_gifs(query)
                                    function_response = types.FunctionResponse(
                                        id=fc.id,
                                        name=fc.name,
                                        response={"result": result},
                                    )
                                    function_responses.append(function_response)
                                elif fc.name == "display_content":
                                    content_type = fc.args["content_type"]
                                    url = fc.args.get("url")
                                    widget_type = fc.args.get("widget_type")
                                    data = fc.args.get("data")
                                    duration = fc.args.get("duration")
                                    result = await self.handle_display_content(content_type, url, widget_type, data, duration)
                                    function_response = types.FunctionResponse(
                                        id=fc.id,
                                        name=fc.name,
                                        response={"result": result},
                                    )
                                    function_responses.append(function_response)
                                elif fc.name == "generate_cad" or fc.name == "generate_cad_prototype":
                                    if INCLUDE_RAW_LOGS:
                                        print(f"\n[ADA DEBUG] --------------------------------------------------")
                                        print(f"[ADA DEBUG] [TOOL] Tool Call Detected: 'generate_cad'")
                                        print(f"[ADA DEBUG] [IN] Arguments: prompt='{prompt}'")

                                    asyncio.create_task(self.handle_cad_request(prompt))
                                    # No function response needed - model already acknowledged when user asked

                                elif fc.name == "run_web_agent":
                                    if INCLUDE_RAW_LOGS:
                                        print(f"[ADA DEBUG] [TOOL] Tool Call: 'run_web_agent' with prompt='{prompt}'")
                                    asyncio.create_task(self.handle_web_agent_request(prompt))

                                    result_text = "Web Navigation started. Do not reply to this message."
                                    function_response = types.FunctionResponse(
                                        id=fc.id,
                                        name=fc.name,
                                        response={
                                            "result": result_text,
                                        }
                                    )
                                    if INCLUDE_RAW_LOGS:
                                        print(f"[ADA DEBUG] [RESPONSE] Sending function response: {function_response}")
                                    function_responses.append(function_response)

                                elif fc.name == "run_jules_agent":
                                    if INCLUDE_RAW_LOGS:
                                        print(f"[ADA DEBUG] [TOOL] Tool Call: 'run_jules_agent' with prompt='{prompt}'")
                                    source = fc.args.get("source")
                                    result = await self.handle_jules_request(prompt, source)
                                    function_response = types.FunctionResponse(
                                        id=fc.id,
                                        name=fc.name,
                                        response={"result": result},
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "send_jules_feedback":
                                    if INCLUDE_RAW_LOGS:
                                        print(f"[ADA DEBUG] [TOOL] Tool Call: 'send_jules_feedback'")
                                    session_id = fc.args.get("session_id")
                                    feedback = fc.args.get("feedback")
                                    result = await self.handle_jules_feedback(session_id, feedback)
                                    function_response = types.FunctionResponse(
                                        id=fc.id,
                                        name=fc.name,
                                        response={"result": result},
                                    )
                                    function_responses.append(function_response)


                                elif fc.name == "list_jules_sources":
                                    if INCLUDE_RAW_LOGS:
                                        print("[ADA DEBUG] [TOOL] Tool Call: 'list_jules_sources'")
                                    result = await self.handle_list_jules_sources()
                                    function_response = types.FunctionResponse(
                                        id=fc.id,
                                        name=fc.name,
                                        response={"result": result},
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "list_jules_sessions":
                                    if INCLUDE_RAW_LOGS:
                                        print("[ADA DEBUG] [TOOL] Tool Call: 'list_jules_sessions'")
                                    result = await self.handle_list_jules_sessions()
                                    function_response = types.FunctionResponse(
                                        id=fc.id,
                                        name=fc.name,
                                        response={"result": result},
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "list_jules_activities":
                                    if INCLUDE_RAW_LOGS:
                                        print("[ADA DEBUG] [TOOL] Tool Call: 'list_jules_activities'")
                                    session_id = fc.args.get("session_id")
                                    result = await self.handle_list_jules_activities(session_id)
                                    function_response = types.FunctionResponse(
                                        id=fc.id,
                                        name=fc.name,
                                        response={"result": result},
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "write_file":
                                    path = fc.args["path"]
                                    content = fc.args["content"]
                                    if INCLUDE_RAW_LOGS:
                                        print(f"[ADA DEBUG] [TOOL] Tool Call: 'write_file' path='{path}'")
                                    asyncio.create_task(self.handle_write_file(path, content))
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": "Writing file..."}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "read_directory":
                                    path = fc.args["path"]
                                    if INCLUDE_RAW_LOGS:
                                        print(f"[ADA DEBUG] [TOOL] Tool Call: 'read_directory' path='{path}'", flush=True)
                                    asyncio.create_task(self.handle_read_directory(path))
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": "Reading directory..."}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "read_file":
                                    path = fc.args["path"]
                                    if INCLUDE_RAW_LOGS:
                                        print(f"[ADA DEBUG] [TOOL] Tool Call: 'read_file' path='{path}'", flush=True)
                                    asyncio.create_task(self.handle_read_file(path))
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": "Reading file..."}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "create_project":
                                    name = fc.args["name"]
                                    if INCLUDE_RAW_LOGS:
                                        print(f"[ADA DEBUG] [TOOL] Tool Call: 'create_project' name='{name}'", flush=True)
                                    success, msg = self.project_manager.create_project(name)
                                    if success:
                                        # Auto-switch to the newly created project
                                        self.project_manager.switch_project(name)
                                        msg += f" Switched to '{name}'."
                                        if self.on_project_update:
                                            self.on_project_update(name)
                                        self.reconnect()
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": msg}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "switch_project":
                                    name = fc.args["name"]
                                    if INCLUDE_RAW_LOGS:
                                        print(f"[ADA DEBUG] [TOOL] Tool Call: 'switch_project' name='{name}'", flush=True)
                                    success, msg = self.project_manager.switch_project(name)
                                    if success:
                                        if self.on_project_update:
                                            self.on_project_update(name)

                                        # Trigger a reconnect to load the new project's system prompt
                                        self.reconnect()

                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": msg}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "list_projects":
                                    if INCLUDE_RAW_LOGS:
                                        print(f"[ADA DEBUG] [TOOL] Tool Call: 'list_projects'", flush=True)
                                    projects = self.project_manager.list_projects()
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": f"Available projects: {', '.join(projects)}"}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "list_smart_devices":
                                    if INCLUDE_RAW_LOGS:
                                        print(f"[ADA DEBUG] [TOOL] Tool Call: 'list_smart_devices'", flush=True)
                                    # Use cached devices directly for speed
                                    # devices_dict is {ip: SmartDevice}
                                    # Use cached devices directly for speed
                                    # devices_dict is {ip: SmartDevice}

                                    dev_summaries = []
                                    frontend_list = []

                                    for ip, d in self.kasa_agent.devices.items():
                                        dev_type = "unknown"
                                        if d.is_bulb: dev_type = "bulb"
                                        elif d.is_plug: dev_type = "plug"
                                        elif d.is_strip: dev_type = "strip"
                                        elif d.is_dimmer: dev_type = "dimmer"

                                        # Format for Model
                                        info = f"{d.alias} (IP: {ip}, Type: {dev_type})"
                                        if d.is_on:
                                            info += " [ON]"
                                        else:
                                            info += " [OFF]"
                                        dev_summaries.append(info)

                                        # Format for Frontend
                                        frontend_list.append({
                                            "ip": ip,
                                            "alias": d.alias,
                                            "model": d.model,
                                            "type": dev_type,
                                            "is_on": d.is_on,
                                            "brightness": d.brightness if d.is_bulb or d.is_dimmer else None,
                                            "hsv": d.hsv if d.is_bulb and d.is_color else None,
                                            "has_color": d.is_color if d.is_bulb else False,
                                            "has_brightness": d.is_dimmable if d.is_bulb or d.is_dimmer else False
                                        })

                                    result_str = "No devices found in cache."
                                    if dev_summaries:
                                        result_str = "Found Devices (Cached):\n" + "\n".join(dev_summaries)

                                    # Trigger frontend update
                                    if self.on_device_update:
                                        self.on_device_update(frontend_list)

                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result_str}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "control_light":
                                    target = fc.args["target"]
                                    action = fc.args["action"]
                                    brightness = fc.args.get("brightness")
                                    color = fc.args.get("color")

                                    if INCLUDE_RAW_LOGS:
                                        print(f"[ADA DEBUG] [TOOL] Tool Call: 'control_light' Target='{target}' Action='{action}'")

                                    result_msg = f"Action '{action}' on '{target}' failed."
                                    success = False

                                    if action == "turn_on":
                                        success = await self.kasa_agent.turn_on(target)
                                        if success:
                                            result_msg = f"Turned ON '{target}'."
                                    elif action == "turn_off":
                                        success = await self.kasa_agent.turn_off(target)
                                        if success:
                                            result_msg = f"Turned OFF '{target}'."
                                    elif action == "set":
                                        success = True
                                        result_msg = f"Updated '{target}':"

                                    # Apply extra attributes if 'set' or if we just turned it on and want to set them too
                                    if success or action == "set":
                                        if brightness is not None:
                                            sb = await self.kasa_agent.set_brightness(target, brightness)
                                            if sb:
                                                result_msg += f" Set brightness to {brightness}."
                                        if color is not None:
                                            sc = await self.kasa_agent.set_color(target, color)
                                            if sc:
                                                result_msg += f" Set color to {color}."

                                    # Notify Frontend of State Change
                                    if success:
                                        # We don't need full discovery, just refresh known state or push update
                                        # But for simplicity, let's get the standard list representation
                                        # KasaAgent updates its internal state on control, so we can rebuild the list

                                        # Quick rebuild of list from internal dict
                                        updated_list = []
                                        for ip, dev in self.kasa_agent.devices.items():
                                            # We need to ensure we have the correct dict structure expected by frontend
                                            # We duplicate logic from KasaAgent.discover_devices a bit, but that's okay for now or we can add a helper
                                            # Ideally KasaAgent has a 'get_devices_list()' method.
                                            # Use the cached objects in self.kasa_agent.devices

                                            dev_type = "unknown"
                                            if dev.is_bulb: dev_type = "bulb"
                                            elif dev.is_plug: dev_type = "plug"
                                            elif dev.is_strip: dev_type = "strip"
                                            elif dev.is_dimmer: dev_type = "dimmer"

                                            d_info = {
                                                "ip": ip,
                                                "alias": dev.alias,
                                                "model": dev.model,
                                                "type": dev_type,
                                                "is_on": dev.is_on,
                                                "brightness": dev.brightness if dev.is_bulb or dev.is_dimmer else None,
                                                "hsv": dev.hsv if dev.is_bulb and dev.is_color else None,
                                                "has_color": dev.is_color if dev.is_bulb else False,
                                                "has_brightness": dev.is_dimmable if dev.is_bulb or dev.is_dimmer else False
                                            }
                                            updated_list.append(d_info)

                                        if self.on_device_update:
                                            self.on_device_update(updated_list)
                                    else:
                                        # Report Error
                                        if self.on_error:
                                            self.on_error(result_msg)

                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result_msg}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "discover_printers":
                                    if INCLUDE_RAW_LOGS:
                                        print(f"[ADA DEBUG] [TOOL] Tool Call: 'discover_printers'")
                                    printers = await self.printer_agent.discover_printers()
                                    # Format for model
                                    if printers:
                                        printer_list = []
                                        for p in printers:
                                            printer_list.append(f"{p['name']} ({p['host']}:{p['port']}, type: {p['printer_type']})")
                                        result_str = "Found Printers:\n" + "\n".join(printer_list)
                                    else:
                                        result_str = "No printers found on network. Ensure printers are on and running OctoPrint/Moonraker."

                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result_str}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "print_stl":
                                    stl_path = fc.args["stl_path"]
                                    printer = fc.args["printer"]
                                    profile = fc.args.get("profile")

                                    if INCLUDE_RAW_LOGS:
                                        print(f"[ADA DEBUG] [TOOL] Tool Call: 'print_stl' STL='{stl_path}' Printer='{printer}'")

                                    # Resolve 'current' to project STL
                                    if stl_path.lower() == "current":
                                        stl_path = "output.stl" # Let printer agent resolve it in root_path

                                    # Get current project path
                                    project_path = str(self.project_manager.get_current_project_path())

                                    result = await self.printer_agent.print_stl(
                                        stl_path,
                                        printer,
                                        profile,
                                        root_path=project_path
                                    )
                                    result_str = result.get("message", "Unknown result")

                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result_str}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "get_print_status":
                                    printer = fc.args["printer"]
                                    if INCLUDE_RAW_LOGS:
                                        print(f"[ADA DEBUG] [TOOL] Tool Call: 'get_print_status' Printer='{printer}'")

                                    status = await self.printer_agent.get_print_status(printer)
                                    if status:
                                        result_str = f"Printer: {status.printer}\n"
                                        result_str += f"State: {status.state}\n"
                                        result_str += f"Progress: {status.progress_percent:.1f}%\n"
                                        if status.time_remaining:
                                            result_str += f"Time Remaining: {status.time_remaining}\n"
                                        if status.time_elapsed:
                                            result_str += f"Time Elapsed: {status.time_elapsed}\n"
                                        if status.filename:
                                            result_str += f"File: {status.filename}\n"
                                        if status.temperatures:
                                            temps = status.temperatures
                                            if "hotend" in temps:
                                                result_str += f"Hotend: {temps['hotend']['current']:.0f}°C / {temps['hotend']['target']:.0f}°C\n"
                                            if "bed" in temps:
                                                result_str += f"Bed: {temps['bed']['current']:.0f}°C / {temps['bed']['target']:.0f}°C"
                                    else:
                                        result_str = f"Could not get status for printer '{printer}'. Ensure it is discovered first."

                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result_str}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "iterate_cad":
                                    prompt = fc.args["prompt"]
                                    if INCLUDE_RAW_LOGS:
                                        print(f"[ADA DEBUG] [TOOL] Tool Call: 'iterate_cad' Prompt='{prompt}'")

                                    # Emit status
                                    if self.on_cad_status:
                                        self.on_cad_status("generating")

                                    # Get project cad folder path
                                    cad_output_dir = str(self.project_manager.get_current_project_path() / "cad")

                                    # Call CadAgent to iterate on the design
                                    cad_data = await self.cad_agent.iterate_prototype(prompt, output_dir=cad_output_dir)

                                    if cad_data:
                                        if INCLUDE_RAW_LOGS:
                                            print(f"[ADA DEBUG] [OK] CadAgent iteration returned data successfully.")

                                        # Dispatch to frontend
                                        if self.on_cad_data:
                                            if INCLUDE_RAW_LOGS:
                                                print(f"[ADA DEBUG] [SEND] Dispatching iterated CAD data to frontend...")
                                            self.on_cad_data(cad_data)
                                            if INCLUDE_RAW_LOGS:
                                                print(f"[ADA DEBUG] [SENT] Dispatch complete.")

                                        # Save to Project
                                        self.project_manager.save_cad_artifact("output.stl", f"Iteration: {prompt}")

                                        result_str = f"Successfully iterated design: {prompt}. The updated 3D model is now displayed."
                                    else:
                                        if INCLUDE_RAW_LOGS:
                                            print(f"[ADA DEBUG] [ERR] CadAgent iteration returned None.")
                                        result_str = f"Failed to iterate design with prompt: {prompt}"

                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result_str}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "set_timer":
                                    duration = fc.args["duration"]
                                    name = fc.args["name"]
                                    result = await self.timer_agent.set_timer(duration, name)
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "modify_timer":
                                    name = fc.args["name"]
                                    new_duration = fc.args.get("new_duration")
                                    new_timestamp = fc.args.get("new_timestamp")
                                    result = await self.timer_agent.modify_timer(name, new_duration, new_timestamp)
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "set_reminder":
                                    timestamp = fc.args["timestamp"]
                                    name = fc.args["name"]
                                    result = await self.timer_agent.set_reminder(timestamp, name)
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "list_timers":
                                    result = self.timer_agent.list_timers()
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "delete_entry":
                                    name = fc.args["name"]
                                    result = self.timer_agent.delete_entry(name)
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "check_for_updates":
                                    try:
                                        print(f"[ADA DEBUG] [TOOL] check_for_updates was called. INCLUDE_RAW_LOGS={INCLUDE_RAW_LOGS}", flush=True)
                                        result = await self.update_agent.check_for_updates()
                                        print(f"[ADA DEBUG] [TOOL] check_for_updates result: {result}", flush=True)
                                    except Exception as update_err:
                                        print(f"[ADA DEBUG] [ERR] Error in check_for_updates tool: {update_err}")
                                        traceback.print_exc()
                                        result = f"Error checking for updates: {str(update_err)}"

                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "apply_update":
                                    try:
                                        result = await self.update_agent.apply_update()
                                    except Exception as update_err:
                                        print(f"[ADA DEBUG] [ERR] Error in apply_update tool: {update_err}")
                                        traceback.print_exc()
                                        result = f"Error applying update: {str(update_err)}"

                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result}
                                    )
                                    function_responses.append(function_response)
                        if function_responses:
                            if INCLUDE_RAW_LOGS:
                                print(f"[ADA DEBUG] [TOOL] Sending tool responses back to model: {function_responses}", flush=True)
                            await self.session.send_tool_response(function_responses=function_responses)
                
                # Turn/Response Loop Finished
                # Check if we have a Slack message to send
                if self.message_source == 'slack' and self.slack_agent and full_turn_text_response.strip():
                    if INCLUDE_RAW_LOGS:
                        print(f"[ADA DEBUG] [SLACK] End of turn. Sending full response to Slack: '{full_turn_text_response.strip()}'")
                    asyncio.create_task(self.slack_agent.send_message(full_turn_text_response.strip()))

                # Reset the message source after the turn is fully processed
                self.message_source = None

                self.flush_chat()

                while not self.audio_in_queue.empty():
                    self.audio_in_queue.get_nowait()
        except Exception as e:
            if "1011" in str(e) or "CANCELLED" in str(e).upper():
                if INCLUDE_RAW_LOGS:
                    print(f"[ADA DEBUG] [WARN] Transient Session Error in receive_audio: {e}")
            else:
                if INCLUDE_RAW_LOGS:
                    print(f"Error in receive_audio: {e}")
            traceback.print_exc()
            # CRITICAL: Re-raise to crash the TaskGroup and trigger outer loop reconnect
            raise e

    async def play_audio(self):
        stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE,
            output=True,
            output_device_index=self.output_device_index,
        )
        while True:
            bytestream = await self.audio_in_queue.get()
            if self.on_audio_data:
                self.on_audio_data(bytestream)
            await asyncio.to_thread(stream.write, bytestream)

    async def get_frames(self):
        cap = await asyncio.to_thread(cv2.VideoCapture, 0, cv2.CAP_AVFOUNDATION)
        while True:
            if self.paused:
                await asyncio.sleep(0.1)
                continue
            frame = await asyncio.to_thread(self._get_frame, cap)
            if frame is None:
                break
            await asyncio.sleep(1.0)
            if self.out_queue:
                await self.out_queue.put(frame)
        cap.release()

    def _get_frame(self, cap):
        ret, frame = cap.read()
        if not ret:
            return None
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = PIL.Image.fromarray(frame_rgb)
        img.thumbnail([1024, 1024])
        image_io = io.BytesIO()
        img.save(image_io, format="jpeg")
        image_io.seek(0)
        image_bytes = image_io.read()
        return {"mime_type": "image/jpeg", "data": base64.b64encode(image_bytes).decode()}

    async def _get_screen(self):
        pass 
    async def get_screen(self):
         pass

    async def _session_runner(self, start_message=None, is_reconnect=False):
        """Handles a single connection and run-loop of the voice agent."""
        service_info = f"Service: Gemini Multimodal Live API, Endpoint: {MODEL}"
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [SESSION] Starting session runner. Reconnect: {is_reconnect}")
        try:
            if INCLUDE_RAW_LOGS:
                print(f"[ADA DEBUG] [CONNECT] Connecting to {service_info}...")

            config = self._get_live_connect_config()

            tasks = []
            async with client.aio.live.connect(model=MODEL, config=config) as session:
                try:
                    self.session = session
                    self.timer_agent.session = session
                    self.proactive_agent.session = session

                    self.audio_in_queue = asyncio.Queue()
                    self.out_queue = asyncio.Queue(maxsize=10)

                    tasks.append(asyncio.create_task(self.send_realtime()))
                    # Run listen_audio as a separate, non-critical background task
                    # This prevents the main session from crashing if audio input fails (e.g., in a headless environment)
                    audio_input_task = asyncio.create_task(self.listen_audio())
                    tasks.append(audio_input_task) # Still track it for cleanup

                    if self.video_mode == "camera":
                        tasks.append(asyncio.create_task(self.get_frames()))
                    elif self.video_mode == "screen":
                        tasks.append(asyncio.create_task(self.get_screen()))

                    tasks.append(asyncio.create_task(self.receive_audio()))
                    tasks.append(asyncio.create_task(self.play_audio()))
                    tasks.append(asyncio.create_task(self.proactive_agent.run()))

                    # Start the Jules session monitoring task
                    tasks.append(asyncio.create_task(self.jules_agent.start_monitoring(self._handle_jules_status_change)))

                    if not is_reconnect:
                        if start_message:
                            if INCLUDE_RAW_LOGS:
                                print(f"[ADA DEBUG] [INFO] Sending start message: {start_message}")
                            await self.session.send(input=start_message, end_of_turn=True)

                        if self.on_project_update and self.project_manager:
                            self.on_project_update(self.project_manager.current_project)
                    else:
                        # Display Reconnect GIF and Stay Silent
                        if INCLUDE_RAW_LOGS:
                            print(f"[ADA DEBUG] [RECONNECT] Connection restored. Fetching reconnect GIF...")

                        try:
                            api_key = os.getenv("GIPHY_API_KEY")
                            if api_key:
                                # Run search in thread to avoid blocking loop
                                response = await asyncio.to_thread(
                                    self.giphy_client.gifs_search_get,
                                    api_key,
                                    "I'm back",
                                    limit=25
                                )
                                if response.data:
                                    # Pick a random GIF
                                    selected_gif = random.choice(response.data)
                                    gif_url = selected_gif.images.original.url

                                    if INCLUDE_RAW_LOGS:
                                        print(f"[ADA DEBUG] [RECONNECT] Selected GIF: {gif_url}")

                                    # Display GIF for 10 seconds
                                    if self.on_display_content:
                                        self.on_display_content({
                                            "content_type": "image",
                                            "url": gif_url,
                                            "duration": 10000
                                        })
                                else:
                                    if INCLUDE_RAW_LOGS:
                                        print(f"[ADA DEBUG] [RECONNECT] No GIFs found.")
                            else:
                                if INCLUDE_RAW_LOGS:
                                    print(f"[ADA DEBUG] [RECONNECT] Missing Giphy API Key.")

                        except Exception as e:
                            if INCLUDE_RAW_LOGS:
                                print(f"[ADA DEBUG] [ERR] Failed to display reconnect GIF: {e}")

                    self._last_input_transcription = ""
                    self._last_output_transcription = ""
                    self.chat_buffer = {"sender": None, "text": ""}

                    stop_task = asyncio.create_task(self.stop_event.wait())
                    reconnect_task = asyncio.create_task(self._reconnect_needed.wait())

                    wait_tasks = tasks + [stop_task, reconnect_task]
                    done, pending = await asyncio.wait(
                        wait_tasks,
                        return_when=asyncio.FIRST_COMPLETED
                    )

                    # If a signal task is done, cancel the other signal task.
                    if stop_task in done:
                        reconnect_task.cancel()
                    elif reconnect_task in done:
                        stop_task.cancel()
                    else:
                        # A worker task finished (likely crashed). Log and trigger reconnect.
                        if INCLUDE_RAW_LOGS:
                            print("[ADA DEBUG] [ERR] A worker task exited unexpectedly. Triggering reconnect.")
                        # Attempt to find the crashed task and log its exception
                        for done_task in done:
                            try:
                                if done_task.exception():
                                    print(f"[ADA DEBUG] [ERR] Task exception: {done_task.exception()}")
                            except asyncio.InvalidStateError:
                                pass # No exception
                        reconnect_task.cancel()
                        stop_task.cancel()
                        self._reconnect_needed.clear()
                        return True

                    if reconnect_task in done:
                        if INCLUDE_RAW_LOGS:
                            print("[ADA DEBUG] [RECONNECT] Reconnect event received. Ending session...")
                        self._reconnect_needed.clear()
                        return True # Signal for reconnect

                finally:
                    # Flush chat buffer to save any pending conversation before teardown
                    self.flush_chat()
                    if INCLUDE_RAW_LOGS:
                        print(f"[ADA DEBUG] [SESSION] Tearing down {len(tasks)} session tasks...")
                    for task in tasks:
                        task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                    if INCLUDE_RAW_LOGS:
                        print("[ADA DEBUG] [SESSION] All session tasks cancelled.")
                    # Add small delay as requested
                    await asyncio.sleep(0.1)

        except (Exception, asyncio.CancelledError) as e:
            if self.stop_event.is_set():
                if INCLUDE_RAW_LOGS:
                    print(f"[ADA DEBUG] [INFO] Session runner stopping.")
                return False

            error_msg = str(e)
            if "429" in error_msg:
                 print(f"Rate limited (429) for {service_info}.")
            else:
                if INCLUDE_RAW_LOGS:
                    print(f"[ADA DEBUG] [ERR] Connection Error in session runner ({service_info}): {e}")

            if hasattr(e, 'exceptions'):
                for idx, se in enumerate(e.exceptions):
                    if INCLUDE_RAW_LOGS:
                        print(f"  Sub-exception {idx}: {se}")

            return True
        finally:
            if INCLUDE_RAW_LOGS:
                print("[ADA DEBUG] [SESSION] Session runner cleanup.")
            if hasattr(self, 'audio_stream') and self.audio_stream:
                try:
                    self.audio_stream.close()
                except:
                    pass

        return False

    async def run(self, start_message=None):
        retry_delay = 1
        is_reconnect = False

        while not self.stop_event.is_set():
            if INCLUDE_RAW_LOGS:
                print("[ADA DEBUG] [RUN] Main loop is running. Starting session runner.")
            should_reconnect = await self._session_runner(start_message, is_reconnect)

            if not should_reconnect:
                if INCLUDE_RAW_LOGS:
                    print("[ADA DEBUG] [RUN] Session runner requested no reconnect. Exiting main loop.")
                break

            is_reconnect = True
            start_message = None

            if not self.stop_event.is_set():
                if INCLUDE_RAW_LOGS:
                    print(f"[ADA DEBUG] [RETRY] Reconnecting in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 10)

        if INCLUDE_RAW_LOGS:
            print("[ADA DEBUG] [INFO] Main run loop has exited.")

def get_input_devices():
    p = pyaudio.PyAudio()
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    devices = []
    for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            devices.append((i, p.get_device_info_by_host_api_device_index(0, i).get('name')))
    p.terminate()
    return devices

def get_output_devices():
    p = pyaudio.PyAudio()
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    devices = []
    for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxOutputChannels')) > 0:
            devices.append((i, p.get_device_info_by_host_api_device_index(0, i).get('name')))
    p.terminate()
    return devices

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        type=str,
        default=DEFAULT_MODE,
        help="pixels to stream from",
        choices=["camera", "screen", "none"],
    )
    args = parser.parse_args()
    main = AudioLoop(video_mode=args.mode)
    asyncio.run(main.run())
