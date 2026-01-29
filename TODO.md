# Product Backlog & Vision

This document serves as the single source of truth for the evolution of the A.D.A (Advanced Design Assistant) platform. It outlines the roadmap towards a "JARVIS-level" intelligence, prioritizing cinematic interactions, proactive assistance, and deep integration with development workflows.

**North Star:** "Proactive, context-aware, cinematic, useful, and occasionally delightful."

---

## 🌟 WOW / JARVIS-Level Features
*Big, bold, aspirational capabilities that define identity.*

- [ ] **Holographic Avatar Interface**
  - **Description**: Replace the static UI with a reactive 3D avatar (using `three-vrm`) that lip-syncs to ADA's voice, tracks the user's face (via camera), and displays emotions (thinking, listening, happy).
  - **Wow Factor**: Transforms the assistant from a voice in a box to a "physical" presence in the room. The avatar looks at you when you speak.
  - **User Impact**: Higher engagement and immediate visual feedback on the agent's state (listening vs. processing).
  - **Technical Notes**: Requires installing `@pixiv/three-vrm`. Need to map audio amplitude/visemes to blend shapes and head rotation to MediaPipe face tracking coordinates.
  - **Status**: **Idea** (Dependencies missing)

- [ ] **"Jules" Self-Evolution (Meta-Programming)**
  - **Description**: Allow the user to ask ADA to modify its own source code to add simple features or fix bugs, handling the git flow automatically.
  - **Wow Factor**: "James, add a dark mode toggle to your interface." -> "Consider it done, Sir." (Screen flickers, UI updates).
  - **User Impact**: infinite customizability without leaving the flow.
  - **Technical Notes**: leveraged existing `JulesAgent` but needs a safe "sandbox" or specific "self-improvement" mode where the context is the `ada_v2` repo itself.
  - **Status**: **Idea** (Foundation exists in `JulesAgent`)

- [ ] **The "War Room" Dashboard**
  - **Description**: A voice-activated "command center" view that aggregates Trello tickets, active GitHub PRs, and system status into a sci-fi style grid layout.
  - **Wow Factor**: "James, show me the situation report." -> Screen transforms into a high-density information display.
  - **User Impact**: Instant context on project health without checking 5 different browser tabs.
  - **Technical Notes**: React component using CSS Grid/bento-box style. Needs to aggregate data from `TrelloAgent` and `JulesAgent` concurrently.
  - **Status**: **Idea**

---

## 🧩 Smart Enhancements (Coding Focus)
*High-impact improvements that make the assistant feel sharper and more capable.*

- [ ] **Deep Git Context Awareness**
  - **Description**: ADA should know the *current* local state—which branch is active, what files are staged, and the diff of the working directory—before sending a request to Jules.
  - **Wow Factor**: "James, why is this failing?" (ADA reads the local error log and the specific file diff you just made).
  - **User Impact**: Reduces the need to "explain" the context to the AI.
  - **Technical Notes**: Add a `LocalGitAgent` or extend `JulesAgent` to read `.git` status/diffs locally and prepend to the prompt.
  - **Status**: **Partially Implemented** (Basic source context exists, local state is missing)

- [ ] **Visual Task Scheduling**
  - **Description**: When a Jules task is long-running (e.g., "Refactor the backend"), show a dedicated progress bar or "working" visualization in the UI, rather than just a spinner.
  - **Wow Factor**: Visualizing the "thought process" or "files being touched" makes the wait feel productive.
  - **User Impact**: Certainty that the agent is not stuck.
  - **Technical Notes**: Parse the streaming `activities` from `JulesAgent` to update a dynamic UI list of "Completed Steps".
  - **Status**: **Designed**

- [ ] **Proactive "Bug Hunting" Mode**
  - **Description**: A background mode where ADA watches for file saves, runs the relevant tests silently, and speaks up *only* if something breaks.
  - **Wow Factor**: "Sir, that last edit to `server.py` seems to have broken the login test."
  - **User Impact**: Catch regressions immediately.
  - **Technical Notes**: File watcher -> `pytest` runner -> Voice notification trigger.
  - **Status**: **Idea**

---

## 🛠 Quality of Life & Polish
*Features that make daily use smoother, faster, and more delightful.*

- [ ] **Voice-Controlled Git Actions**
  - **Description**: Simple voice commands for routine git operations. "James, commit this as 'Fix login bug' and push."
  - **User Impact**: Hands-free version control.
  - **Technical Notes**: Wrap `git` CLI commands in `AudioLoop` tools.
  - **Status**: **Idea**

- [ ] **Smart Error Interception**
  - **Description**: If a terminal command run by the user (or agent) fails, ADA automatically parses the stderr and offers a one-sentence explanation/fix.
  - **User Impact**: Faster debugging.
  - **Status**: **Idea**

- [ ] **Project-Specific Voice Settings**
  - **Description**: Persist the "Voice Name" and "Persona" per project in `project_manager.py`.
  - **User Impact**: "Writing Mode" feels different from "Coding Mode".
  - **Status**: **Partially Implemented** (Settings exist, UI for switching is basic)

- [ ] **Video Feed Optimization**
  - **Description**: Ensure the camera feed doesn't freeze when the agent is "thinking" (blocking main thread).
  - **Technical Notes**: Move video processing to a WebWorker or optimize the Python asyncio loop.
  - **Status**: **Idea** (Optimization)

---

## 🛑 Deprecated / Removed
- *Legacy "Chatbot" Interfaces*: We are moving towards purely multimodal/agentic interactions.
