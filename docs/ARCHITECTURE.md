# Agent James — Architecture

> Canonical working knowledge for agents. Read this + `docs/issues/` before starting tasks. Do not rely on chat history.
> Renamed from A.D.A (Advanced Design Assistant) to **Agent James** — persona: James (British, witty, professional).
> google-genai/Gemini removed. Raw httpx LLM (OpenRouter/LM Studio/Ollama, no SDK) + local/hybrid voice (STT→LLM→TTS).

## 1. Overview
Voice-first Electron + React + Python assistant.
`Raw httpx LLM (LLMClient) + voice_pipeline (STT→LLM→TTS)` → `backend/agent_james.py:AgentJames` → `backend/server.py:FastAPI + Socket.IO :8180` → ~35 specialist agents + React UI.

- Backend entry: `backend/agent_james.py` (`AgentJames`, alias `AudioLoop` for backward compat)
- Server: `backend/server.py` (Socket.IOano events, `/status`, `/mobile`, static `/projects`)
- Tools: `backend/tools.py` (~80+ schemas, `NON_BLOCKING`), `backend/tool_registry.py` (`register/dispatch/load_skills`, confirmation keywords)
- Orchestration: `backend/fleet_manager.py` (`projects/fleet_state.json`), `backend/automation_engine.py` (cron/interval/daily + git/Trello monitors + self-heal), `backend/task_manager.py`
- Memory: `backend/memory_manager.py` (`memory.jsonl` + `text-embedding-004`), `backend/db.py` (SQLite `projects/ada.db:oauth_credentials`), `backend/project_manager.py` (per-project dirs, `user_profile.json`, FTS5 chat)
- Frontend: `src/App.jsx` (~2248 lines), 34 `src/components/*.jsx` + 4 `agents-ui/*.tsx`, `electron/main.js` (frameless 1920x1080, Vite :5173 dev / `dist/` prod, auto-spawns `.venv` backend)
- Package: `agent-james@1.0.0` (`package.json` / `package-lock.json`), Docker service `agent-james` (`docker-compose.yml`), conda env `agent_james`

## 2. Request flow
1. `server.py:start_audio` creates `AgentJames(sio, callbacks...)` in daemon thread.
2. `AgentJames._get_live_connect_config()` sends `tools_list + dynamic skills` to Gemini Live.
3. `receive_audio()`: `tool_call.function_calls` → permission check → `tool_confirmation_request` → `ToolRegistry.dispatch` → `FunctionResponse` → `session.send_tool_response()`.
4. Long tasks (`run_web_agent`, `run_research_agent`, `run_opencode_agent`) run as `asyncio.create_task` + `System Notification:` callback.
5. Frontend Socket.IO: `user_input`, `video_frame`, `confirm_tool`, `interrupt` in; `status`, `transcription`, `display_content`, `fleet_state_update`, `printer_list`, etc. out. Status strings: `Agent James Started/Stopped`, `Connected to Agent James Backend`.

## 3. Agents (1-line)
`browser_agent` Playwright primitives; `local_web_agent`/`web_agent` task runner; `research_agent` deep-research loop; `search_agent`/`scraper_agent` search+scrape; `openhands_agent`/`opencode_agent` external coding (worktrees, model tiers, Ollama triage); `ollama_agent`/`openai_agent`/`llm_client` offload; `git_agent`/`github_agent` git+PRs; `kasa_agent` TP-Link; `printer_agent` Moonraker/OctoPrint + Orca; `timer_agent` reminders; `music_agent` YouTube Music queue; `weather_agent` widget; `trello_agent` CRUD; `os_agent` volume/apps/keys; `fs_agent` sandboxed files; `writing_agent`+`autonovel/` novel pipeline; `proactive_agent` vision nudges; `update_agent` releases; `oauth_manager`+`providers/` OAuth; `mcp_client` MCP bridge; `slack_agent` Slack IO; `authenticator` face-auth; `bug_hunter`/`log_monitor` pytest/stderr watch; `cad_agent` **disabled (stubs)**; `time_utils`.

## 4. Frontend map
`TopAudioBar` + `ChatModule` + `ToolsModule` + `DisplayArea`; overlays `AuthLock`, `ConfirmationPopup`, `NotificationManager`, `Suggestion`, `SettingsWindow/FleetSettingsWindow`, `FleetManagerUI/SwarmVisualizer/WarRoomDashboard/WorkspaceBoard` (Kanban `backlog→todo_planning→dev_implementation→review_verification→completed`), `KasaWindow`, `PrinterWindow`, `CadWindow`, `BrowserWindow`, `AutomationEditor`, `MusicPlayerBar` + visualizers (`three/@react-three`, `butterchurn`, `livekit-client`). Voice output: `VoicePlayback` (renderless; server 24kHz PCM → browser `AudioContext` FIFO queue, gapless scheduling, `setSinkId` speaker select, mute-aware, stops on interrupt; works frontend/server split — mobile template already plays `audio_data` the same way). Title: `Agent James`. Mobile: `backend/templates/mobile.html` (`Agent James Mobile`, sender `James`, backward compat `ADA`), `manifest.json` (`Agent James Mobile`/`James`).

## 5. Branding rename (A.D.A → Agent James)
- `backend/ada.py` → `backend/agent_james.py`, `AudioLoop` → `AgentJames` (`AudioLoop = AgentJames` alias)
- `tests/test_ada_tools.py` → `tests/test_agent_james_tools.py` (imports `backend.agent_james`)
- Logs `[ADA]`/`[ADA DEBUG]` → `[JAMES]`/`[JAMES DEBUG]`; transcription sender `ADA` → `James`
- `automation_engine.ada` → `.agent` (`.ada` alias kept); `server.py` sets both
- `cli_harness.py`: `james = AgentJames(...)`
- UI: `AGENT JAMES` header, `AGENT JAMES OS v2.0`, `Agent James Started/Stopped`
- Package `ada-v2` → `agent-james`; conda `ada_v2` → `agent_james`; repo `nazirlouis/ada_v2` → `Cyberdogs7/agent_james`
- Intentional transitional refs kept: backward-compat aliases + comments mentioning old import paths.

