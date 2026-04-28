import asyncio
import queue
import base64
import json
import os
import sys
import traceback
from dotenv import load_dotenv
import cv2
import numpy as np
try:
    import pyaudio
except ImportError:
    pyaudio = None
import mss
import argparse
import math
import struct
import time
import random
from datetime import datetime

from backend.time_utils import format_datetime, get_local_time
from backend.weather_agent import WeatherAgent
from backend.giphy_agent import GiphyAgent
from google import genai
from google.genai import types

if sys.version_info < (3, 11, 0):
    import taskgroup, exceptiongroup
    asyncio.TaskGroup = taskgroup.TaskGroup
    asyncio.ExceptionGroup = exceptiongroup.ExceptionGroup

from backend.tools import tools_list, trello_tools
from backend.tool_registry import ToolRegistry

if pyaudio:
    FORMAT = pyaudio.paInt16
else:
    FORMAT = 8  # Fallback

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

tools = tools_list

if pyaudio:
    try:
        pya = pyaudio.PyAudio()
    except Exception:
        print("[ADA] Warning: PyAudio failed to initialize.")
        pya = None
else:
    pya = None

from backend.cad_agent import CadAgent
from backend.web_agent import WebAgent
from backend.kasa_agent import KasaAgent
from backend.printer_agent import PrinterAgent
from backend.trello_agent import TrelloAgent
from backend.jules_agent import JulesAgent
from backend.openhands_agent import OpenHandsAgent
from backend.timer_agent import TimerAgent
from backend.update_agent import UpdateAgent
from backend.search_agent import SearchAgent
from backend.scraper_agent import ScraperAgent
from backend.proactive_agent import ProactiveAgent
from backend.os_agent import OSAgent
from backend.music_agent import MusicAgent
from backend.writing_agent import WritingAgent
from backend.ollama_agent import OllamaAgent
from backend.fs_agent import FileSystemAgent
from backend.git_agent import GitAgent
try:
    from backend.task_manager import TaskManager
except ImportError:
    from backend.task_manager import TaskManager

