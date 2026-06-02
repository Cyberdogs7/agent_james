# OpenCode Integration Plan for ADA V2

## Overview
This document outlines the plan to integrate [OpenCode](https://opencode.ai/) into the ADA V2 architecture. The integration will allow ADA to delegate complex coding tasks to OpenCode's API, dynamically select LLM models for OpenCode to use, and track OpenCode tasks through the existing Workspace Kanban Board (`WorkspaceBoard.jsx`).

## Benefits & Trade-offs
### Benefits
- **Dedicated Coding OS**: OpenCode provides specialized terminal and coding agents that handle file edits natively.
- **Dynamic Routing**: ADA can act as a natural language router, determining when to use OpenCode vs. other agents (like OpenHands or Jules).
- **Native Kanban Support**: The integration cleanly hooks into `FleetManager` and the React Kanban UI, meaning tasks sent to OpenCode become trackable tickets that can be visually monitored.
- **API Modularity**: By utilizing OpenCode's API instead of CLI calls, ADA maintains robust state tracking, cleaner error handling, and structured communication.

### Trade-offs
- **Additional Dependency**: Requires users to have an OpenCode API server/process accessible, adding complexity to the developer setup compared to native Python agents.
- **State Synchronization**: OpenCode has its own internal state management which must be carefully synced with ADA's `FleetManager` to ensure the Kanban UI accurately reflects agent status.
- **Model Key Propogation**: Passing API keys and model selections to an external API securely requires careful credential management between ADA's `.env` and the OpenCode payload.

---

## Architecture Changes

### 1. `backend/opencode_agent.py`
Create a new agent wrapper class `OpenCodeAgent` similar to `openhands_agent.py`.
- **Initialization**: Will accept a base URL pointing to the OpenCode API.
- **Dynamic Model Selection**: Support passing in an explicit `model` argument (e.g. `claude-3.5-sonnet`, `gemini-2.5-pro`, or open router models) to the session creation payload.
- **Methods**:
  - `async def create_session(self, prompt, repo_path, model_selection)`
  - `async def spawn_agent(self, prompt, repo_path, model_selection)`
  - `async def check_status(self, session_id)` for polling and Kanban updates.

### 2. `backend/ada.py`
Update the central AI router to register OpenCode tools and handle user intent.
- **Instantiation**: Add `self.opencode_agent = OpenCodeAgent()` to the `__init__` method.
- **Tool Registration**: Add a `run_opencode_agent` tool into `self.tool_registry`.
- **Voice Intercepts**: Update the transcription logic. When ADA enters the routing phase (`self._pending_coding_task_prompt`), listen for the keyword "opencode".
- **Handlers**: Create `async def handle_opencode_request(self, prompt, repo_path=None, model=None)` to trigger the spawn and notify the user via voice.

### 3. `backend/tools.py`
Add the OpenCode tool definition so Gemini knows how to use it.
```python
run_opencode_agent_tool = {
    "name": "run_opencode_agent",
    "description": "Creates a new OpenCode coding task.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "prompt": { "type": "STRING", "description": "The description of the coding task." },
            "repo_path": { "type": "STRING", "description": "Optional repository path." },
            "model": { "type": "STRING", "description": "The LLM model to delegate to (e.g., 'gemini', 'claude', 'openrouter/model')." }
        },
        "required": ["prompt"]
    }
}
```
Add `run_opencode_agent_tool` to the global tools list.

### 4. `backend/fleet_manager.py` & `backend/server.py`
- When OpenCode starts, its session ID needs to be stored in the `FleetManager` so the `WorkspaceBoard` can display it in the "Todo / Planning" or "Dev / Implementation" lane.
- Update `server.py`'s agent task pooling loop to recognize `opencode` agent IDs and correctly route completion/error events to the frontend.

### 5. Frontend & UI
- Since OpenCode can require manual confirmation for critical steps, the frontend needs a mechanism to surface these requests. We can use the existing `ConfirmationPopup.jsx` or send voice confirmation prompts back to the user via ADA.
- Ensure the `TaskDetailPanel` in `WorkspaceBoard.jsx` correctly parses OpenCode session IDs and attachments (diffs/logs).

## Execution Strategy
This plan structures the implementation to gracefully add OpenCode alongside the existing agents without disrupting the core Gemini voice loop. ADA remains the orchestrator, delegating task payloads dynamically to OpenCode's API and pulling statuses into the global Fleet system.