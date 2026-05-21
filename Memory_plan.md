# A.D.A V2: "Grows With You" Implementation Plan

This document outlines the strategy to integrate "grows with you" capabilities into A.D.A V2, inspired by Hermes Agent. The goal is to evolve A.D.A from a reactive assistant to a proactive, learning system with persistent memory and autonomous routines.

## 1. Learning About the User (User Modeling & Persistence) [DONE]

**Goal:** Build a deepening model of the user across sessions, capturing preferences, constraints, and implicit feedback to personalize interactions.

**Implementation Plan:**
1.  **User Profile Schema [DONE]:** Extended `ProjectManager` to include `get_user_profile` and `update_user_profile` to store and load `user_profile.json` in the root workspace.
2.  **Implicit Learning Engine [DONE]:** Added `_implicit_learning_task` in `Ada` (AudioLoop) that runs every 5 minutes, reading `chat_history.jsonl` since the last check and summarizing new insights into `ProjectManager.update_user_profile` using `gemini-2.5-flash`.
3.  **Dialectic User Modeling [DONE]:** Implemented an `update_user_preferences` tool, allowing the agent to actively reconcile and explicitly persist stated preferences to the user profile via user instruction.
4.  **Integration with Agent Context [DONE]:** Modified `_get_live_connect_config` in `ada.py` to dynamically load the `user_profile.json` and append the user's constraints and preferences directly into the system prompt.

**Expected Benefits:**
*   More personalized and relevant responses.
*   Reduced need for the user to repeat constraints or preferences.
*   A feeling of continuity and a deeper relationship with the agent.

## 2. The Core Agent (Autonomous Skill Generation & Learning Loop) [DONE]

**Goal:** Enable A.D.A to autonomously create, refine, and persist new skills based on successful complex task resolutions.

**Implementation Plan:**
1.  **Procedural Memory (Skills Hub) [DONE]:** Created a dedicated directory (`projects/skills/`) to store these generated skills as Python scripts.
2.  **Dynamic Tool Registration [DONE]:** Extended `ToolRegistry` in `backend/tool_registry.py` to dynamically load (`load_skills`) and expose these newly generated skills as available tools (`get_dynamic_tool_declarations`). Added `create_new_skill` tool to `backend/tools.py`.
3.  **Self-Improvement Loop [DONE]:** Added a feedback mechanism in `ToolRegistry.dispatch` where exceptions from dynamic skills are caught and returned with a stack trace and a prompt encouraging the LLM to rewrite the code.

**Expected Benefits:**
*   A.D.A becomes exponentially more capable over time.
*   Complex, multi-step tasks become single-command executions.
*   Reduces the need for manual tool authoring by human developers.

## 3. Daily Routines (Natural Language Cron Scheduling)

**Goal:** Implement scheduled, unattended automations managed entirely via natural language.

**Implementation Plan:**
1.  **Cron Scheduler Integration:** Integrate a lightweight Python cron library (e.g., `APScheduler`) into `backend/server.py` or as a standalone `CronAgent`.
2.  **Natural Language Parsing:** Create a tool (e.g., `schedule_routine`) that accepts natural language (e.g., "Every morning at 8 AM, summarize my unread PRs") and converts it into a cron expression and an executable task payload.
3.  **Unattended Execution Context:** Allow the `AutomationEngine` to spin up headless, isolated agent instances to run these scheduled tasks without interrupting the user's active UI session.
4.  **Cross-Platform Delivery:** Ensure routine outputs (e.g., "Daily Briefing") can be routed to the appropriate channel (UI dashboard, Slack, Voice via `notify_user`).

**Expected Benefits:**
*   Proactive assistance without prompting.
*   Seamless handling of repetitive maintenance tasks (backups, audits, daily summaries).
*   Transforms A.D.A into a true background collaborator.

## 4. Context Keeping Memory into Everyday Interactions

**Goal:** Provide the agent with instantaneous, deep recall of past conversations and project decisions, eliminating the "blank slate" problem.

**Implementation Plan:**
1.  **SQLite/FTS5 Implementation:** Migrate chat logs and architectural decisions from flat text/JSON files to a local SQLite database utilizing FTS5 (Full-Text Search).
2.  **Vector/Semantic Search (Optional Enhancement):** Supplement FTS5 with local embeddings (using `OllamaAgent`) for semantic retrieval of past context.
3.  **Autonomous Context Nudging:** Implement a background observer that monitors the current conversation stream. When it detects topics discussed previously, it silently retrieves the historical context and "nudges" the main agent by injecting it into the context window.
4.  **Cross-Session Search Tool:** Provide a specific tool (`search_memory`) allowing the agent to explicitly query its own historical database when uncertain.

**Expected Benefits:**
*   Eliminates repetitive context-setting by the user.
*   Prevents the agent from contradicting past architectural decisions.
*   Creates a seamless, ongoing dialogue that truly feels like working with a long-term colleague.