class AudioLoop:
    def __init__(self, sio=None, video_mode=DEFAULT_MODE, on_audio_data=None, on_video_frame=None, on_cad_data=None, on_web_data=None, on_transcription=None, on_tool_confirmation=None, on_cad_status=None, on_cad_thought=None, on_project_update=None, on_device_update=None, on_error=None, input_device_index=None, input_device_name=None, output_device_index=None, kasa_agent=None, project_manager=None, on_display_content=None, slack_agent=None, scraper_agent=None):
        self.sio = sio
        self.slack_agent = slack_agent
        self.automation_engine = None
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
        self.last_input_source = 'ui'  # Default to 'ui'

        # Initialize ProjectManager
        if project_manager:
            self.project_manager = project_manager
        else:
            from project_manager import ProjectManager
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            self.project_manager = ProjectManager(project_root)

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
        self.kasa_agent.set_on_update(self.on_device_update)
        self.printer_agent = PrinterAgent()
        self.printer_agent.set_root_path(self.project_manager.get_current_project_path())
        self.trello_agent = TrelloAgent()
        self.timer_agent = TimerAgent(sio=self.sio)
        self.weather_agent = WeatherAgent()
        self.giphy_agent = GiphyAgent()
        self.scraper_agent = scraper_agent if scraper_agent else ScraperAgent()
        
        def handle_update_log(message):
            # Always print to console from the main thread context
            print(f"[ADA DEBUG] {message}", flush=True)

        self.update_agent = UpdateAgent(on_log=handle_update_log)

        # Instantiate JulesAgent for session management and monitoring
        self.jules_agent = JulesAgent(project_manager=self.project_manager)
        self.openhands_agent = OpenHandsAgent()

        self.stop_event = asyncio.Event()
        self._reconnect_needed = asyncio.Event()
        
        self._pending_confirmations = {}

        # Coding Task Routing State
        self._pending_coding_task_prompt = None
        self._pending_coding_task_source = None

        # Video buffering state
        self._latest_image_payload = None
        # VAD State
        self._is_speaking = False
        self._silence_start_time = None
        
        self.task_manager = TaskManager(self.project_manager.get_current_project_path())
        self.search_agent = SearchAgent(self.trello_agent, self.project_manager, self.scraper_agent)
        self.proactive_agent = ProactiveAgent(
            session=None,
            project_manager=self.project_manager,
            vision_provider=lambda: self._latest_image_payload,
            genai_client=client
        )
        self.os_agent = OSAgent()
        self.music_agent = MusicAgent(sio=self.sio)
        self.ollama_agent = OllamaAgent()
        self.fs_agent = FileSystemAgent(self.project_manager)
        self.git_agent = GitAgent(self.project_manager)
        self.writing_agent = WritingAgent(self.project_manager, self.git_agent)

        self.sct = None

        # Initialize Face Detector for Presence
        try:
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        except Exception as e:
            if INCLUDE_RAW_LOGS:
                print(f"[ADA DEBUG] [WARN] Failed to load face cascade: {e}")
            self.face_cascade = None
        self._last_face_check_time = 0

        # Initialize Tool Registry
        self.tool_registry = ToolRegistry()
        self._register_tools()

        # Sync Initial Project State
        if self.on_project_update:
            pass

    async def _trigger_morning_briefing_offer(self):
        """Triggers the morning briefing offer if pending."""
        if self.automation_engine and self.automation_engine.briefing_status == "PENDING":
            if INCLUDE_RAW_LOGS:
                print("[ADA DEBUG] [BRIEFING] Triggering Morning Briefing Offer (Presence/Interaction detected).")

            # Mark as OFFERED so we don't spam
            self.automation_engine.briefing_status = "OFFERED"

            # Send System Notification to prompt the model
            # We include the time generated to add context
            gen_time = "09:00" # Default or fetch from report timestamp if available
            msg = f"System Notification: The user's Daily Morning Briefing is ready (generated at {gen_time}). Please politely inform the user: 'Good morning, Sir. I have your daily briefing ready. Would you like to hear it?'"

            if self.session:
                try:
                    await self.session.send(input=msg, end_of_turn=False)
                except Exception as e:
                    if INCLUDE_RAW_LOGS:
                        print(f"[ADA DEBUG] [ERR] Failed to send briefing offer: {e}")

    def flush_chat(self):
        """Forces the current chat buffer to be written to log."""
        if self.chat_buffer["sender"] and self.chat_buffer["text"].strip():
            self.project_manager.log_chat(self.chat_buffer["sender"], self.chat_buffer["text"])
            self.chat_buffer = {"sender": None, "text": ""}
        # Reset transcription tracking for new turn
        self._last_input_transcription = ""
        self._last_output_transcription = ""

    def update_permissions(self, permissions):
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] Updating permissions: {permissions}")
        self.tool_permissions = permissions

    def set_paused(self, paused):
        self.paused = paused

    def set_last_input_source(self, source):
        self.last_input_source = source

    def stop(self):
        self.stop_event.set()
        if self.music_agent:
            try:
                # If we are in the main thread (shutdown), we shouldn't create a task in the main loop for a sub-loop
                asyncio.create_task(self.music_agent.stop())
            except RuntimeError:
                pass

        # If we have a running task in another loop, we need to cancel it
        if hasattr(self, '_main_task') and self._main_task and not self._main_task.done():
            self._main_task.get_loop().call_soon_threadsafe(self._main_task.cancel)

    def reconnect(self):
        """Signals the main loop to reconnect."""
        if INCLUDE_RAW_LOGS:
            print("[ADA DEBUG] [RECONNECT] Reconnect signaled.")
        self._reconnect_needed.set()

    async def _handle_jules_status_change(self, session_id, title, new_state):
        """Handles UI and voice notifications for Jules session status changes and syncs fleet."""
        notification_text = f"Jules task '{title}' has moved to {new_state}."
        self.notify_user(notification_text, duration=20000)

        # Try to sync this state change with the fleet manager
        try:
            from backend.server import fleet_manager, sio, check_and_start_next_task, fleet_account_active_sessions, get_all_accounts

            agent_id, repo_name, task_id = fleet_manager.get_by_session(session_id)
            if agent_id and repo_name and task_id:
                # Map Jules state to fleet state where possible
                # The fleet manager queue tracks "status": pending, in_progress, completed, failed
                # The agent tracks "status": idle, working, stuck, error

                if new_state == "COMPLETED":
                    fleet_manager.update_task_status(repo_name, task_id, "completed")
                    fleet_manager.update_agent_session(agent_id, None, "idle")
                elif new_state == "FAILED":
                    fleet_manager.update_task_status(repo_name, task_id, "failed", error_message="Jules session failed.")
                    fleet_manager.update_agent_session(agent_id, None, "error")
                elif new_state in ["QUEUED", "PLANNING", "IN_PROGRESS"]:
                    fleet_manager.update_task_status(repo_name, task_id, "in_progress")
                    fleet_manager.update_agent_session(agent_id, session_id, "working")
                elif new_state in ["AWAITING_PLAN_APPROVAL", "AWAITING_USER_FEEDBACK"]:
                    fleet_manager.update_task_status(repo_name, task_id, "needing_feedback")
                    fleet_manager.update_agent_session(agent_id, session_id, "needing_feedback")

                    if self.session:
                        try:
                            message = f"Jules session '{title}' (ID: {session_id}) is currently {new_state}. Please review the session and provide feedback using the 'send_jules_feedback' tool."
                            asyncio.create_task(self.session.send(input=f"System Notification: {message}", end_of_turn=False))
                        except Exception as e:
                            if INCLUDE_RAW_LOGS:
                                print(f"[ADA DEBUG] [ERR] Failed to send feedback system notification: {e}")
                elif new_state == "PAUSED":
                    fleet_manager.update_task_status(repo_name, task_id, "in_progress")
                    fleet_manager.update_agent_session(agent_id, session_id, "stuck")

                # Emit update
                await sio.emit('fleet_state_update', fleet_manager.get_state())

                # If finished, optionally trigger next task if the agent is now idle
                if new_state in ["COMPLETED", "FAILED"]:
                    # Wait a tiny bit to let _on_jules_finished handle it if it hasn't already
                    await asyncio.sleep(1)
                    await check_and_start_next_task(repo_name, agent_id)

        except Exception as e:
            if INCLUDE_RAW_LOGS:
                print(f"[ADA DEBUG] [ERR] Failed to sync fleet status for {session_id}: {e}")

    async def _handle_jules_triage(self, session_id, message_content):
        """
        Intercepts Jules agent messages, acts as a manager using Ollama to triage,
        and either auto-replies or escalates to the human user.
        """
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [TRIAGE] Intercepted Jules message for session {session_id}: {message_content[:50]}...")

        # 1. Construct Context
        context = ""
        if self.project_manager:
            context = self.project_manager.get_project_context_summary() or "No specific project context available."

        # 2. Build Triage Prompt
        triage_prompt = f"""
You are an engineering manager. Your developer 'Jules' (Session ID: {session_id}) just sent this message:

"{message_content}"

Project Context:
{context}

Can you answer this question or resolve this blocker immediately using your general engineering knowledge and the provided context?
If YES: Output ONLY a direct, helpful, and concise response to send back to Jules. Do not include introductory text.
If NO (it requires high-level human approval, PR review, external API keys, or complex product decisions): Output EXACTLY the word "ESCALATE:" followed by a brief summary of why human attention is needed.
"""

        # 3. Call internal LLM (Ollama)
        try:
            # Reusing the existing OllamaAgent for internal reasoning
            triage_response = await self.ollama_agent.chat(triage_prompt, role="manager_triage")

            if not triage_response:
                # Fallback to escalate if LLM fails
                self.notify_user(f"Jules task {session_id} requires attention: {message_content[:100]}...", duration=20000)
                return

            triage_response = triage_response.strip()

            if triage_response.startswith("ESCALATE:"):
                # Human needed!
                escalation_reason = triage_response.replace("ESCALATE:", "").strip()
                if INCLUDE_RAW_LOGS:
                    print(f"[ADA DEBUG] [TRIAGE] ESCALATING session {session_id}. Reason: {escalation_reason}")

                # Notify the user
                self.notify_user(f"Jules task {session_id} escalated: {escalation_reason}", duration=20000)

                # Optionally update UI or slack
                if self.slack_agent and self.project_manager.get_project_config().get("jules_slack_notifications", False):
                    self.slack_agent.send_message(f"🚨 *Escalation* for Jules Task `{session_id}`:\n{escalation_reason}")
            else:
                # Auto-reply!
                if INCLUDE_RAW_LOGS:
                    print(f"[ADA DEBUG] [TRIAGE] AUTO-REPLYING to session {session_id}: {triage_response}")

                # Send message back to Jules
                await self.jules_agent.send_message(session_id, triage_response)

                # Briefly notify UI so user knows Ada handled it
                self.notify_user(f"Auto-replied to Jules task {session_id}.", duration=5000, send_voice=False)

        except Exception as e:
            if INCLUDE_RAW_LOGS:
                print(f"[ADA DEBUG] [ERR] Triage failed for {session_id}: {e}")
            self.notify_user(f"Jules task {session_id} sent a message: {message_content[:50]}...", duration=20000)

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
        if not pya:
             if INCLUDE_RAW_LOGS:
                 print("[ADA] PyAudio not available. Audio input disabled.")
             while not self.stop_event.is_set():
                 await asyncio.sleep(1)
             return

        try:
            mic_info = pya.get_default_input_device_info()
        except Exception as e:
            if INCLUDE_RAW_LOGS:
                print(f"[ADA] [WARN] No default input device found: {e}")
            mic_info = {"index": -1}

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
        actual_input_device_index = resolved_input_device_index if resolved_input_device_index is not None else mic_info.get("index")
        
        if actual_input_device_index == -1 or actual_input_device_index is None:
             if INCLUDE_RAW_LOGS:
                 print("[ADA] [WARN] No valid input device index. Audio input disabled (Waiting loop).")
             # Keep the task alive but idle to prevent session teardown
             while not self.stop_event.is_set():
                 await asyncio.sleep(1)
             return

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
            # Keep the task alive but idle to prevent session teardown
            while not self.stop_event.is_set():
                await asyncio.sleep(1)
            return

        if __debug__:
            kwargs = {"exception_on_overflow": False}
        else:
            kwargs = {}
        
        # VAD Constants
        VAD_THRESHOLD = 800 # Adj based on mic sensitivity (800 is conservative for 16-bit)
        SILENCE_DURATION = 0.5 # Seconds of silence to consider "done speaking"
        PRE_ROLL_CHUNKS = int(SEND_SAMPLE_RATE / CHUNK_SIZE * 0.5) # 0.5 seconds of pre-roll

        from collections import deque
        audio_buffer = deque(maxlen=PRE_ROLL_CHUNKS)
        
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

                # VAD Logic
                count = len(data) // 2
                if count > 0:
                    shorts = struct.unpack(f"<{count}h", data)
                    sum_squares = sum(s**2 for s in shorts)
                    rms = int(math.sqrt(sum_squares / count))
                else:
                    rms = 0
                
                # State Machine
                if rms > VAD_THRESHOLD:
                    # Speech Detected
                    self._silence_start_time = None
                    
                    if not self._is_speaking:
                        # NEW Speech Utterance Started
                        self._is_speaking = True

                        # Trigger Briefing if pending (First Interaction)
                        asyncio.create_task(self._trigger_morning_briefing_offer())

                        if INCLUDE_RAW_LOGS:
                            print(f"[ADA DEBUG] [VAD] Speech Detected (RMS: {rms}). Starting Stream.")
                        
                        # 1. Send Buffered Pre-roll (catch the start of the word)
                        while audio_buffer:
                             buffered_data = audio_buffer.popleft()
                             if self.out_queue:
                                 await self.out_queue.put({"data": buffered_data, "mime_type": "audio/pcm"})

                        # 2. Send Video Frame (Once per utterance)
                        if self._latest_image_payload and self.out_queue:
                            await self.out_queue.put(self._latest_image_payload)
                        else:
                            if INCLUDE_RAW_LOGS:
                                print(f"[ADA DEBUG] [VAD] No video frame available to send.")

                    # Send Current Chunk
                    if self.out_queue:
                        await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})
                            
                else:
                    # Silence Detected
                    if self._is_speaking:
                        # Hangover Period - continue sending until silence duration met
                        if self.out_queue:
                            await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})

                        if self._silence_start_time is None:
                            self._silence_start_time = time.time()
                        
                        elif time.time() - self._silence_start_time > SILENCE_DURATION:
                            # Silence confirmed, stop sending
                            if INCLUDE_RAW_LOGS:
                                print(f"[ADA DEBUG] [VAD] Silence timeout. Stopping Stream.")
                            self._is_speaking = False
                            self._silence_start_time = None
                    else:
                        # Not speaking, buffer audio for pre-roll
                        audio_buffer.append(data)
                        # DO NOT SEND TO QUEUE

            except Exception as e:
                if INCLUDE_RAW_LOGS:
                    print(f"Error reading audio: {e}")
                await asyncio.sleep(0.1)

    def _register_tools(self):
        """Registers all tools with the registry."""

        # Trello Tools
        for key in trello_tools:
            # Tool name in schema is 'trello_list_boards', method is 'list_boards'
            tool_name = trello_tools[key]['name']
            method_name = key
            self.tool_registry.register(tool_name, getattr(self.trello_agent, method_name))

        # Explicit Registrations
        self.tool_registry.register("generate_cad", self.handle_cad_request)
        self.tool_registry.register("run_web_agent", self.handle_web_agent_request)
        self.tool_registry.register("create_coding_task", self.handle_create_coding_task)
        self.tool_registry.register("run_jules_agent", self.handle_jules_request)
        self.tool_registry.register("run_openhands_agent", self.handle_openhands_request)
        self.tool_registry.register("run_ollama_agent", self.handle_ollama_request)
        self.tool_registry.register("send_jules_feedback", self.handle_jules_feedback)
        self.tool_registry.register("list_jules_sources", self.jules_agent.list_sources_formatted)
        self.tool_registry.register("list_jules_sessions", self.jules_agent.list_sessions_formatted)
        self.tool_registry.register("list_jules_activities", self.jules_agent.list_activities_formatted)
        self.tool_registry.register("create_project", lambda name: self._execute_project_switch(self.project_manager.create_project, name))
        self.tool_registry.register("switch_project", lambda name: self._execute_project_switch(self.project_manager.switch_project, name))
        self.tool_registry.register("list_projects", lambda: f"Available projects: {', '.join(self.project_manager.list_projects())}")
        self.tool_registry.register("list_smart_devices", self.kasa_agent.get_formatted_list)
        self.tool_registry.register("control_light", self.kasa_agent.control_device)
        self.tool_registry.register("discover_printers", self.printer_agent.get_formatted_discovery)
        self.tool_registry.register("print_stl", self.printer_agent.print_stl)
        self.tool_registry.register("get_print_status", self.printer_agent.get_formatted_status)
        self.tool_registry.register("iterate_cad", self.handle_iterate_cad)
        self.tool_registry.register("set_timer", self.timer_agent.set_timer)
        self.tool_registry.register("set_reminder", self.timer_agent.set_reminder)
        self.tool_registry.register("list_timers", self.timer_agent.list_timers)
        self.tool_registry.register("delete_entry", self.timer_agent.delete_entry)
        self.tool_registry.register("modify_timer", self.timer_agent.modify_timer)
        self.tool_registry.register("check_for_updates", self.update_agent.check_for_updates)
        self.tool_registry.register("apply_update", self.update_agent.apply_update)
        self.tool_registry.register("search_gifs", self.giphy_agent.search_gifs)
        self.tool_registry.register("display_content", self.handle_display_content)
        self.tool_registry.register("get_weather", self.weather_agent.get_weather)
        self.tool_registry.register("set_time_format", lambda format: self.project_manager.set_time_format(format)[1])
        self.tool_registry.register("get_datetime", lambda: f"The current date and time is {format_datetime(get_local_time(), self.project_manager.get_project_config().get('time_format', '12h'))}.")
        self.tool_registry.register("restart_application", lambda: asyncio.create_task(self.sio.emit("initiate_restart")) and "Restart signal sent to frontend." if self.sio else "Cannot send restart signal: not connected to server.")
        self.tool_registry.register("search", self.search_agent.search)
        self.tool_registry.register("proactive_suggestion", lambda suggestion: self.on_display_content({"content_type": "suggestion", "suggestion": suggestion}) and "Suggestion displayed." if self.on_display_content else "No display content handler registered.")

        if self.slack_agent:
            self.tool_registry.register("send_slack_message", self.slack_agent.send_message)

        self.tool_registry.register("append_system_prompt", lambda text: self._execute_project_action(self.project_manager.append_system_prompt, False, text))
        self.tool_registry.register("delete_custom_system_prompt", lambda: self._execute_project_action(self.project_manager.reset_system_prompt, False))
        self.tool_registry.register("get_system_prompt", lambda: self.project_manager.get_system_prompt())
        self.tool_registry.register("toggle_jules_slack_notifications", lambda enabled: f"Slack notifications {'enabled' if enabled else 'disabled'}." if self.project_manager.update_project_config({"jules_slack_notifications": enabled})[0] else "Failed.")
        async def deliver_briefing_wrapper(force_refresh=False):
            if self.automation_engine:
                return await self.automation_engine.deliver_morning_briefing(force_refresh)
            return "Automation engine not running."
        self.tool_registry.register("get_morning_briefing", deliver_briefing_wrapper)
        self.tool_registry.register("spawn_swarm_agent", self.handle_spawn_swarm_agent)
        self.tool_registry.register("create_swarm_mission", self.handle_create_swarm_mission)
        self.tool_registry.register("control_os", self.os_agent.control)

        # Novel Writing Mode Tools
        self.tool_registry.register("commit_novel_changes", self.writing_agent.commit_novel_changes)
        self.tool_registry.register("seed", self.writing_agent.seed)
        self.tool_registry.register("gen_world", self.writing_agent.gen_world)
        self.tool_registry.register("gen_characters", self.writing_agent.gen_characters)
        self.tool_registry.register("gen_outline", self.writing_agent.gen_outline)
        self.tool_registry.register("gen_outline_part2", self.writing_agent.gen_outline_part2)
        self.tool_registry.register("gen_canon", self.writing_agent.gen_canon)
        self.tool_registry.register("voice_fingerprint", self.writing_agent.voice_fingerprint)
        self.tool_registry.register("draft_chapter", self.writing_agent.draft_chapter)
        self.tool_registry.register("run_drafts", self.writing_agent.run_drafts)
        self.tool_registry.register("evaluate", self.writing_agent.evaluate)
        self.tool_registry.register("adversarial_edit", self.writing_agent.adversarial_edit)
        self.tool_registry.register("compare_chapters", self.writing_agent.compare_chapters)
        self.tool_registry.register("reader_panel", self.writing_agent.reader_panel)
        self.tool_registry.register("review", self.writing_agent.review)
        self.tool_registry.register("gen_brief", self.writing_agent.gen_brief)
        self.tool_registry.register("gen_revision", self.writing_agent.gen_revision)
        self.tool_registry.register("apply_cuts", self.writing_agent.apply_cuts)
        self.tool_registry.register("gen_art", self.writing_agent.gen_art)
        self.tool_registry.register("gen_art_directions", self.writing_agent.gen_art_directions)
        self.tool_registry.register("gen_cover_composite", self.writing_agent.gen_cover_composite)
        self.tool_registry.register("gen_cover_print", self.writing_agent.gen_cover_print)
        self.tool_registry.register("gen_audiobook_script", self.writing_agent.gen_audiobook_script)
        self.tool_registry.register("gen_audiobook", self.writing_agent.gen_audiobook)
        self.tool_registry.register("run_pipeline", self.writing_agent.run_pipeline)
        self.tool_registry.register("build_arc_summary", self.writing_agent.build_arc_summary)
        self.tool_registry.register("build_outline", self.writing_agent.build_outline)
        self.tool_registry.register("build_tex", self.writing_agent.build_tex)

        self.tool_registry.register("set_auto_merge_threshold", lambda hours: f"Auto-merge threshold set to {hours} hours." if self.project_manager.update_project_config({"auto_merge_threshold": int(hours * 3600)})[0] else "Failed.")
        self.tool_registry.register("add_architectural_memory", lambda content, tags=None: self.project_manager.add_architectural_memory(content, tags)[1])
        self.tool_registry.register("switch_video_source", lambda source: setattr(self, "video_mode", source) or f"Switched video source to {source}." if source in ["camera", "screen"] else f"Invalid source '{source}'. Use 'camera' or 'screen'.")
        self.tool_registry.register("apply_task_fix", lambda task_id: self.automation_engine.apply_fix(task_id)[1] if self.automation_engine else "Automation Engine not available.")
        self.tool_registry.register("dismiss_jules_session", self.jules_agent.dismiss_session)
        self.tool_registry.register("jules_get_diff", self.jules_agent.get_diff_formatted)

        # Tools returning simple strings from simple project interactions

        self.tool_registry.register("assign_agent_to_repo", self.handle_assign_agent)
        self.tool_registry.register("add_task_to_repo_queue", self.handle_add_task)
        self.tool_registry.register("clear_completed_fleet_tasks", self.handle_clear_completed_tasks)
        self.tool_registry.register("display_dashboard", self.handle_display_dashboard)
        self.tool_registry.register("change_voice", lambda voice_name: self._execute_project_action(self.project_manager.set_voice, False, voice_name))
        self.tool_registry.register("update_persona", lambda persona: self._execute_project_action(self.project_manager.update_persona, False, persona))

        # File System Agent Tools
        self.tool_registry.register("write_file", self.fs_agent.write_file)
        self.tool_registry.register("read_directory", self.fs_agent.read_directory)
        self.tool_registry.register("read_file", self.fs_agent.read_file)

        # Git Agent Tools
        self.tool_registry.register("git_merge_branch", self.git_agent.merge)
        self.tool_registry.register("git_commit", self.git_agent.commit)
        self.tool_registry.register("git_push", self.git_agent.push)
        self.tool_registry.register("git_pull", self.git_agent.pull)
        self.tool_registry.register("git_list_repos", self.git_agent.list_repos)
        self.tool_registry.register("git_list_branches", self.git_agent.list_branches)
        self.tool_registry.register("git_status", self.git_agent.status)
        self.tool_registry.register("git_fleet_status", self.git_agent.fleet_status)
        self.tool_registry.register("sync_git_repos", self.git_agent.sync_fleet)
        self.tool_registry.register("merge_pull_request", self.git_agent.merge_pull_request)

        # Music Agent Tools
        self.tool_registry.register("play_music", self.music_agent.play)
        self.tool_registry.register("control_music", self.music_agent.control)
        self.tool_registry.register("create_playlist", self.music_agent.create_playlist)

    # --- Wrapper Methods for Async Tasks (to return immediate response) ---
    async def handle_cad_request(self, prompt):
        if INCLUDE_RAW_LOGS:
             print(f"[ADA DEBUG] [TOOL] Tool Call Detected: 'generate_cad', prompt='{prompt}'")
        asyncio.create_task(self._run_cad_generation_task(prompt))
        return "CAD Generation started."

    async def handle_web_agent_request(self, prompt):
        if INCLUDE_RAW_LOGS:
             print(f"[ADA DEBUG] [TOOL] Tool Call: 'run_web_agent' with prompt='{prompt}'")
        asyncio.create_task(self._run_web_agent_task(prompt))
        return "Web Navigation started. Do not reply to this message."

    # --- New Handler Methods ---

    async def handle_create_coding_task(self, prompt, source=None):
        """Initiates a coding task by pausing to ask the user which agent to use."""
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [ROUTING] 'create_coding_task' called. Prompt: '{prompt}'")

        self._pending_coding_task_prompt = prompt
        self._pending_coding_task_source = source

        # Instruct the model to immediately ask the user to choose
        msg = "System Notification: Please ask the user exactly this question: 'Would you like to use OpenHands or Jules for this coding task?' and then immediately display a select window with those two options. Do not do anything else until they respond."

        if self.on_display_content:
            self.on_display_content({
                "content_type": "widget",
                "widget_type": "select",
                "data": {
                    "options": ["OpenHands", "Jules"]
                }
            })

        try:
            await self.session.send(input=msg, end_of_turn=True)
        except Exception as e:
            if INCLUDE_RAW_LOGS:
                print(f"[ADA DEBUG] [ERR] Failed to send routing prompt: {e}")

        return "Waiting for user to choose the agent."

    async def handle_openhands_request(self, prompt, repo_path=None):
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [OPENHANDS] Task: '{prompt}' (Repo: {repo_path})")

        # Start the agent
        session = await self.openhands_agent.spawn_agent(prompt, repo_path)

        if session:
            msg = f"System Notification: Local OpenHands agent started with ID '{session.get('conversation_id')}'. I will notify you when it completes."
        else:
            msg = "System Notification: Failed to start OpenHands agent."

        try:
            await self.session.send(input=msg, end_of_turn=True)
        except Exception as e:
            if INCLUDE_RAW_LOGS:
                print(f"[ADA DEBUG] [ERR] Failed to send OpenHands notification: {e}")

        return f"Agent started. ID: {session.get('conversation_id') if session else 'Failed'}"


    async def handle_spawn_swarm_agent(self, role, prompt, source=None, swarm_id=None):
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [TOOL] Tool Call: 'spawn_swarm_agent'")

        # Prepend role to prompt for context, but also pass role explicitly
        full_prompt = f"Role: {role}\nTask: {prompt}"

        async def _on_created(sid):
            if swarm_id:
                success, msg = self.project_manager.add_session_to_swarm(swarm_id, sid)
                if INCLUDE_RAW_LOGS:
                    print(f"[ADA DEBUG] [SWARM] Added session {sid} to swarm {swarm_id}: {msg}")

                if self.sio:
                    swarms = self.project_manager.get_swarms()
                    await self.sio.emit('swarms_update', swarms)

        result = await self.handle_jules_request(full_prompt, source, role=role, on_session_created=_on_created)
        return result

    def _execute_project_action(self, action_func, notify_name=False, *args):
        """Consolidates wrapper logic for project settings that require a reconnect."""
        success, msg = action_func(*args)
        if success:
            if notify_name and self.on_project_update and args:
                self.on_project_update(args[0])
            self.reconnect()
        return msg

    def _execute_project_switch(self, action_func, name):
        success, msg = action_func(name)
        if success:
            if action_func.__name__ == 'create_project':
                self.project_manager.switch_project(name)
                msg += f" Switched to '{name}'."

            self.printer_agent.set_root_path(self.project_manager.get_current_project_path())
            if self.on_project_update:
                self.on_project_update(name)
            self.reconnect()
        return msg



    async def handle_iterate_cad(self, prompt):
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
        return result_str

    async def _run_cad_generation_task(self, prompt):
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [CAD] Background Task Started: _run_cad_generation_task('{prompt}')")
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


    async def _run_web_agent_task(self, prompt):
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [WEB] Background Task Started: _run_web_agent_task('{prompt}')")
        
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

    async def handle_create_swarm_mission(self, title):
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [SWARM] Creating mission: '{title}'")
        swarm_id, msg = self.project_manager.create_swarm(title)

        if self.sio:
             swarms = self.project_manager.get_swarms()
             await self.sio.emit('swarms_update', swarms)

        return f"{msg} (ID: {swarm_id})"

    async def handle_ollama_request(self, prompt, source=None, role=None, model="llama3"):
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [OLLAMA] Task: '{prompt}' (Model: {model}, Source: {source})")

        # Start the agent
        session = await self.ollama_agent.spawn_agent(prompt, source, role, model)

        # Notify
        msg = f"System Notification: Local Ollama agent started with ID '{session['id']}'. I will notify you when it completes."
        try:
            await self.session.send(input=msg, end_of_turn=True)
        except Exception as e:
            if INCLUDE_RAW_LOGS:
                print(f"[ADA DEBUG] [ERR] Failed to send ollama notification: {e}")

        return f"Agent started. ID: {session['id']}"

    async def handle_jules_request(self, prompt, source=None, role=None, on_session_created=None):
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [JULES] Jules Agent Task: '{prompt}' (Role: {role})")

        is_force_restart = False
        if prompt.startswith("FORCE_RESTART:"):
            is_force_restart = True
            prompt = prompt.replace("FORCE_RESTART:", "", 1).strip()

        # We use the persistent instance self.jules_agent instead of creating a new one
        # to ensure centralized management of polling tasks.

        if not is_force_restart:
            clean_title_prompt = prompt.replace('\n', ' ').replace('\r', ' ').strip()[:40] # Jules truncates to 50, but let's be safe

            try:
                existing_sessions = await self.jules_agent.list_sessions()
                for session in existing_sessions:
                    s_title = session.get('title', '')
                    if not s_title:
                        continue
                    if clean_title_prompt in s_title or s_title in clean_title_prompt:
                        matching_title = s_title
                        if INCLUDE_RAW_LOGS:
                            print(f"[ADA DEBUG] [JULES] Found potential duplicate session: {matching_title}")

                        msg = f"System Notification: A similar Jules task '{matching_title}' already exists. Please ask the user if they want to restart it. If they approve, run the task again but prepend 'FORCE_RESTART:' to the prompt."
                        try:
                            await self.session.send(input=msg, end_of_turn=True)
                        except Exception as e:
                            if INCLUDE_RAW_LOGS:
                                print(f"[ADA DEBUG] [ERR] Failed to send duplicate task notification: {e}")
                        return "Duplicate task detected. Asking user for permission."
            except Exception as e:
                if INCLUDE_RAW_LOGS:
                    print(f"[ADA DEBUG] [WARN] Failed to check for duplicate sessions: {e}")

        if not source:
            if INCLUDE_RAW_LOGS:
                print("[ADA DEBUG] [JULES] No source provided, fetching available sources.")
            
            async def fetch_sources_and_notify():
                sources_response = await self.jules_agent.list_sources()
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

        async def _jules_update_callback(message):
            """Callback for when Jules sends an update."""
            if self.session:
                 try:
                    # Add a timeout to the send operation
                    await asyncio.wait_for(
                        self.session.send(input=f"System Notification: {message}", end_of_turn=False),
                        timeout=10.0
                    )
                 except Exception as e:
                    if INCLUDE_RAW_LOGS:
                        print(f"[ADA DEBUG] [ERR] Failed to send Jules update to model: {e}")

        async def run_jules_task():
            # Spawn the agent using the new enhanced method which handles RAG
            session = await self.jules_agent.spawn_agent_with_context(prompt, source, role=role, callback=_jules_update_callback)

            if session:
                session_id = session['name']
                if INCLUDE_RAW_LOGS:
                    print(f"[ADA DEBUG] [JULES] Session created: {session_id}")

                if on_session_created:
                    if asyncio.iscoroutinefunction(on_session_created):
                        await on_session_created(session_id)
                    else:
                        on_session_created(session_id)

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
        
        # Check if it's an Ollama session
        if session_id in self.ollama_agent.sessions:
            return await self.ollama_agent.send_message(session_id, feedback)

        # Use the existing agent instance
        async def _jules_update_callback(message):
            if self.session:
                 try:
                    await self.session.send(input=f"System Notification: {message}", end_of_turn=False)
                 except Exception:
                    pass

        # Ensure we are polling this session (if not already)
        if session_id not in self.jules_agent.polling_tasks:
            if INCLUDE_RAW_LOGS:
                print(f"[ADA DEBUG] [JULES] Starting polling for existing session: {session_id}")
            self.jules_agent.start_polling(session_id, callback=_jules_update_callback, interceptor_callback=self._handle_jules_triage)

        response = await self.jules_agent.send_message(session_id, feedback)
        if response:
            return "Feedback sent successfully."
        else:
            return "Failed to send feedback."


    async def handle_focused_session(self, session_id):
        """Notifies the model that the user is focusing on a specific session."""
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [FOCUS] User focused session: {session_id}")

        # Fetch summary context
        activities = await self.jules_agent.list_activities(session_id)
        summary = "No recent activity."
        # activities is a dict {"activities": [...]}, but list_activities_formatted returns string.
        # Ideally we want raw list here to summarize.
        # list_activities returns dict.

        acts_list = []
        if isinstance(activities, dict) and "activities" in activities:
            acts_list = activities["activities"]
        elif isinstance(activities, list):
            acts_list = activities

        if acts_list:
            # Get last 3 activities
            recent = acts_list[-3:]
            summary_lines = []
            for act in recent:
                if 'agentMessage' in act:
                    summary_lines.append(f"Jules: {act['agentMessage']['content'][:100]}...")
                elif 'userMessage' in act:
                    summary_lines.append(f"User: {act['userMessage']['content'][:100]}...")
            summary = "\n".join(summary_lines)

        msg = (
            f"System Notification: The user has opened the detailed view for Jules Session '{session_id}'.\n"
            f"Context (Recent Activity):\n{summary}\n\n"
            f"The user is now looking at this session. If they speak, assume it might be feedback or instructions for this specific session. "
            f"Use the 'send_jules_feedback' tool if appropriate."
        )

        if self.session:
            try:
                await self.session.send(input=msg, end_of_turn=True)
            except Exception as e:
                print(f"[ADA DEBUG] Failed to send focus notification: {e}")

    async def handle_clear_focused_session(self):
        """Notifies the model that the user has closed the specific session view."""
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [FOCUS] User cleared focus.")

        msg = "System Notification: The user has closed the Jules Session detail view. You are back to general context."

        if self.session:
            try:
                await self.session.send(input=msg, end_of_turn=True)
            except Exception as e:
                print(f"[ADA DEBUG] Failed to send clear focus notification: {e}")

    async def get_dashboard_data(self):
        """Gathers all data for the War Room Dashboard."""
        if INCLUDE_RAW_LOGS:
            print("[ADA DEBUG] [DASHBOARD] Gathering data for War Room...")

        # 1. Project Info
        project = self.project_manager.current_project

        # 2. Jules Data (Fetch early for stats)
        jules_sessions = await self.jules_agent.list_sessions()
        ollama_sessions = await self.ollama_agent.list_sessions()

        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [DASHBOARD] Jules sessions: {len(jules_sessions)}, Ollama sessions: {len(ollama_sessions)}")

        # 3. System Stats (REPLACED WITH AGENT STATS)
        # Calculate stats from both sources
        all_sessions = jules_sessions + ollama_sessions
        total_sessions = len(all_sessions)

        # Jules states are uppercase, Ollama states are uppercase
        active_states = ['RUNNING', 'PENDING', 'IN_PROGRESS']
        failed_states = ['FAILED', 'ERROR']
        completed_states = ['COMPLETED', 'DONE']

        active_sessions_count = len([s for s in all_sessions if s.get('state') in active_states or s.get('state') not in (completed_states + failed_states)])
        completed_sessions_count = len([s for s in all_sessions if s.get('state') in completed_states])

        system_stats = {
            "total_agents": total_sessions,
            "active_agents": active_sessions_count,
            "completed_agents": completed_sessions_count,
            "success_rate": int((completed_sessions_count / total_sessions * 100)) if total_sessions > 0 else 0
        }

        # 4. Tasks (Worker Nodes)
        tasks = self.task_manager.list_tasks()

        # 5. Trello Data (Active Cards)
        trello_cards = []
        try:
            # Attempt to get the first board and its cards
            boards = await self.trello_agent.list_boards()
            if boards:
                board_id = boards[0]['id']
                lists = await self.trello_agent.list_lists(board_id)
                active_list_ids = {l['id']: l['name'] for l in lists if 'done' not in l['name'].lower()}

                tasks_coros = [self.trello_agent.list_cards(lid) for lid in active_list_ids.keys()]
                results = await asyncio.gather(*tasks_coros, return_exceptions=True)

                for i, res in enumerate(results):
                    if isinstance(res, list):
                        lid = list(active_list_ids.keys())[i]
                        lname = active_list_ids[lid]
                        for card in res:
                            trello_cards.append({
                                "name": card['name'],
                                "idShort": card['idShort'],
                                "listName": lname
                            })
        except Exception as e:
             if INCLUDE_RAW_LOGS:
                print(f"[ADA DEBUG] [ERR] Failed to fetch Trello data: {e}")

        # 6. Jules Data Enrichment
        enriched_sessions = []
        now = time.time()

        # Efficiently manage local state
        all_states = self.project_manager.get_all_jules_session_states()
        new_session_ids = []

        # Identify new sessions (Jules only for persistent tracking, but we treat Ollama as ephemeral for now or same?)
        # Let's track Ollama sessions too if they have IDs
        for s in all_sessions:
            s_id = s.get('name') or s.get('id')
            if not s_id: continue

            if s_id not in all_states or "seen_at" not in all_states[s_id]:
                new_session_ids.append(s_id)

        # Batch update new sessions
        if new_session_ids:
            self.project_manager.batch_mark_jules_sessions_seen(new_session_ids)
            for nid in new_session_ids:
                if nid not in all_states: all_states[nid] = {}
                all_states[nid]["seen_at"] = now

        for s in all_sessions:
            s_id = s.get('name') or s.get('id')
            if not s_id: continue

            s_state = s.get('state', 'UNKNOWN')
            s_title = s.get('title', 'Untitled')

            # Local State Check (Dismissal / Seen)
            ui_state = all_states.get(s_id, {})
            if ui_state.get('dismissed'):
                continue

            seen_at = ui_state.get('seen_at', now)

            # Auto-Archive Logic for Completed Sessions
            if s_state in ['COMPLETED', 'FAILED']:
                completion_time_str = s.get('updateTime') or s.get('createTime')
                is_old = False
                if completion_time_str:
                    try:
                        if completion_time_str.endswith('Z'):
                             completion_time_str = completion_time_str[:-1] + '+00:00'
                        dt = datetime.fromisoformat(completion_time_str)
                        completion_ts = dt.timestamp()
                        if (now - completion_ts) > (2 * 3600):
                            is_old = True
                    except Exception as e:
                        pass

                if is_old:
                    if (now - seen_at) > 300:
                        continue

            # Determine source for insight
            if s in ollama_sessions:
                insight = self.ollama_agent.get_session_insight(s_id)
                agent_type = "ollama"
            else:
                insight = self.jules_agent.get_session_insight(s_id)
                agent_type = "jules"

            enriched_sessions.append({
                "id": s_id,
                "title": s_title,
                "state": s_state,
                "latest_thought": insight,
                "type": agent_type
            })

        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [DASHBOARD] Enriched sessions: {len(enriched_sessions)}")

        # 6. Device Data
        devices = []
        for ip, d in self.kasa_agent.devices.items():
             devices.append({
                 "alias": d.alias,
                 "is_on": d.is_on
             })

        # 7. Printer Data
        printers = []
        if self.printer_agent:
            for host, p in self.printer_agent.printers.items():
                status = await self.printer_agent.get_print_status(host)
                p_data = {
                    "name": p.name,
                    "state": status.state if status else "OFFLINE",
                    "temp": status.temperatures.get('hotend', {}).get('current', 0) if status and status.temperatures else 0,
                    "progress": status.progress_percent if status else 0
                }
                printers.append(p_data)

        # 8. Git Ops Data
        repo_path = self.project_manager.get_current_project_path()
        git_status = {
            "branch": await self.git_agent.get_current_branch(repo_path) or "unknown",
            "branches": await self.git_agent.get_branches_list(repo_path),
            "status": await self.git_agent.get_status_raw(repo_path)
        }

        return {
            "project": project,
            "system_status": "ONLINE",
            "system_stats": system_stats,
            "tasks": tasks,
            "trello": trello_cards[:10],
            "jules": enriched_sessions[:5],
            "devices": devices,
            "printers": printers,
            "git": git_status
        }



    async def handle_assign_agent(self, agent_id, repo_name):
        from backend.server import fleet_manager, sio
        if fleet_manager.assign_agent(agent_id, repo_name):
            await sio.emit('fleet_state_update', fleet_manager.get_state())
            return f"Assigned {agent_id} to {repo_name}."
        return f"Failed to assign {agent_id}. Agent may not exist."

    async def handle_add_task(self, repo_name, prompt, depends_on=None, attachments=None):
        from backend.server import fleet_manager, sio, check_and_start_next_task
        task_id = fleet_manager.add_task_to_queue(repo_name, prompt, depends_on, attachments or [])
        await sio.emit('fleet_state_update', fleet_manager.get_state())
        await check_and_start_next_task(repo_name)
        return f"Task '{task_id}' added to {repo_name} queue."

    async def handle_clear_completed_tasks(self, repo_name):
        from backend.server import fleet_manager, sio
        fleet_manager.clear_completed_tasks(repo_name)
        await sio.emit('fleet_state_update', fleet_manager.get_state())
        return f"Cleared all completed tasks for {repo_name}."

    async def handle_display_dashboard(self):
        dashboard_data = await self.get_dashboard_data()
        return await self.handle_display_content("widget", widget_type="dashboard", data=dashboard_data)

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

