# Project Manager Upgrade: Integrating Routa Principles into the Agent Model

## Overview
Routa is a "workspace-first multi-agent coordination platform for software delivery." It tackles the limitations of single-thread, monolithic AI agent chats by enforcing structured workflows modeled after Kanban boards. Instead of a single agent attempting to plan, code, and review in one chaotic context, Routa uses **explicit product objects** (workspaces, sessions, boards, lanes) and **specialist agents** bounded by strict prompt contracts at each stage of delivery.

This document outlines how to upgrade the current Fleet Manager and WarRoom architecture by either directly integrating Routa or adapting its core principles to enhance the existing coding agents.

---

## Core Routa Principles to Adopt

If we are to upgrade our current system (which uses a generic `FleetManager` and a catch-all `jules_agent.py`), we must adopt the following beliefs and mechanics from Routa:

### 1. The Workspace is the Source of Truth
- **Current State:** Agents often rely on their conversational memory or ephemeral prompts to understand context.
- **Routa Model:** The repository itself (specifically a `docs/` folder or similar structured system) holds the canonical working knowledge. Artifacts like architecture specs, exec plans, and review records must be durable files, not hidden in chat history.

### 2. Kanban Lanes as Specialist Prompts
- **Current State:** Tasks in the `WarRoomDashboard` go from "pending" to "in_progress" to "completed". The same agent handles everything.
- **Routa Model:** A task moves through specific lanes (Backlog -> Todo -> Dev -> Review -> Done). Each lane is backed by a **different specialist prompt** with strict entry/exit contracts:
  - **Todo Orchestrator (Planning):** Creates an execution-ready brief. Cannot write code.
  - **Dev Crafter (Implementation):** Distrusts the plan. Only writes code scoped to the brief. Commits work and generates evidence.
  - **Review Guard (Verification):** Distrusts the Crafter. Independently verifies acceptance criteria. Rejects dirty git states or failed tests. Cannot write implementation code.

### 3. Review Gates and Evidence
- **Current State:** An agent finishes its task and assumes it's complete (`assuming task completed`), or asks the user for a review.
- **Routa Model:** Moving a card from `Dev` to `Review` requires *evidence* (e.g., test outputs, git diffs). The `Review` stage is a hard gate that forces the task back to `Dev` if evidence is missing or validation fails.

---

## Integration Strategies

There are two main approaches to upgrading the current system:

### Strategy A: Direct Integration
Integrate the Routa engine alongside the existing `server.py` backend.
- **Pros:** Full access to Routa's Axum backend, Tauri desktop features, and built-in specialist prompts.
- **Cons:** Heavy architectural mismatch. Our system relies on Python (FastAPI/SocketIO) and a React frontend heavily coupled to `fleet_manager.py` and Gemini Native Audio. Running a dual-backend (Axum + Python) introduces severe state synchronization issues regarding task queues and agent assignments.

### Strategy B: Principle Adaptation (Recommended)
Refactor the existing `FleetManager` and `WarRoomDashboard` to implement Routa's Kanban-specialist model natively in Python/React.
- **Pros:** Maintains the current tech stack, tightly integrates with the existing Voice Agent (A.D.A) and `FleetManager` ecosystem, and allows incremental adoption.
- **Cons:** Requires significant changes to `fleet_manager.py` task states and the introduction of distinct specialist agent personalities in the backend.

---

## Implementation Plan (Strategy B)

### Phase 1: Backend State & Fleet Manager Refactor
1. **Redefine Task States (`backend/fleet_manager.py`):**
   - Expand the task `status` enum to match Routa lanes: `backlog`, `todo_planning`, `dev_implementation`, `review_verification`, `completed`, `blocked`.
2. **Introduce Evidence Attachments:**
   - Tasks currently have an `attachments` array. Enforce that moving from `dev_implementation` to `review_verification` requires structured "Dev Evidence" (e.g., test logs, git commit hashes) added to the task object.
3. **Task Routing Logic:**
   - Modify `get_next_task()` to dispatch tasks not just by repository, but by required *role*.
   - When a task enters `todo_planning`, it requires a "Planner" agent. When it enters `dev_implementation`, it requires a "Crafter" agent.

### Phase 2: Specialist Agents (`backend/jules_agent.py`)
1. **Agent Profiles:**
   - Instead of a monolithic Jules system prompt, dynamically inject strict sub-prompts based on the task's current lane.
   - **Planner Prompt:** "You are the Todo Orchestrator. Read the prompt. Write an execution plan to `docs/exec-plans/{task_id}.md`. Do NOT write source code."
   - **Crafter Prompt:** "You are the Dev Crafter. Read the execution plan. Implement the code. Run tests. Update the task state with Dev Evidence."
   - **Reviewer Prompt:** "You are the Review Guard. Independently verify the acceptance criteria. If tests fail, transition the task status back to `dev_implementation` with a `Blocked Analysis`."

### Phase 3: Frontend Refactor (New Dedicated UI Route)
Given that the existing `WarRoomDashboard` is a global, space-constrained modal overlay designed for quick, transient interactions, forcing a complex Kanban board into it is fundamentally flawed. Instead, we should introduce a **dedicated full-screen route**.

1. **New Workspace Route (`src/components/WorkspaceBoard.jsx`):**
   - Create a separate, full-page UI (e.g., accessible via a new sidebar icon or a button in the WarRoom).
   - This full-screen view naturally accommodates a traditional 5-column Kanban board (`Backlog`, `Todo`, `Dev`, `Review`, `Done`), exactly mirroring Routa's UI.
2. **Visualizing Contracts in the New UI:**
   - Because we have more screen real estate, clicking a card opens a wide detail panel.
   - This panel must display the *Evidence* and *Review Findings* required for a card to move forward.
   - Surface the actual artifacts (`docs/exec-plans/...` and `docs/issues/...`) instead of just hiding everything behind the original user prompt.
3. **Blocked State Visuals:**
   - If a task is returned to `Dev` by the `Review` agent, highlight the card in red and immediately show the "Blocker Analysis" summary on the card face.

### Phase 4: Enforcing Durable Knowledge
1. **System Directives:**
   - Update `AGENTS.md` and default prompts to explicitly forbid agents from relying on long conversational histories for architectural decisions.
   - Force agents to read `docs/ARCHITECTURE.md` or `docs/issues/` when starting a task, making the file system the true state database as advocated by Routa's "Repository Holds the Working Knowledge" belief.