## 6. Dependencies — google-genai + openai SDK removal (done)
**google-genai removed; `openai` SDK also removed. Raw httpx only (anime pattern).**

- `requirements.txt` / `requirements_safe.txt`: `google-genai` gone, `openai` gone — `httpx` only
- `backend/llm_client.py`: raw `POST {base}/chat/completions` via httpx (sync+async, SSE streaming); `response_format` never sent (local servers 400) — prompt-enforced JSON + `_extract_json` retries; `max_tokens` omitted by default (`JAMES_MAX_OUTPUT_TOKENS`); OpenAI-shaped `_Resp` shim keeps callers unchanged; chain `JAMES_LLM_*` override → OpenRouter → LM Studio → Ollama `/v1`
- `backend/local_web_agent.py`, `cli_harness.py`, `backend/embeddings.py`: ex-`AsyncOpenAI` call sites → raw `LLMClient`/httpx
- `backend/agent_james.py`: no top-level genai import/client; Gemini Live disabled; text chat via `handle_text_chat()` (LLMClient + tools + optional TTS); `_session_runner` runs background LLM tasks in text mode
- `backend/voice_pipeline.py`: STT (`faster-whisper` opt-in, default none/frontend text) + TTS (auto: Qwen3-TTS clone → Kokoro → Piper → none) + `get_llm()` (LLMClient)
- `backend/qwen_tts.py`: Qwen3-TTS voices (ported anime `studio/tts_runner.py` protocol). Default **design** mode — VoiceDesign renders the built-in James description (warm British male, `JAMES_VOICE_DESCRIPTION` override), no recording needed; opt-in **clone** mode (ref WAV + transcript → `.pt` prompt cache). Resident `--serve` worker (one 1.7B model resident, idle-timeout releases VRAM; stdout-junk-tolerant replies); output normalized to 24kHz PCM16 (stdlib only). Measured 2.4s/sentence — quality path, NOT realtime.
- `backend/chatterbox_tts.py` (new): **realtime** backend (MIT). Zero-shot clone of `voices/james_ref.wav` (23s, built once via `python -m backend.qwen_tts --build-ref` from the designed voice). Native 24kHz, ~1.5s/chunk on 4060 Ti, singleton model (~2GB VRAM). Needs CUDA torch (`--index-url .../cu124`; pip installs CPU torch by default) + `setuptools`/`onnxruntime` for perth import; Resemble watermark deliberately disabled (DummyWatermarker passthrough). Chain: chatterbox → qwen → kokoro → piper → none. Verified end-to-end via `TTSProvider`. Pair with OpenRouter LLM to dodge VRAM contention.
- `backend/embeddings.py` (new): local hashed embeddings (no network); optional OpenAI-compatible `api_embed`
- `backend/memory_manager.py`: local embeddings, keyword fallback preserved
- `backend/automation_engine.py`: self-heal via LLMClient `chat_completion`
- `backend/proactive_agent.py`: vision via LLMClient OpenAI-compatible vision; `genai_client` kept as legacy kwarg
- `backend/cad_agent.py`: codegen via LLMClient (`JAMES_CAD_MODEL` / `OPENROUTER_MODEL`)
- `backend/web_agent.py`: deprecated stub (raises → use `LocalWebAgent`); Gemini `computer_use` gone
- `backend/mcp_client.py` / `local_web_agent.py` / `cli_harness.py`: schema converters renamed (`convert_to_tool_schema`, `convert_tools_to_openai`, aliases kept)
- `.env.example`: `OPENROUTER_API_KEY/MODEL`, `LM_STUDIO_*`, `OLLAMA_*`, `JAMES_STT_*`, `JAMES_TTS_*` (+ `JAMES_VOICE_FILE`, Qwen venv/model/sox). No `ELEVENLABS_*` (legacy audiobook only).
- `SettingsWindow.jsx`: API keys list updated (no GEMINI)
- Tests: google mocks removed; CAD skips check `OPENROUTER_API_KEY`/`LM_STUDIO_BASE_URL`; web_agent tests assert deprecation; proactive tests mock `llm_client.chat_completion`

### Google Jules
**Confirmed removed / never present.** Only mention is this doc's prior audit line. No package, import, env, or code reference. No action needed — use `opencode_agent`/`openhands_agent` for coding sessions, `LLMClient` for general LLM (opencode serve is unsuitable as realtime brain: async poll, no tools/JSON, coding prompt).

## 7. Open issues
- `docs/issues/youtube_music_playlist_access.md` — **open**. Proposes SHA1 `SAPISIDHASH`, `_authenticated=False` reset, cookie expiry. Current code uses `SAPISIDHASH placeholder` (relies on `ytmusicapi` overwrite). Decide hack vs proper fix before closing.

## 8. Run / test
- Backend: `python backend/server.py` (port `SERVER_PORT` or 8180, `/status`)
- Frontend: `npm run dev` (Vite + Electron `--no-sandbox`)
- Tests: `pytest` (`pytest.ini:asyncio_mode=auto,testpaths=tests`), 35 `test_*.py`; runner `tests/test_runner.py` (`tools→test_agent_james_tools.py`)
- First flight: "Hello James" → voice; camera unlock; CAD (disabled); browser task; Kasa lights.
