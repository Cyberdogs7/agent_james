# Product Backlog & Vision

This document serves as the single source of truth for the evolution of the A.D.A (Advanced Design Assistant) platform. It outlines the roadmap towards a "JARVIS-level" intelligence, prioritizing cinematic interactions, proactive assistance, and deep integration.

**North Star:** "Proactive, context-aware, cinematic, useful, and occasionally delightful."
**Persona:** James (British, witty, professional).

---

## 🏛 Phase 1: Foundation (Active & Partially Implemented)
*Core capabilities that are live in the codebase but evolving.*

- [x] **The Forge (Generative Manufacturing)**
  - **Description**: "I need a bracket for this camera." -> Generates a 3D model (STL) from a description, slices it, and sends it to the 3D printer automatically.
  - **Wow Factor**: Turning a voice command into a physical object.
  - **User Impact**: Rapid prototyping speed.
  - **Technical Notes**: `backend/cad_agent.py` (Generation), `backend/printer_agent.py` (Discovery/Slicing/Printing) are active.
  - **Status**: Partially Implemented

- [x] **The Oracle (Predictive Architecture)**
  - **Description**: Analyzes codebase changes to predict future technical debt, security risks, or scalability bottlenecks *before* they are committed. Currently detects "Smart Merge Candidates".
  - **Wow Factor**: A senior architect from the future guarding the codebase.
  - **User Impact**: Prevents long-term architectural decay.
  - **Technical Notes**: `backend/automation_engine.py` (Smart Merge Candidate detection active).
  - **Status**: Partially Implemented

- [x] **The Sentry (Security Overwatch)**
  - **Description**: A dedicated background agent that monitors file system changes, network ports, and suspicious API calls in real-time. Currently monitors stalled PRs and Jules sessions.
  - **Wow Factor**: "Sir, I've detected an unauthorized outbound connection on port 8080."
  - **User Impact**: Passive security and peace of mind without manual auditing.
  - **Technical Notes**: `backend/automation_engine.py` (Stalled item checks active). FS/Network monitoring pending.
  - **Status**: Partially Implemented

- [x] **Temporal Echoes (Contextual Memory)**
  - **Description**: Automatically surfaces relevant past decisions, mistakes, or preferences when the user starts a similar task.
  - **Wow Factor**: "Sir, last time you touched the auth system, you broke the login page. Be careful with the token expiration."
  - **User Impact**: Prevents regression and reinforces learning.
  - **Technical Notes**: `backend/memory_manager.py` (Vector search active). Integration with chat flow pending.
  - **Status**: Partially Implemented

- [x] **The Historian (Conversational Git)**
  - **Description**: Analyzes git diffs and explains changes in plain English with narrative flair. Can answer "Why did we remove the cache layer?" by analyzing commit history.
  - **Wow Factor**: "James, what did we just break?" -> "It appears the frontend team inverted the auth logic in the login component."
  - **User Impact**: Rapid understanding of complex merges without reading diffs.
  - **Technical Notes**: `backend/git_agent.py` (Diff retrieval), `backend/jules_agent.py` (Diff formatting). Narrative layer pending.
  - **Status**: Partially Implemented

- [x] **System Pulse (Visual Heartbeat)**
  - **Description**: Visualizing the heartbeat of the automation engine (CPU/Memory/Tasks/Agents) in the UI.
  - **Wow Factor**: Seeing the system "breathe" and knowing it's alive.
  - **User Impact**: System confidence and situational awareness.
  - **Technical Notes**: `backend/ada.py` (get_dashboard_data active). Visualizer pending.
  - **Status**: Partially Implemented

- [x] **Neural Sync (Adaptive Soundscapes)**
  - **Description**: Generates or selects ambient music based on system load, coding intensity (keystroke velocity), or detected user sentiment.
  - **Wow Factor**: The soundtrack of your work adapts to your flow state.
  - **User Impact**: Increases immersion and focus.
  - **Technical Notes**: `backend/music_agent.py` (Playback/Search active). Adaptive logic pending.
  - **Status**: Partially Implemented

- [x] **Biometric Sentinel (Voiceprint Security)**
  - **Description**: Identifies the current user via Voice ID and Face ID to tailor context and permissions. Unlock system by saying a passphrase.
  - **Wow Factor**: "Good evening, Mr. Stark" vs "Access Denied".
  - **User Impact**: Seamless multi-user support and security.
  - **Technical Notes**: `backend/capture_face.py` (Face presence detection active). Voiceprint authentication pending.
  - **Status**: Partially Implemented

---

## 🚀 Phase 2: Expansion (Next Up)
*High-impact features to be built next.*

- [ ] **Project Recall (Photographic Memory)**
  - **Description**: A local, privacy-first vector database of everything the user has seen on screen, searchable by natural language.
  - **Wow Factor**: "James, show me that article about quantum computing I was reading last Tuesday."
  - **User Impact**: Infinite recall of context without bookmarking.
  - **Technical Notes**: `backend/proactive_agent.py` (Screen analysis active). Need to link Vision results to `backend/memory_manager.py` for storage.
  - **Status**: Designed / Partially Implemented

