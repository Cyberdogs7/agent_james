# CEO Mode & Orchestration Backlog

This document outlines the detailed tasks required to upgrade A.D.A's "The Overseer" from a basic agent spawner to a fully orchestrated "CEO Mode" inspired by the `paperclip` architecture.

## 1. Data Model & Hierarchical State

**Goal:** Establish a robust underlying data model that supports an autonomous "Company" instead of isolated scripts.

- [ ] **Org Chart Definitions**
  - Implement a configuration system to define agent roles, reporting structures, and adapter types (e.g., CEO -> CTO -> Engineers).
  - Add `agent_roles.json` or similar config to track the hierarchy.
- [ ] **Hierarchical Task Management**
  - Replace flat prompt execution with a task graph.
  - Implement task ancestry so every piece of work (e.g., "Write a test") traces back to a top-level strategic goal (e.g., "Ship feature X").
- [ ] **Budget & Token Tracking**
  - Add token budget limits per task and per agent to prevent runaway loops.
  - Expose cost tracking to the CEO role to allow for budget-based prioritization.

## 2. CEO Agent Capabilities

**Goal:** Give the CEO agent explicit tools to manage strategy and workforce.

- [ ] **Agent Hiring & Spawning**
  - Create tools for the CEO agent to "hire" (instantiate) sub-agents based on the required role.
  - Add explicit "limbo" states for newly spawned agents until the CEO or User approves their configuration.
- [ ] **Strategy Review & Delegation**
  - Give the CEO agent the ability to review top-level goals and automatically break them down into actionable sub-tasks.
  - Allow the CEO to assign sub-tasks explicitly to reporting agents (e.g., assign technical task to `JulesAgent`).
- [ ] **Heartbeat System**
  - Implement a cron-like heartbeat for the CEO agent to periodically wake up, review sub-agent progress, and update strategy.

## 3. UI/UX & User Loop

**Goal:** Provide the user ("The Board") with a clear, board-level view of what the autonomous system is doing.

- [ ] **Org Chart Visualization**
  - Add a UI component in the frontend to display the current agent hierarchy and their status (active, idle, pending).
- [ ] **Task & Strategy Dashboard**
  - Create a dashboard showing the hierarchical task tree, budget usage, and current blockers.
- [ ] **Explicit Approval Gates**
  - Implement a threaded approval UI where the CEO agent presents a strategy or a sub-agent's output for user sign-off.
  - Ensure execution pauses on critical gates (e.g., "Approve new Agent Hire", "Approve CEO Strategy").

## 4. Integration with Existing A.D.A Systems

**Goal:** Connect the new orchestration layer to A.D.A's current tooling.

- [ ] **Project Manager Integration**
  - Link the new hierarchical task system with `ProjectManager`'s isolated context storage.
- [ ] **OpenHands & Jules Alignment**
  - Wrap `OpenHandsAgent` and `JulesAgent` with the new adapter interface so they can be "hired" and managed by the CEO agent.
- [ ] **Memory & Recall Connection**
  - Allow the CEO agent to query `MemoryManager` to inform strategic breakdowns based on past context.
