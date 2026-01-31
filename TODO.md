# Product Backlog & Vision

This document serves as the single source of truth for the evolution of the A.D.A (Advanced Design Assistant) platform. It outlines the roadmap towards a "JARVIS-level" intelligence, prioritizing cinematic interactions, proactive assistance, and deep integration with development workflows.

**North Star:** "Proactive, context-aware, cinematic, useful, and occasionally delightful."
**Persona:** James (British, witty, professional).

---

## 🌟 WOW / JARVIS-Level Features
*Big, bold, aspirational capabilities that define identity.*

- [x] **"Omniscient" Desktop Vision**
  - **Description**: Allow James to "see" the user's screen content on demand. "James, look at this error log" or "What do you think of this UI design?".
  - **Wow Factor**: Bridges the gap between the assistant and the digital workspace. The AI becomes a true pair programmer that sees what you see.
  - **User Impact**: Dramatically reduces the need to copy-paste context.
  - **Technical Notes**: Implemented `_get_screen` in `ada.py` using `mss`. Added `switch_video_source` tool to dynamically toggle between camera and screen share.
  - **Status**: **Implemented**

- [x] **Swarm Intelligence (Multi-Agent Mode)**
  - **Description**: Allow James to spawn and coordinate multiple "Jules" agents to work on different repositories or tasks simultaneously.
  - **Wow Factor**: "Sir, I have Agent 1 refactoring the frontend and Agent 2 updating the API. Both are 50% complete."
  - **User Impact**: Massive parallelism for complex refactors.
  - **Technical Notes**: Extend `JulesAgent` to manage a pool of sessions and aggregate their "thought" streams into a unified dashboard view.
  - **Status**: **Implemented**
    - [x] **Centralize Session Management**: Refactor `JulesAgent` to internally manage `asyncio` polling tasks for multiple sessions, removing ad-hoc management from `ada.py`.
    - [x] **Add `spawn_swarm_agent` Tool**: Create a high-level tool for the assistant to explicitly spawn agents with defined roles.
    - [x] **Swarm Dashboard Aggregation**: Update `get_dashboard_data` to visualize the status and active "thoughts" of the entire fleet.

- [x] **Remote Fleet Management**
  - **Description**: Monitor and manage remote repositories (JulesAgents) directly from the War Room. View detailed commit history, branch status, and perform remote merges.
  - **Wow Factor**: "James, merge the feature branch on the backend repo."
  - **User Impact**: Centralized control of the distributed agent fleet.
  - **Technical Notes**: Integration with GitHub API via `GitHubClient` to fetch commit details and trigger merges. Dashboard UI for fleet status.
  - **Status**: **Implemented**

---

## 👔 Engineering Manager Mode (Orchestration & Review)
*Transforming the user from a coder to a commander of agents.*

- [ ] **Event-Driven Automation Engine**
  - **Description**: A robust "If-This-Then-That" system to trigger Jules Agents based on events.
    - *Triggers*: Schedule (Cron), Git Events (PR Open, Commit Push), Trello Card Movement.
    - *Actions*: Spawn Agent with specific Prompt & Context, Send Notification, Run Script.
  - **Wow Factor**: "Sir, the nightly build failed, so I automatically deployed an agent to investigate the logs. It has identified the issue."
  - **User Impact**: Automates the "management" overhead of assigning tasks to agents.

- [ ] **Streamlined "One-Click" Review & Merge**
  - **Description**: A dedicated interface for reviewing Agent work.
    - View file diffs directly in the dashboard.
    - "Approve & Merge": Single button to merge the PR and delete the remote branch, replacing the 5-click GitHub workflow.
  - **Wow Factor**: Reviewing code becomes as fast as swiping through a feed.
  - **User Impact**: Drastically reduces the friction of finalizing agent work.

- [ ] **Proactive Voice Notifications ("The Nagging Secretary")**
  - **Description**: Voice announcements to ensure the human manager doesn't become the bottleneck.
  - **Behavior**: If a Jules Agent finishes a task and it sits unreviewed for >X minutes, James verbally notifies the user. "Sir, Agent 3 has finished the refactor and is awaiting your approval."
  - **User Impact**: Keeps the "factory line" of coding agents moving efficiently.

---

## 🛠 Quality of Life & Polish
*Features that make daily use smoother, faster, and more delightful.*

- [x] **Conversation Memory Persistence**
  - **Description**: Allow James to look up past conversation history. "What did we decide about the database last week?"
  - **User Impact**: Continuity and reference.
  - **Technical Notes**: Implemented `search_chat_history` in `project_manager.py` and integrated it into the `search` tool via `search_agent.py`. The assistant can now search through `chat_history.jsonl`.
  - **Status**: **Implemented**

---

## 🛑 Deprecated / Removed
- *Legacy "Chatbot" Interfaces*: We are moving towards purely multimodal/agentic interactions.
- *Local "Brain"*: Removed to focus on cloud-based Swarm Intelligence.
- *Semantic Code Search*: Removed to focus on Swarm Intelligence.
- *Smart Home "Scenes"*: Removed to focus on Swarm Intelligence.
- *Video Feed Optimization*: Removed to focus on Swarm Intelligence.