- [ ] **Protocol: FOCUS (Cinematic Mode)**
  - **Description**: A single voice command ("James, let's work") that dims the smart lights (Kasa), puts the dashboard in full screen, and plays a "boot up" sound.
  - **Wow Factor**: The room physically changes to match the user's intent.
  - **User Impact**: Instant flow state induction.
  - **Technical Notes**: `backend/kasa_agent.py` (Lights) + `backend/os_agent.py` (Control) active. Orchestration logic needed.
  - **Status**: Idea

- [ ] **Deep OS Integration (Ghost in the Machine)**
  - **Description**: Advanced control over the operating system beyond simple app launching (window tiling, file indexing, workflow automation).
  - **Wow Factor**: Blurring the line between the assistant and the OS.
  - **User Impact**: Drastically speeds up complex system workflows.
  - **Technical Notes**: `backend/os_agent.py` active (launch/volume/lock/sleep). Window management pending.
  - **Status**: Partially Implemented

- [ ] **Dream State (Generative Idle Mode)**
  - **Description**: While the user is away (AFK), the assistant automatically switches to a low-priority branch and runs optimization tasks: writing unit tests, refactoring legacy code, or generating documentation.
  - **Wow Factor**: "Sir, while you were getting coffee, I took the liberty of writing test coverage for the new auth module."
  - **User Impact**: Massive productivity gain; the system works while you sleep.
  - **Technical Notes**: `ProactiveAgent` detects idle state -> Spawns `JulesAgent` on `optimization` branch.
  - **Status**: Idea

- [ ] **Babel Fish (Real-time Meeting Assistant)**
  - **Description**: Live transcription and sentiment analysis of Zoom/Meet calls with real-time "cue cards" for the user.
  - **Wow Factor**: "Sir, the client seems hesitant about the budget. I suggest focusing on ROI."
  - **User Impact**: Superhuman social awareness and meeting effectiveness.
  - **Technical Notes**: Audio loop -> Whisper -> LLM Analysis -> HUD Overlay.
  - **Status**: Idea

---

## 🔮 Phase 3: The Vision (Future)
*Long-term, aspirational, and slightly sci-fi.*

- [ ] **The Construct (Holo-Table 2.0)**
  - **Description**: An interactive 3D environment ("The Construct") where the user can manipulate code modules, server infrastructure, and database schemas as physical objects.
  - **Wow Factor**: "I need guns. Lots of guns." -> Summoning a fleet of testing agents instantly.
  - **User Impact**: Spatial reasoning applied to abstract software architecture.
  - **Technical Notes**: VR/AR support (`@react-three/fiber`) pending.
  - **Status**: Idea

- [ ] **Telepathy (Ghost Text)**
  - **Description**: Predicts what the user is about to type next and displays it as ghost text (system-wide), allowing them to accept it with a tab.
  - **Wow Factor**: "It knew what I was going to type before I did."
  - **User Impact**: Massive productivity boost.
  - **Technical Notes**: Local LLM inference on keystrokes + OS overlay.
  - **Status**: Idea

- [ ] **The Chameleon (Dynamic Theming)**
  - **Description**: The UI automatically adapts its theme and layout based on the current task context (e.g., Coding -> Dark/Terminal, Writing -> Calm/Paper, Crisis -> Red Alert).
  - **Wow Factor**: The interface feels like a living organism reacting to the situation.
  - **User Impact**: Reduces cognitive load by matching visual environment to mental state.
  - **Technical Notes**: `ProactiveAgent` detects context -> `ThemeManager` updates CSS variables.
  - **Status**: Idea

- [ ] **The Eye of Agamotto (Visual Time Travel)**
  - **Description**: Allows rewinding the *visual state* of the screen/dashboard, not just data. "Show me what the dashboard looked like 10 minutes ago."
  - **Wow Factor**: Scrubbing through the visual history of your work session.
  - **User Impact**: Visual context recovery for debugging UI glitches or recalling fleeting notifications.
  - **Technical Notes**: Snapshotting visual state in `MemoryManager`.
  - **Status**: Idea

- [ ] **Vocal Chameleon (Dynamic Personality)**
  - **Description**: The assistant dynamically adjusts its voice tone, speed, and vocabulary based on the context (e.g., whispering at night, authoritative during a crisis, casual during brainstorming).
  - **Wow Factor**: "Why are you whispering?" -> "It is 2 AM, Sir."
  - **User Impact**: Increases social presence and reduces friction in different environments.
  - **Technical Notes**: Context detection -> Dynamic TTS parameter adjustment.
  - **Status**: Idea

---

## 🛠 Quality of Life & Polish
*Features that make daily use smoother, faster, and more delightful.*

- [ ] **Latency "Magic Tricks"**
  - **Description**: UX hacks to mask latency (filler sounds, instant UI feedback).
  - **Wow Factor**: The assistant feels instant and alive.
  - **User Impact**: Maintains immersion.
  - **Technical Notes**: Client-side prediction/optimistic UI.
  - **Status**: Idea

- [ ] **Audio Polish**
  - **Description**: High-fidelity sound effects for UI interactions and system events.
  - **Wow Factor**: Cinematic sound design.
  - **User Impact**: Delight and feedback.
  - **Technical Notes**: `backend/music_agent.py` enhancement.
  - **Status**: Idea
