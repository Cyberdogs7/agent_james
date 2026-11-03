# Agent Context: Agent James Architecture

This document provides context for agents modifying this codebase regarding the overall architectural direction of Agent James.

## The Goal
Agent James is a voice-assistant that executes tasks, manages smart devices, and provides various utility functions.

## Code Constraints
- `backend/agent_james.py`: The central nervous system. Manages the main Audio Loop (`AgentJames` class), tool registry, and routing logic. Keep heavy logic out of here; delegate to specific agents.
- **Dependency Management:** This project uses specific virtual environments. Ensure you do not arbitrarily add new global dependencies. Testing must be done via the provided `pytest` wrapper script or explicitly activated environment.

## Pull Request Naming
- 🎨 Palette: [UX improvement]
- 🧹 [code health improvement description]
- 🧪 [testing improvement description]

## Durable Knowledge Protocol
Agents **MUST NOT** rely on conversational history to remember the state of a project, the architecture, or past decisions. 
- The repository itself holds the working knowledge.
- Agents must actively read `docs/ARCHITECTURE.md` or issues within `docs/issues/` before starting tasks.
- When an architectural decision is made, or an issue is resolved, agents must update the corresponding markdown file in the repository to persist this knowledge for future fleet members.