**War Room / Dashboard:**
If the user asks for a "status report", "situation report", "war room", or "dashboard", use the `display_dashboard` tool immediately. This tool aggregates all project, device, and agent status into a single visual view.

**Select Options Window:**
If you need to ask the user to choose between options (e.g. which agent to use, or confirming an action with options), you should display a select window using the `display_content` tool with `content_type='widget'`, `widget_type='select'`, and `data={'options': ['Option 1', 'Option 2']}`. This will pop up a window for the user to make a selection.

**Vision Capabilities (VLA):**
You have access to a real-time video feed of the user and their environment.
- You can see objects, text, and gestures.
- If the user asks "what is this?" or shows you something, use the video feed to answer.
- You do NOT need to ask for permission to see; you are already looking.

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

        # Swarm Mode Instructions
        swarm_prompt = """
**Swarm Mode (Multi-Agent Orchestration):**
When the user asks you to perform a complex, multi-faceted task (e.g., "Refactor the authentication system", "Build a new feature from scratch"), do NOT try to do it all yourself in a single session.
1.  **Analyze** the request and break it down into sub-tasks (e.g., Frontend, Backend, Database, QA).
2.  **Deploy** a "Swarm" of specialized agents using the `spawn_swarm_agent` tool.
    - Call `spawn_swarm_agent` multiple times, once for each sub-task.
    - Assign a specific `role` to each agent (e.g., "Frontend Engineer", "Security Specialist").
    - Give each agent a specific `prompt` relevant to their role.
3.  **Inform** the user: "I am deploying a swarm to handle this. I have assigned a Frontend Engineer and a Backend Specialist to the task."
"""

        # Music Playback Behavior Prompt
        music_prompt = """
**Music Playback Behavior:**
When music is playing (e.g., after you call `play_music` or resume it), you MUST alter your communication style to avoid talking over the track:
- DO NOT use voice for simple tool executions or acknowledgments.
- Only respond with voice if it is absolutely critical.
- For simple responses or acknowledgments, you should find a GIF using the `search_gifs` tool, and then display it using `display_content(content_type='image', url=<gif_url>)` instead of speaking.
- Once music is paused or stopped, you may resume normal voice communication.
"""

        # Combine prompts
        system_prompt = f"{personality_prompt}\n{tool_prompt}\n{swarm_prompt}\n{music_prompt}"

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
                spoken_response_for_slack = ""
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
                                    self.audio_in_queue.put(part.inline_data.data)

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
                                        # Handle Intercept for Routing
                                        if getattr(self, "_pending_coding_task_prompt", None):
                                            lower_transcript = transcript.lower()
                                            if "openhands" in lower_transcript or "open hands" in lower_transcript:
                                                if INCLUDE_RAW_LOGS:
                                                    print("[ADA DEBUG] [ROUTING] Intercepted 'openhands'.")
                                                p = self._pending_coding_task_prompt
                                                s = self._pending_coding_task_source
                                                self._pending_coding_task_prompt = None
                                                self._pending_coding_task_source = None
                                                asyncio.create_task(self.handle_openhands_request(p, repo_path=s))
                                                # Tell the model the user chose OpenHands
                                                try:
                                                    await self.session.send(input="System Notification: The user chose OpenHands. The task has been routed.", end_of_turn=True)
                                                except Exception:
                                                    pass

                                            elif "jules" in lower_transcript:
                                                if INCLUDE_RAW_LOGS:
                                                    print("[ADA DEBUG] [ROUTING] Intercepted 'jules'.")
                                                p = self._pending_coding_task_prompt
                                                s = self._pending_coding_task_source
                                                self._pending_coding_task_prompt = None
                                                self._pending_coding_task_source = None
                                                asyncio.create_task(self.handle_jules_request(p, source=s))
                                                # Tell the model the user chose Jules
                                                try:
                                                    await self.session.send(input="System Notification: The user chose Jules. The task has been routed.", end_of_turn=True)
                                                except Exception:
                                                    pass

                                        # User is speaking, so interrupt model playback!
                                        self.clear_audio_queue()
                                        self.set_last_input_source('ui')

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
                                        spoken_response_for_slack += delta
                        
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

                            # --- Tool Registry Dispatch ---

                            # Confirmation Logic
                            confirmed = True
                            requires_confirmation = self.tool_registry.is_confirmation_required(fc.name)
                            if hasattr(self, 'tool_permissions') and fc.name in self.tool_permissions:
                                requires_confirmation = self.tool_permissions[fc.name]

                            if fc.name == "merge_pull_request":
                                from backend.server import SETTINGS
                                if SETTINGS.get("auto_merge_master", False):
                                    requires_confirmation = False

                            if requires_confirmation:
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

                            # Execute Tool via Registry
                            result = await self.tool_registry.dispatch(fc.name, fc.args)

                            # Construct Response
                            function_response = types.FunctionResponse(
                                id=fc.id,
                                name=fc.name,
                                response={"result": result}
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
                if self.last_input_source == 'slack' and spoken_response_for_slack:
                    if self.slack_agent:
                        asyncio.create_task(self.slack_agent.send_message(spoken_response_for_slack))
                self.set_last_input_source('ui')

                while not self.audio_in_queue.empty():
                    self.audio_in_queue.get_nowait()
        except Exception as e:
            import websockets.exceptions
            if "1011" in str(e) or "1008" in str(e) or "CANCELLED" in str(e).upper() or isinstance(e, websockets.exceptions.ConnectionClosedError):
                if INCLUDE_RAW_LOGS:
                    print(f"[ADA DEBUG] [WARN] Transient Session Error in receive_audio: {e}")
            else:
                if INCLUDE_RAW_LOGS:
                    print(f"Error in receive_audio: {e}")
                traceback.print_exc()
            # CRITICAL: Re-raise to crash the TaskGroup and trigger outer loop reconnect
            raise e

    def play_audio(self):
        stream = None
        if pya:
            try:
                stream = pya.open(
                    format=FORMAT,
                    channels=CHANNELS,
                    rate=RECEIVE_SAMPLE_RATE,
                    output=True,
                    output_device_index=self.output_device_index,
                )
            except Exception as e:
                if INCLUDE_RAW_LOGS:
                    print(f"[ADA] [ERR] Failed to open audio output stream: {e}")
                stream = None
        else:
            if INCLUDE_RAW_LOGS:
                print("[ADA] PyAudio not available. Audio output will only be sent to frontend.")

        import struct
        last_voice_time = 0
        DUCK_DURATION = 1.0 # Keep ducking for 1 sec after voice stops
        DUCK_VOLUME = 0.15 # 85% reduction

        v_buffer = bytearray()
        m_buffer = bytearray()
        import audioop
        import time

        while not self.stop_event.is_set():
            try:
                # 1. Fill buffers from queues
                try:
                    while True:
                        v_buffer.extend(self.audio_in_queue.get_nowait())
                except queue.Empty:
                    pass

                is_paused = getattr(self, "music_agent", None) and getattr(self.music_agent, "paused", False)

                if is_paused:
                    m_buffer.clear()
                    try:
                        while True:
                            self.music_queue.get_nowait()
                    except queue.Empty:
                        pass
                else:
                    try:
                        while True:
                            m_data = self.music_queue.get_nowait()
                            m_buffer.extend(m_data)
                    except queue.Empty:
                        pass

                # If both buffers are empty, wait a bit
                if not v_buffer and not m_buffer:
                    try:
                        v_data = self.audio_in_queue.get(timeout=0.05)
                        v_buffer.extend(v_data)
                    except queue.Empty:
                        if not is_paused:
                            try:
                                m_data = self.music_queue.get(timeout=0.05)
                                m_buffer.extend(m_data)
                            except queue.Empty:
                                pass

                now = time.time()
                if v_buffer:
                    last_voice_time = now

                should_duck = (now - last_voice_time) < DUCK_DURATION

                # 2. Mix and flush buffers
                mixed_data = b""
                MAX_CHUNK_SIZE = 4096

                if v_buffer and m_buffer:
                    min_len = min(len(v_buffer), len(m_buffer), MAX_CHUNK_SIZE)
                    min_len = (min_len // 2) * 2 # 16-bit align

                    if min_len > 0:
                        v_chunk = bytes(v_buffer[:min_len])
                        m_chunk = bytes(m_buffer[:min_len])

                        # Remove processed data from buffers
                        del v_buffer[:min_len]
                        del m_buffer[:min_len]

                        if should_duck:
                            m_chunk = audioop.mul(m_chunk, 2, DUCK_VOLUME)

                        mixed_data = audioop.add(v_chunk, m_chunk, 2)

                elif v_buffer:
                    v_len = min(len(v_buffer), MAX_CHUNK_SIZE)
                    v_len = (v_len // 2) * 2
                    if v_len > 0:
                        mixed_data = bytes(v_buffer[:v_len])
                        del v_buffer[:v_len]
                elif m_buffer:
                    m_len = min(len(m_buffer), MAX_CHUNK_SIZE)
                    m_len = (m_len // 2) * 2
                    if m_len > 0:
                        m_chunk = bytes(m_buffer[:m_len])
                        del m_buffer[:m_len]

                        if should_duck:
                            mixed_data = audioop.mul(m_chunk, 2, DUCK_VOLUME)
                        else:
                            mixed_data = m_chunk

                if mixed_data:
                    # Always send to frontend
                    if self.on_audio_data:
                        self.on_audio_data(mixed_data)

                    # Play locally if stream is available
                    if stream:
                        stream.write(mixed_data)

            except Exception as e:
                if INCLUDE_RAW_LOGS:
                    print(f"[ADA] [ERR] Error in play_audio loop: {e}")

    async def video_loop(self):
        cap = None

        while not self.stop_event.is_set():
            if self.paused:
                await asyncio.sleep(0.1)
                continue

            frame = None
            if self.video_mode == "camera":
                if cap is None or not cap.isOpened():
                     cap = await asyncio.to_thread(cv2.VideoCapture, 0)

                # Manual capture to support face detection on raw frame
                ret, raw_frame = await asyncio.to_thread(cap.read)
                if ret:
                     # Face Detect (Presence)
                     if self.face_cascade:
                         now = time.time()
                         if now - self._last_face_check_time > 1.0:
                             self._last_face_check_time = now
                             try:
                                 gray = cv2.cvtColor(raw_frame, cv2.COLOR_BGR2GRAY)
                                 # Detect faces
                                 faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
                                 if len(faces) > 0:
                                     await self._trigger_morning_briefing_offer()
                             except Exception as e:
                                 if INCLUDE_RAW_LOGS:
                                     print(f"[ADA DEBUG] [WARN] Face detection error: {e}")

                     frame = self._process_frame(raw_frame)
                else:
                     frame = None

            elif self.video_mode == "screen":
                if cap and cap.isOpened():
                    cap.release()
                    cap = None

                try:
                    frame = await asyncio.to_thread(self._get_screen_sync)
                except Exception as e:
                    if INCLUDE_RAW_LOGS:
                        print(f"[ADA DEBUG] [ERR] Screen capture failed: {e}")

            else:
                 # None or unknown
                 if cap: cap.release(); cap = None
                 await asyncio.sleep(1)
                 continue

            if frame:
                self._latest_image_payload = frame
                if self.out_queue:
                    await self.out_queue.put(frame)

            await asyncio.sleep(1.0)

        if cap: cap.release()

    def _get_screen_sync(self):
        if self.sct is None:
            self.sct = mss.mss()

        if len(self.sct.monitors) > 1:
            monitor = self.sct.monitors[1]  # Capture primary monitor
        else:
            monitor = self.sct.monitors[0]  # Fallback to all/virtual monitor

        sct_img = self.sct.grab(monitor)

        # Optimized Path: Use OpenCV directly on buffer
        # mss returns BGRA. Convert to BGR -> Process
        img_np = np.array(sct_img, copy=False)

        # Drop Alpha (BGRA -> BGR)
        frame_bgr = cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)

        return self._process_frame(frame_bgr)

    def close(self):
        if self.sct:
            try:
                self.sct.close()
            except Exception as e:
                if INCLUDE_RAW_LOGS:
                    print(f"[ADA DEBUG] [ERR] Failed to close MSS: {e}")
            self.sct = None


    def notify_user(self, text, duration=10000, send_voice=True, send_slack=True):
        """Consolidated method to dispatch system notifications across UI, Voice, and Slack."""
        if INCLUDE_RAW_LOGS:
            print(f"[ADA DEBUG] [NOTIFY] {text}")

        # UI
        if self.on_display_content:
            self.on_display_content({
                "content_type": "notification",
                "data": {"text": text},
                "duration": duration
            })

        # Voice
        if send_voice and self.session:
            asyncio.create_task(self.session.send(input=f"System Notification: {text}", end_of_turn=False))

        # Slack
        if send_slack and self.slack_agent and self.project_manager.get_project_config().get("jules_slack_notifications", False):
            asyncio.create_task(self.slack_agent.send_message(text))

    async def handle_external_event(self, event):
        """Handles external events (like Git commits) triggered by AutomationEngine."""
        if event['type'] == 'git_commit':
            msg = f"New commit in {event['repo']} by {event['author']}: {event['message']}"
            self.notify_user(msg)
        elif event['type'] == 'git_pr':
            msg = f"New pull request in {event['repo']} by {event['author']}: {event['title']}"
            self.notify_user(msg)
        elif event['type'] == 'trello_move':
            msg = f"New card '{event.get('card_name')}' added to Trello list '{event.get('list_name')}' in board '{event.get('board_name')}'."
            self.notify_user(msg)
        elif event['type'] == 'notification':
            msg = event.get('message', 'No message provided.')
            self.notify_user(msg)

    def _process_frame(self, frame_bgr):
        """Resizes and encodes a BGR frame to JPEG."""
        h, w = frame_bgr.shape[:2]
        max_size = 1024

        if w > max_size or h > max_size:
            scale = min(max_size/w, max_size/h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            frame_resized = cv2.resize(frame_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            frame_resized = frame_bgr

        # Encode to JPEG (Quality 75 to match PIL default)
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 75]
        ret, buffer = cv2.imencode('.jpg', frame_resized, encode_param)

        if not ret:
            return None

        return {"mime_type": "image/jpeg", "data": base64.b64encode(buffer).decode()}

    async def _session_runner(self, start_message=None, is_reconnect=False):
        """Handles a single connection and run-loop of the voice agent."""
        # Force reset message_source to ensure clean state on new session/reconnect
        self.message_source = None

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

                    import queue
                    self.audio_in_queue = queue.Queue()
                    self.music_queue = queue.Queue()
                    self.out_queue = asyncio.Queue(maxsize=10)

                    # Wire MusicAgent to the dedicated music queue
                    if self.music_agent:
                        self.music_agent.set_audio_queue(self.music_queue)

                    tasks.append(asyncio.create_task(self.send_realtime()))
                    # Run listen_audio as a separate, non-critical background task
                    # This prevents the main session from crashing if audio input fails (e.g., in a headless environment)
                    audio_input_task = asyncio.create_task(self.listen_audio())
                    tasks.append(audio_input_task) # Still track it for cleanup

                    # Start Video Loop (Handles Camera/Screen switching dynamically)
                    tasks.append(asyncio.create_task(self.video_loop()))

                    tasks.append(asyncio.create_task(self.receive_audio()))
                    import threading
                    threading.Thread(target=self.play_audio, daemon=True).start()
                    tasks.append(asyncio.create_task(self.proactive_agent.run()))

                    # Start the Jules session monitoring task
                    tasks.append(asyncio.create_task(self.jules_agent.start_monitoring(self._handle_jules_status_change)))

                    # Git Fleet monitoring is now handled by AutomationEngine in server.py
                    # tasks.append(asyncio.create_task(self._monitor_git_fleet()))

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
                            gif_url = await self.giphy_agent.get_random_gif("I'm back")
                            if gif_url:
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

                        except Exception as e:
                            if INCLUDE_RAW_LOGS:
                                print(f"[ADA DEBUG] [ERR] Failed to display reconnect GIF: {e}")

                    self._last_input_transcription = ""
                    self._last_output_transcription = ""
                    self.chat_buffer = {"sender": None, "text": ""}

                    stop_task = asyncio.create_task(self.stop_event.wait())
                    reconnect_task = asyncio.create_task(self._reconnect_needed.wait())

                    wait_tasks = tasks + [stop_task, reconnect_task]
                    done, _ = await asyncio.wait(
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
            self.close()

        return False

    async def run(self, start_message=None):
        self._main_task = asyncio.current_task()
        retry_delay = 1
        is_reconnect = False

        # Start background tasks safely when event loop is running
        self.giphy_agent.start_precaching_task()
        if self.music_agent:
            await self.music_agent.start()

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
