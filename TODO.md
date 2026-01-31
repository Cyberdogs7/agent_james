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

- [ ] **Swarm Intelligence (Multi-Agent Mode)**
  - **Description**: Allow James to spawn and coordinate multiple "Jules" agents to work on different repositories or tasks simultaneously.
  - **Wow Factor**: "Sir, I have Agent 1 refactoring the frontend and Agent 2 updating the API. Both are 50% complete."
  - **User Impact**: Massive parallelism for complex refactors.
  - **Technical Notes**: Extend `JulesAgent` to manage a pool of sessions and aggregate their "thought" streams into a unified dashboard view.
  - **Status**: **Idea**

- [x] **Remote Fleet Management**
  - **Description**: Monitor and manage remote repositories (JulesAgents) directly from the War Room. View detailed commit history, branch status, and perform remote merges.
  - **Wow Factor**: "James, merge the feature branch on the backend repo."
  - **User Impact**: Centralized control of the distributed agent fleet.
  - **Technical Notes**: Integration with GitHub API via `GitHubClient` to fetch commit details and trigger merges. Dashboard UI for fleet status.
  - **Status**: **Implemented**

- [ ] **Local "Brain" (Offline Mode)**
  - **Description**: When the internet is down (or for privacy), switch to a local LLM (e.g., Llama 3 on GPU) for basic commands (timers, local device control).
  - **Wow Factor**: "Sir, the network is down, but I am still operational."
  - **User Impact**: Reliability and privacy.
  - **Technical Notes**: Integration with `ollama` or `llama.cpp` python bindings. Check `check_cuda.py` for hardware capability.
  - **Status**: **Idea**

---

## 🧩 Smart Enhancements
*High-impact improvements that make the assistant feel sharper and more capable.*

- [ ] **Project Management Suite (Slack & Trello)**
  - **Description**: Formalize the current experimental Slack and Trello agents into a core "Office Manager" feature. "James, summarize the morning standup from Slack and create Trello cards for the blockers."
  - **Wow Factor**: The assistant handles the bureaucracy of software development.
  - **User Impact**: Less context switching between chat, tracker, and IDE.
  - **Technical Notes**: The agents exist (`slack_agent.py`, `trello_agent.py`) but need higher-level intent logic in `ada.py` to coordinate them.
  - **Status**: **Partially Implemented**

- [ ] **Semantic Code Search**
  - **Description**: "Where do we handle authentication?" -> James opens the exact file and highlights the lines.
  - **Wow Factor**: Instant navigation of large codebases.
  - **User Impact**: Faster debugging and onboarding.
  - **Technical Notes**: Use `chromadb` or similar to embed the codebase (already started in `memory_manager.py`?) and provide a "Jump to" tool.
  - **Status**: **Idea**

- [ ] **Smart Home "Scenes"**
  - **Description**: Context-aware environment control. "James, I'm coding." -> Lights turn cool white, music lowers. "James, it's late." -> Lights warm, notifications suppressed.
  - **Wow Factor**: The physical room adapts to the digital task.
  - **User Impact**: Immersion and focus.
  - **Technical Notes**: Extend `KasaAgent` to support grouped states (Scenes) rather than just individual device control.
  - **Status**: **Idea**

---

## 🛠 Quality of Life & Polish
*Features that make daily use smoother, faster, and more delightful.*

- [ ] **Video Feed Optimization (WebWorker)**
  - **Description**: Ensure the camera feed doesn't freeze when the agent is "thinking" (blocking main thread).
  - **Technical Notes**: Move video processing to a WebWorker or optimize the Python asyncio loop.
  - **Status**: **Idea** (Optimization)

- [ ] **Conversation Memory Persistence**
  - **Description**: Allow James to remember the *conversation* context across restarts, not just the project files. "As we discussed yesterday..."
  - **User Impact**: Continuity.
  - **Technical Notes**: Persist `chat_buffer` or a summary of it to `memory.jsonl` on session end.
  - **Status**: **Idea**

---

## 🛑 Deprecated / Removed
- *Legacy "Chatbot" Interfaces*: We are moving towards purely multimodal/agentic interactions.
