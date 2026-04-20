# CEO Mode & Orchestration Backlog

This document outlines the detailed tasks required to upgrade A.D.A's "The Overseer" from a basic agent spawner to a fully orchestrated "CEO Mode" inspired by the `paperclip` architecture. The goal is to transition the user from a "micromanager of prompts" to "The Board," overseeing an autonomous organization of agents.

## 1. Data Model & Hierarchical State

**Goal:** Establish a robust underlying data model that supports an autonomous "Company" instead of isolated scripts.

- [ ] **Org Chart Definitions**
  - Implement a configuration system to define agent roles, reporting structures, and adapter types (e.g., CEO -> CTO -> Engineers).
  - Add `agent_roles.json` or similar config to track the hierarchy.
- [ ] **Hierarchical Task Management**
  - Replace flat prompt execution with a hierarchical task tree (e.g., Initiative -> Project -> Milestone -> Issue -> Sub-issue).
  - Implement task ancestry so every piece of work traces back to a top-level strategic goal.
- [ ] **Atomic Task Execution & Checkout**
  - Implement a single-assignee model with strict "checkout" locks for tasks to prevent agents from doing duplicate work or clashing on concurrent modifications.
  - Tasks should represent a clear "state machine" (e.g., Draft -> Pending Approval -> In Progress -> Blocked -> Done).
- [ ] **Cost and Budget Enforcement**
  - Add soft and hard token budget limits per task, per agent, and per company.
  - Implement auto-pause functionality when an agent or company hits its hard budget limit, requiring Board intervention.

## 2. Agent Capabilities & Execution Engine

**Goal:** Give the CEO agent explicit tools to manage strategy and workforce, and implement a resilient execution model.

- [ ] **Agent Hiring & Spawning**
  - Create tools for the CEO agent to "hire" (instantiate) sub-agents based on required roles and capabilities.
  - Add explicit "limbo" states for newly spawned agents until "The Board" approves their hiring request.
- [ ] **Strategy Review & Delegation**
  - Give the CEO agent the ability to review top-level goals and automatically break them down into actionable sub-tasks.
  - Allow the CEO to assign sub-tasks explicitly to reporting agents based on their defined capabilities.
- [ ] **Persistent Agent State (Heartbeats)**
  - Transition from continuous execution loops (which risk runaway token spend) to an event-driven or scheduled "Heartbeat" model.
  - Agents wake up on a heartbeat (or web-hook/event), assess their assigned tasks, take action, log status, and return to sleep.
- [ ] **Adapter Integration**
  - Wrap existing agents (`OpenHandsAgent`, `JulesAgent`, `GitAgent`) with a standardized "Adapter" interface so they can be treated as standard employees in the org chart.

## 3. UI/UX & User Loop (The Board Experience)

**Goal:** Provide the user ("The Board") with a clear, high-level view of what the autonomous system is doing, focusing on outcomes and governance rather than raw chat.

- [ ] **Output-First UX**
  - Redesign the UI to prioritize the presentation of completed artifacts (documents, PRs, mockups), rather than a streaming chat transcript.
  - Ensure conversations and logs are attached to specific tasks or issues for context, rather than a single endless thread.
- [ ] **Org Chart & Dashboard Visualization**
  - Add a dynamic Org Chart UI component showing the current agent hierarchy, their status (active, idle, paused), and budget usage.
  - Create a "Company Dashboard" showing high-level goal progress and aggregated costs.
- [ ] **Strict Governance & Approval Gates**
  - Implement a centralized "Approval Queue" UI.
  - Require explicit Board sign-off for critical actions:
    - Approving the CEO's initial strategic plan.
    - Approving new Agent "hires".
    - Overriding budget limits.
- [ ] **Live Control Surface**
  - Allow the Board to pause/resume any agent or task at any time directly from the UI.
  - Allow the Board to reassign tasks, edit descriptions, or manually adjust the priority of work.

## 4. Integration with Existing A.D.A Systems

**Goal:** Connect the new orchestration layer to A.D.A's current tooling.

- [ ] **Project Manager Integration**
  - Link the new hierarchical task system with `ProjectManager`'s isolated context storage, ensuring each "Company" or "Initiative" has its own sandbox.
- [ ] **Memory & Recall Connection**
  - Allow the CEO agent to query `MemoryManager` to inform strategic breakdowns based on past context and lessons learned.
