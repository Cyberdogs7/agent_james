# OpenCode Integration for ADA V2 - Implementation Summary

## Status: Implemented

## Overview
OpenCode has been integrated into ADA as a local coding agent, following the same patterns as the existing Jules agent. ADA can now send coding tasks to OpenCode, poll for progress, and receive updates via voice and UI.

## Architecture

### Core Components

| File | Purpose |
|------|---------|
| `backend/opencode_agent.py` | Core agent class (~400 lines) - HTTP client, session management, polling, workspaces |
| `backend/tools.py` | 6 new tool declarations for OpenCode operations |
| `backend/ada.py` | Handler methods, voice routing, triage interceptor |
| `backend/server.py` | Settings defaults, Socket.IO event handlers |
| `backend/fleet_manager.py` | OpenCode session tracking methods |
| `src/components/SettingsWindow.jsx` | UI configuration panel |

### Tool Definitions

| Tool | Description |
|------|-------------|
| `run_opencode_agent` | Create and start a new coding task |
| `send_opencode_feedback` | Send follow-up message to existing session |
| `list_opencode_sessions` | List all active sessions |
| `list_opencode_messages` | Get messages/progress from a session |
| `abort_opencode_session` | Cancel a running task |
| `dismiss_opencode_session` | Stop tracking and clean up |

### Settings (settings.json)

```json
{
    "opencode_server_url": "http://127.0.0.1:4096",
    "opencode_server_port": 4096,
    "opencode_auto_start": true,
    "opencode_use_worktrees": true,
    "opencode_use_interceptor": true,
    "opencode_model_tiers": {
        "high": "opencode/big-pickle",
        "medium": "opencode/deepseek-v4-flash-free",
        "low": "opencode/nemotron-3-super-free"
    },
    "opencode_permission_rules": {
        "read": "allow",
        "glob": "allow",
        "grep": "allow",
        "edit": "ask",
        "bash": "ask",
        "task": "ask",
        "webfetch": "ask",
        "doom_loop": "deny"
    }
}
```

## Features

### Voice Routing
- Say "opencode" or "open code" when ADA asks which agent to use
- ADA will route the task to OpenCode automatically

### Workspace Isolation (Default ON)
- Creates git worktrees for each task to prevent file conflicts
- Controlled via `opencode_use_worktrees` setting
- Worktrees are cleaned up after task completion

### Triage Interceptor (Configurable)
- When enabled, OpenCode messages go through Ollama for auto-reply/escalation
- When disabled, messages go directly to voice/UI notifications
- Controlled via `opencode_use_interceptor` setting

### Model Selection
- Three tiers: high, medium, low
- User configures which free model maps to each tier in Settings
- Available free models: Big Pickle, DeepSeek V4 Flash, MiniMax M2.5, Nemotron 3 Super

### Server Lifecycle
- ADA automatically starts `opencode serve` if not running
- Health checks with exponential backoff
- Graceful shutdown on ADA exit

## Usage

### Via Voice
1. Say "create a coding task" or similar
2. ADA asks which agent to use
3. Say "OpenCode"
4. ADA creates session and starts working

### Via Tool Call
```python
# Direct tool call
run_opencode_agent(prompt="Fix the login bug", model_tier="medium")

# With specific repo path
run_opencode_agent(prompt="Add dark mode", repo_path="/path/to/repo", model_tier="high")
```

### Via Settings UI
1. Open Settings window
2. Navigate to "OpenCode Configuration" section
3. Configure server URL, port, workspaces, interceptor, and model tiers
4. Click "Save OpenCode Settings"

## Dependencies
- OpenCode binary installed and available on PATH
- httpx (already in project)
- No new Python packages required

## Next Steps (Future Enhancements)
- [ ] SSE event stream for real-time permission handling
- [x] FleetManager integration for Kanban board display
- [ ] Permission approval via voice/UI
- [ ] Session history and replay
- [ ] Multi-workspace merge conflict detection

## Kanban Board Integration (Implemented)

### Overview
OpenCode tasks are now integrated with the WorkspaceBoard kanban system. Tasks automatically receive mode prefixes (Plan/Execute) based on their kanban lane status.

### Workflow
1. **Task Created** → Status: `backlog` → ADA dispatches with Plan mode prefix
2. **User Reviews** → Drags to `dev_implementation` → Socket.IO triggers mode switch
3. **ADA Re-prompts** → Same session receives Execute mode prefix
4. **OpenCode Completes** → Auto-moves task to `completed` lane

### Mode Prefixes
| Kanban Status | Mode | Behavior |
|--------------|------|----------|
| `todo_planning` | Plan | Analyzes task, creates implementation plan, no code changes |
| `dev_implementation` | Execute | Implements the task, makes all code changes |

### Tool Parameter
The `run_opencode_agent` tool now accepts `kanban_status` parameter:
```python
run_opencode_agent(
    prompt="Fix the login bug",
    kanban_status="todo_planning"  # or "dev_implementation"
)
```

### Files Modified
- `backend/tools.py` - Added `kanban_status` enum parameter
- `backend/ada.py` - Added mode prefix injection and fleet tracking
- `backend/server.py` - Enhanced `update_task_status_lane` handler
- `backend/fleet_manager.py` - Added `get_task_by_session` helper
