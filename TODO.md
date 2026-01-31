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
