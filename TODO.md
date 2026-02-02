# Product Backlog & Vision

This document serves as the single source of truth for the evolution of the A.D.A (Advanced Design Assistant) platform. It outlines the roadmap towards a "JARVIS-level" intelligence, prioritizing cinematic interactions, proactive assistance, and deep integration with development workflows.

**North Star:** "Proactive, context-aware, cinematic, useful, and occasionally delightful."
**Persona:** James (British, witty, professional).

---

## 🌟 WOW / JARVIS-Level Features
*Big, bold, aspirational capabilities that define identity.*

- [x] **Morning Briefing (Presence-Aware)**
  - **Description**: A daily intelligence report delivered verbally by James when the user first appears or speaks in the morning. Covers fleet status, PRs, and critical issues.
  - **Wow Factor**: "Good morning, Sir. I have your briefing. 3 PRs are pending, and the 'frontend' build is failing."
  - **User Impact**: Starts the day with high-level situational awareness.
  - **Technical Notes**: Triggered by schedule (09:00) but delivered only upon Face Auth or VAD (first interaction). Uses `AutomationEngine` to aggregate data.
  - **Status**: Implemented

- [x] **Smart Merge Suggestions (Fleet Command)**
  - **Description**: Proactive recommendations to merge Pull Requests that are passing CI and have been open for a set duration.
  - **Wow Factor**: "The 'fix-auth' PR is passing and has been open for 24 hours. Shall I merge it for you?"
  - **User Impact**: Reduces friction in the development lifecycle.
  - **Technical Notes**: Extends "Nagging Secretary" to include "Green & Old" PR detection. Uses `merge_pull_request` tool.
  - **Status**: Implemented

- [ ] **Adaptive Persona Engine**
  - **Description**: James detects user sentiment (frustration, focus, casual) via voice or text analysis and adjusts his personality.
  - **Behavior**:
    - *Frustrated*: Brief, direct, no jokes.
    - *Casual*: Witty, conversational.
    - *Focus*: Silent, only critical interruptions.
  - **Wow Factor**: Feels like a true partner that "reads the room."
  - **Technical Notes**: Use Gemini 1.5 Pro's native audio understanding or a lightweight local audio classifier to tag input sentiment before response generation.
  - **Status**: Idea

---

## 🧩 Smart Enhancements
*High-impact improvements that make the assistant feel sharper and more capable.*

- [x] **Self-Healing Automations**
  - **Description**: Automatically detect failed automation scripts and generate code fixes using Gemini.
  - **User Impact**: "The build script failed. I've analyzed the error and prepared a fix. Shall I apply it?"
  - **Technical Notes**: Catch exceptions in `AutomationEngine`, send traceback + code to Gemini, store patch, require user confirmation (Voice/UI) to apply.
  - **Status**: Implemented

- [x] **"The Nagging Secretary" (Smart Follow-up)**
  - **Description**: Proactive verbal nudges for stalled processes.
  - **Behavior**: Monitor "Pending" Jules sessions or PRs. If no movement for >2 hours, verbally intervene. "Sir, the frontend refactor is waiting for your review. Shall I merge it?"
  - **User Impact**: Prevents bottlenecks in the agent fleet.
  - **Technical Notes**: Logic needs to be added to `AutomationEngine` to track "time since last update" for specific states.
  - **Status**: Implemented

---

## 🛠 Quality of Life & Polish
*Features that make daily use smoother, faster, and more delightful.*

- [ ] **Swarm Mode (Multi-Agent Orchestration)**
  - **Description**: Enables hierarchical multi-agent tasks (e.g., "Refactor Auth" -> Frontend Agent + Backend Agent) by spawning specialized agents in parallel.
  - **Wow Factor**: Visualizing a coordinated attack on a complex problem with multiple agents working simultaneously in the War Room.
  - **Technical Notes**: Enhance `spawn_swarm_agent` to encode roles in session titles; update War Room to visualize agent roles and groupings.
  - **Status**: In Progress

- [ ] **Smart Interruption Handling**
  - **Description**: Better handling of user interruptions during speech. If the user speaks while James is talking, cut off immediately and listen (Barge-in).
  - **Technical Notes**: Tune VAD and audio output cancellation.
  - **Status**: Idea
