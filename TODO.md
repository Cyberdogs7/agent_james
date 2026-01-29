# Product Backlog & Vision

This document serves as the single source of truth for the evolution of the A.D.A (Advanced Design Assistant) platform. It outlines the roadmap towards a "JARVIS-level" intelligence, prioritizing cinematic interactions, proactive assistance, and deep integration with development workflows.

**North Star:** "Proactive, context-aware, cinematic, useful, and occasionally delightful."
**Persona:** James (British, witty, professional).

---

## 🌟 WOW / JARVIS-Level Features
*Big, bold, aspirational capabilities that define identity.*

- [ ] **Holographic Avatar Interface**
  - **Description**: Replace the static UI with a reactive 3D avatar (using `three-vrm`) that lip-syncs to ADA's voice, tracks the user's face (via camera), and displays emotions (thinking, listening, happy).
  - **Wow Factor**: Transforms the assistant from a voice in a box to a "physical" presence in the room. The avatar looks at you when you speak.
  - **User Impact**: Higher engagement and immediate visual feedback on the agent's state (listening vs. processing).
  - **Technical Notes**: Requires installing `@pixiv/three-vrm`. Need to map audio amplitude/visemes to blend shapes and head rotation to MediaPipe face tracking coordinates. Must gracefully degrade if camera is unavailable.
  - **Status**: **Idea** (Dependencies missing)

- [x] **Self-Healing Codebase (Jules Auto-PR)**
  - **Description**: Allow James to autonomously fix runtime errors or implement requested features by generating code and opening a Pull Request.
  - **Wow Factor**: "Sir, I noticed a crash in the `kasa_agent`. I've analyzed the logs and prepared a fix for your review."
  - **User Impact**: Automated maintenance; the assistant fixes itself.
  - **Technical Notes**: Leverage `JulesAgent` with `automationMode="AUTO_CREATE_PR"`. Needs a log monitoring service that triggers Jules on specific exception patterns.
  - **Status**: **Implemented** (Log monitoring service triggers proactive voice notification; `JulesAgent` creates PRs on demand)

- [x] **The "War Room" Dashboard**
  - **Description**: A voice-activated "command center" view that aggregates Trello tickets, active GitHub PRs, and system status into a sci-fi style grid layout.
  - **Wow Factor**: "James, show me the situation report." -> Screen transforms into a high-density information display.
  - **User Impact**: Instant context on project health without checking 5 different browser tabs.
  - **Technical Notes**: React component using CSS Grid/bento-box style. Needs to aggregate data from `TrelloAgent` and `JulesAgent` concurrently.
  - **Status**: **Implemented**

- [ ] **Deep OS Control (Cross-Platform)**
  - **Description**: Give James control over the operating system beyond the app window. "James, turn off WiFi", "Open Spotify", "Organize my desktop".
  - **Wow Factor**: True digital assistant capabilities; breaking out of the "sandbox".
  - **User Impact**: Redefines the assistant as an OS interface rather than just an app.
  - **Technical Notes**: Python `subprocess` calls. abstracting OS-specific commands (PowerShell for Windows, AppleScript/zsh for macOS). Security permission handling is critical.
  - **Status**: **Idea**

- [ ] **War Room: Fleet Command & Git Ops**
  - **Description**: A visual UI for managing multiple JulesAgents working on tasks across multiple repos. Includes controls for voice-activated or manual git branch merges.
  - **Wow Factor**: "Commanding a fleet of agents across the entire codebase ecosystem."
  - **User Impact**: Orchestrate complex multi-repo development from a single view.
  - **Technical Notes**: Leverage `JulesAgent` source discovery. Implement simple git merge wrappers (conflict-free). React UI extensions.
  - **Status**: **Idea**

---

## 🧩 Smart Enhancements (Coding Focus)
*High-impact improvements that make the assistant feel sharper and more capable.*

- [ ] **Deep Git Context Awareness**
  - **Description**: James should know the *current* local state—which branch is active, what files are staged, and the diff of the working directory—before sending a request to Jules.
  - **Wow Factor**: "James, why is this failing?" (James reads the local error log and the specific file diff you just made).
  - **User Impact**: Reduces the need to "explain" the context to the AI.
  - **Technical Notes**: Extend `JulesAgent` to read `.git` status/diffs locally via `subprocess` (avoiding heavy `GitPython` dependency if possible) and prepend to the prompt.
  - **Status**: **Partially Implemented** (Basic repo source linking exists, local diffs missing)

- [ ] **Visual Task Scheduling**
  - **Description**: When a Jules task is long-running (e.g., "Refactor the backend"), show a dedicated progress bar or "working" visualization in the UI, rather than just a spinner.
  - **Wow Factor**: Visualizing the "thought process" or "files being touched" makes the wait feel productive.
  - **User Impact**: Certainty that the agent is not stuck.
  - **Technical Notes**: Parse the streaming `activities` from `JulesAgent` to update a dynamic UI list of "Completed Steps".
  - **Status**: **Designed**

- [ ] **Architectural Memory (RAG)**
  - **Description**: A long-term memory system where James stores architectural decisions, project constraints, and "lessons learned" to avoid repeating mistakes.
  - **Wow Factor**: "Sir, remember we decided against using `requests` in favor of `httpx` last week."
  - **User Impact**: Consistency across long development cycles.
  - **Technical Notes**: Vector store (ChromaDB or simple JSONL) for retrieving relevant context based on current task.
  - **Status**: **Idea**

- [ ] **Proactive "Bug Hunting" Mode**
  - **Description**: A background mode where James watches for file saves, runs the relevant tests silently, and speaks up *only* if something breaks.
  - **Wow Factor**: "Sir, that last edit to `server.py` seems to have broken the login test."
  - **User Impact**: Catch regressions immediately.
  - **Technical Notes**: File watcher -> `pytest` runner -> Voice notification trigger.
  - **Status**: **Idea**

---

## 🛠 Quality of Life & Polish
*Features that make daily use smoother, faster, and more delightful.*

- [ ] **Smart Error Interception**
  - **Description**: If a terminal command run by the user (or agent) fails, James automatically parses the stderr and offers a one-sentence explanation/fix.
  - **User Impact**: Faster debugging.
  - **Status**: **Idea**

- [ ] **Voice-Controlled Git Actions**
  - **Description**: Simple voice commands for routine git operations. "James, commit this as 'Fix login bug' and push."
  - **User Impact**: Hands-free version control.
  - **Technical Notes**: Wrap `git` CLI commands in `AudioLoop` tools.
  - **Status**: **Idea**

- [ ] **Video Feed Optimization**
  - **Description**: Ensure the camera feed doesn't freeze when the agent is "thinking" (blocking main thread).
  - **Technical Notes**: Move video processing to a WebWorker or optimize the Python asyncio loop.
  - **Status**: **Idea** (Optimization)

- [ ] **Offline Fallback Mode**
  - **Description**: When the internet is down, James should not crash but switch to a limited "Offline" mode (e.g., simple timer/local file commands only).
  - **User Impact**: Reliability. Prevents the "I'm sorry, I can't do that" frustration loop.
  - **Status**: **Idea**

---

## 🛑 Deprecated / Removed
- *Legacy "Chatbot" Interfaces*: We are moving towards purely multimodal/agentic interactions.
