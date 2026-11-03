# Agent James — Architecture

> Canonical working knowledge for agents. Read this + `docs/issues/` before starting tasks. Do not rely on chat history.
> Renamed from A.D.A (Advanced Design Assistant) to **Agent James** — persona: James (British, witty, professional).

## 1. Overview
Voice-first Electron + React + Python assistant.
`Gemini 2.5 Native Audio Live` → `backend/agent_james.py:AgentJames` → `backend/server.py:FastAPI + Socket.IO :8180` → ~35 specialist agents + React UI.

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
`TopAudioBar` + `ChatModule` + `ToolsModule` + `DisplayArea`; overlays `AuthLock`, `ConfirmationPopup`, `NotificationManager`, `Suggestion`, `SettingsWindow/FleetSettingsWindow`, `FleetManagerUI/SwarmVisualizer/WarRoomDashboard/WorkspaceBoard` (Kanban `backlog→todo_planning→dev_implementation→review_verification→completed`), `KasaWindow`, `PrinterWindow`, `CadWindow`, `BrowserWindow`, `AutomationEditor`, `MusicPlayerBar` + visualizers (`three/@react-three`, `butterchurn`, `livekit-client`). Title: `Agent James`. Mobile: `backend/templates/mobile.html` (`Agent James Mobile`, sender `James`, backward compat `ADA`), `manifest.json` (`Agent James Mobile`/`James`).

## 5. Branding rename (A.D.A → Agent James)
- `backend/ada.py` → `backend/agent_james.py`, `AudioLoop` → `AgentJames` (`AudioLoop = AgentJames` alias)
- `tests/test_ada_tools.py` → `tests/test_agent_james_tools.py` (imports `backend.agent_james`)
- Logs `[ADA]`/`[ADA DEBUG]` → `[JAMES]`/`[JAMES DEBUG]`; transcription sender `ADA` → `James`
- `automation_engine.ada` → `.agent` (`.ada` alias kept); `server.py` sets both
- `cli_harness.py`: `james = AgentJames(...)`
- UI: `AGENT JAMES` header, `AGENT JAMES OS v2.0`, `Agent James Started/Stopped`
- Package `ada-v2` → `agent-james`; conda `ada_v2` → `agent_james`; repo `nazirlouis/ada_v2` → `Cyberdogs7/agent_james`
- Intentional transitional refs kept: backward-compat aliases + comments mentioning old import paths.

## 6. Dependencies — deprecation audit (2026-11-03)
**Decision: audit only, no deletion (per user).**

### Google API (`google-genai`, `GEMINI_API_KEY`, `gemini-*`)
Core, not removable without rewrite. Used in:
- `backend/agent_james.py`: `genai.Client`, `MODEL=models/gemini-2.5-flash-native-audio-preview-12-2025`, `gemini-2.5-flash` fallback
- `backend/web_agent.py`: `MODEL_ID=gemini-2.5-flash`, `GEMINI_API_KEY` required
- `backend/cad_agent.py`: `gemini-3-pro-preview` (disabled stubs, still imports)
- `backend/proactive_agent.py`: `gemini-1.5-flash`
- `backend/automation_engine.py`: `GEMINI_API_KEY`, `gemini-2.0-flash` self-heal
- `backend/memory_manager.py`: `GEMINI_API_KEY`, `text-embedding-004`
- `backend/mcp_client.py`/`local_web_agent.py`: Gemini schema converters (`convert_to_gemini_schema`, `convert_gemini_to_openai`)
- `requirements.txt`/`requirements_safe.txt`: `google-genai`
- `tests/conftest.py` mocks `google.genai`; `SettingsWindow.jsx` manages `GEMINI_API_KEY`
Recommendation: keep. If deprecating later, need ASR+LLM+TTS replacement (see `OPENSOURCE_OPTIONS.md` chained: Whisper-Turbo + Llama-3.1-8B + Kokoro, ~8-11GB VRAM) + migrate embeddings + tool schemas. Do not delete now — breaks voice core.

### Google Jules
**Not found.** `rg -i jules` across repo (excl. node_modules/.venv/.git): zero matches. No package, import, env, or doc reference. No action needed. If Jules was expected via OpenCode/OpenHands integration, it was never wired — use `opencode_agent`/`openhands_agent` instead.

## 7. Open issues
- `docs/issues/youtube_music_playlist_access.md` — **open**. Proposes SHA1 `SAPISIDHASH`, `_authenticated=False` reset, cookie expiry. Current code uses `SAPISIDHASH placeholder` (relies on `ytmusicapi` overwrite). Decide hack vs proper fix before closing.

## 8. Run / test
- Backend: `python backend/server.py` (port `SERVER_PORT` or 8180, `/status`)
- Frontend: `npm run dev` (Vite + Electron `--no-sandbox`)
- Tests: `pytest` (`pytest.ini:asyncio_mode=auto,testpaths=tests`), 35 `test_*.py`; runner `tests/test_runner.py` (`tools→test_agent_james_tools.py`)
- First flight: "Hello James" → voice; camera unlock; CAD (disabled); browser task; Kasa lights.
