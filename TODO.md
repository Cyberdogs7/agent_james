# Product Backlog & Vision

This document serves as the single source of truth for the evolution of the A.D.A (Advanced Design Assistant) platform. It outlines the roadmap towards a "JARVIS-level" intelligence, prioritizing cinematic interactions, proactive assistance, and deep integration with development workflows.

**North Star:** "Proactive, context-aware, cinematic, useful, and occasionally delightful."
**Persona:** James (British, witty, professional).

---

## 🌟 WOW / JARVIS-Level Features
*Big, bold, aspirational capabilities that define identity.*

- [x] **Holographic Avatar Interface**
  - **Description**: Replace the static UI with a reactive 3D avatar (using `three-vrm`) that lip-syncs to ADA's voice, tracks the user's face (via camera), and displays emotions (thinking, listening, happy).
  - **Wow Factor**: Transforms the assistant from a voice in a box to a "physical" presence in the room. The avatar looks at you when you speak.
  - **User Impact**: Higher engagement and immediate visual feedback on the agent's state (listening vs. processing).
  - **Technical Notes**: Requires installing `@pixiv/three-vrm`. Need to map audio amplitude/visemes to blend shapes and head rotation to MediaPipe face tracking coordinates. Must gracefully degrade if camera is unavailable.
  - **Status**: **Implemented**
  - [x] Subtask: Dependencies & Basic Rendering
  - [x] Subtask: Audio Lip Sync & Idle Animation
  - [x] Subtask: Per-Project Avatar Loading
  - [x] Subtask: Head Tracking (MediaPipe)

- [ ] **Real-World Vision (VLA)**
  - **Description**: Allow James to "see" and identify physical objects held up to the camera. "James, what size screw is this?" or "Does this 3D print look like the model?"
  - **Wow Factor**: The assistant bridges the gap between digital and physical reality.
  - **User Impact**: Invaluable for hardware debugging and inventory management.
  - **Technical Notes**: Ingest video frames into a Vision-Language Model (VLM) or specialized YOLO models for object detection.
  - **Status**: **Idea**

- [ ] **Deep OS Control (Cross-Platform)**
  - **Description**: Give James control over the operating system beyond the app window. "James, turn off WiFi", "Open Spotify", "Organize my desktop".
  - **Wow Factor**: True digital assistant capabilities; breaking out of the "sandbox".
  - **User Impact**: Redefines the assistant as an OS interface rather than just an app.
  - **Technical Notes**: Python `subprocess` calls. abstracting OS-specific commands (PowerShell for Windows, AppleScript/zsh for macOS). Security permission handling is critical.
  - **Status**: **Implemented**
  - [x] Subtask: App Launching (Cross-platform)
  - [x] Subtask: Volume Control
  - [x] Subtask: System Lock / Sleep

- [x] **Per-Project Fleet & Security Isolation**
  - **Description**: Migrated `fleet.json` and GitHub tokens from global scope to individual project directories.
  - **Wow Factor**: Seamlessly switching projects changes the entire context (repos, auth) without leaks.
  - **User Impact**: Better security (token not in global file) and cleaner multi-project workflow.
  - **Status**: **Implemented**

---

## 🧩 Smart Enhancements (Coding Focus)
*High-impact improvements that make the assistant feel sharper and more capable.*

- [x] **Deep Git Context Awareness**
  - **Description**: James should know the *current* local state—which branch is active, what files are staged, and the diff of the working directory—before sending a request to Jules.
  - **Wow Factor**: "James, why is this failing?" (James reads the local error log and the specific file diff you just made).
  - **User Impact**: Reduces the need to "explain" the context to the AI.
  - **Technical Notes**: Extend `JulesAgent` to read `.git` status/diffs locally via `subprocess` (avoiding heavy `GitPython` dependency if possible) and prepend to the prompt.
  - **Status**: **Implemented**

- [ ] **Local "Brain" (Offline Mode)**
  - **Description**: When the internet is down (or for privacy), switch to a local LLM (e.g., Llama 3 on GPU) for basic commands (timers, local device control).
  - **Wow Factor**: "Sir, the network is down, but I am still operational."
  - **User Impact**: Reliability and privacy.
  - **Technical Notes**: Integration with `ollama` or `llama.cpp` python bindings. Check `check_cuda.py` for hardware capability.
  - **Status**: **Idea**

- [x] **Visual Task Scheduling**
  - **Description**: When a Jules task is long-running (e.g., "Refactor the backend"), show a dedicated progress bar or "working" visualization in the UI, rather than just a spinner.
  - **Wow Factor**: Visualizing the "thought process" or "files being touched" makes the wait feel productive.
  - **User Impact**: Certainty that the agent is not stuck.
  - **Technical Notes**: Parse the streaming `activities` from `JulesAgent` to update a dynamic UI list of "Completed Steps".
  - **Status**: **Implemented**

- [ ] **Architectural Memory (RAG)**
  - **Description**: A long-term memory system where James stores architectural decisions, project constraints, and "lessons learned" to avoid repeating mistakes.
  - **Wow Factor**: "Sir, remember we decided against using `requests` in favor of `httpx` last week."
  - **User Impact**: Consistency across long development cycles.
  - **Technical Notes**: Vector store (ChromaDB or simple JSONL) for retrieving relevant context based on current task.
  - **Status**: **Implemented**
  - [x] Subtask: Memory Manager (JSONL + Embeddings)
  - [x] Subtask: Project Integration
  - [x] Subtask: Ada Tool & RAG Integration

- [x] **Proactive "Bug Hunting" Mode**
  - **Description**: A background mode where James watches for file saves, runs the relevant tests silently, and speaks up *only* if something breaks.
  - **Wow Factor**: "Sir, that last edit to `server.py` seems to have broken the login test."
  - **User Impact**: Catch regressions immediately.
  - **Technical Notes**: File watcher -> `pytest` runner -> Voice notification trigger.
  - **Status**: **Implemented**

---

## 🛠 Quality of Life & Polish
*Features that make daily use smoother, faster, and more delightful.*

- [x] **Voice-Controlled Git Actions (Full Suite)**
  - **Description**: Expand voice git controls beyond simple merging. "James, commit this as 'Fix login bug' and push."
  - **User Impact**: Hands-free version control.
  - **Technical Notes**: Wrap `git commit`, `git push`, `git pull` in `AudioLoop` tools.
  - **Status**: **Implemented**

- [ ] **Video Feed Optimization**
  - **Description**: Ensure the camera feed doesn't freeze when the agent is "thinking" (blocking main thread).
  - **Technical Notes**: Move video processing to a WebWorker or optimize the Python asyncio loop.
  - **Status**: **Idea** (Optimization)

---

## 🛑 Deprecated / Removed
- *Legacy "Chatbot" Interfaces*: We are moving towards purely multimodal/agentic interactions.
