import asyncio
import time
import json
import traceback
import os
import shutil
from datetime import datetime, timedelta
from dotenv import load_dotenv

try:
    from backend.github_client import GitHubClient
except ImportError:
    from github_client import GitHubClient

try:
    from google import genai
except ImportError:
    genai = None

load_dotenv()

class AutomationEngine:
    def __init__(self, task_manager, project_manager, ada_instance=None):
        self.task_manager = task_manager
        self.project_manager = project_manager
        self.ada = ada_instance
        self.running = False
        self.stop_event = asyncio.Event()
        self.last_nag_times = {} # {id: timestamp}
        self._last_stalled_check = 0

        # Briefing State
        self.briefing_status = "IDLE" # IDLE, PENDING, OFFERED, DELIVERED
        self.current_briefing_report = None
        self.briefing_time = "09:00" # Default

        # Configuration
        self.STALL_THRESHOLD = 7200  # 2 hours
        self.MERGE_CANDIDATE_THRESHOLD = 7200 # 2 hours (default)
        self.NAG_COOLDOWN = 86400    # 24 hours
        self.CHECK_INTERVAL = 300    # 5 minutes
        self._last_merge_check = 0

        # Gemini Client for Healing
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = None
        if self.api_key and genai:
             try:
                 self.client = genai.Client(api_key=self.api_key)
             except Exception as e:
                 print(f"[AutomationEngine] Failed to init Gemini client: {e}")

    async def start(self):
        """Starts the automation loop."""
        if self.running:
            return

        print("[AutomationEngine] Starting background loop...")
        self.running = True
        self.stop_event.clear()

        # Start Git Monitor Task
        asyncio.create_task(self._monitor_git_loop())

        while not self.stop_event.is_set():
            try:
                await self._check_schedules()
                await self._check_briefing_schedule()
            except Exception as e:
                print(f"[AutomationEngine] Error in loop: {e}")
                traceback.print_exc()

            # Check for stalled items (Nagging Secretary) every 5 minutes
            now = time.time()
            if now - self._last_stalled_check > self.CHECK_INTERVAL:
                try:
                    await self._monitor_stalled_items()
                    self._last_stalled_check = now
                except Exception as e:
                    print(f"[AutomationEngine] Error checking stalled items: {e}")
                    traceback.print_exc()

            # Check for smart merge candidates every 5 minutes
            if now - self._last_merge_check > self.CHECK_INTERVAL:
                try:
                    await self._monitor_merge_candidates()
                    self._last_merge_check = now
                except Exception as e:
                    print(f"[AutomationEngine] Error checking merge candidates: {e}")
                    traceback.print_exc()

            # Run every minute
            # We calculate sleep to align with the next minute start for cleaner scheduling
            now = time.time()
            sleep_time = 60 - (now % 60)
            try:
                await asyncio.wait_for(self.stop_event.wait(), timeout=sleep_time)
            except asyncio.TimeoutError:
                pass # Timeout means 60s passed, continue loop

    async def _monitor_git_loop(self):
        """Background task to monitor git repos for new commits."""
        print("[AutomationEngine] Starting Git monitor loop...")
        while not self.stop_event.is_set():
            try:
                events = await self.project_manager.monitor_git_repos()
                for event in events:
                    if event['type'] == 'git_commit':
                        print(f"[AutomationEngine] Detected Git Commit: {event.get('repo')} - {event.get('message')}")
                        await self.trigger_event('git_commit', event)
                        # Also announce via Ada if available
                        if self.ada:
                             await self.ada.handle_external_event(event)
            except Exception as e:
                print(f"[AutomationEngine] Git Monitor Error: {e}")

            await asyncio.sleep(30)

    def stop(self):
        """Stops the automation loop."""
        print("[AutomationEngine] Stopping...")
        self.stop_event.set()
        self.running = False

    async def _check_briefing_schedule(self):
        """Checks if it's time to generate the morning briefing."""
        now_dt = datetime.now()
        current_hm = now_dt.strftime("%H:%M")

        # Reset IDLE state at midnight (or just if date changes)
        # Simple logic: If it's briefing time and state is IDLE, generate.
        if current_hm == self.briefing_time and self.briefing_status == "IDLE":
             print("[AutomationEngine] Generating Morning Briefing...")
             try:
                 report = await self.project_manager.generate_fleet_report()
                 self.current_briefing_report = report
                 self.briefing_status = "PENDING"
                 print("[AutomationEngine] Briefing Generated. Status: PENDING")
             except Exception as e:
                 print(f"[AutomationEngine] Failed to generate briefing: {e}")

        # Reset logic: If it's NOT briefing time (e.g. 09:01), ensure we don't re-trigger tomorrow if we stay PENDING?
        # Ideally we reset to IDLE at midnight.
        if current_hm == "00:00":
            self.briefing_status = "IDLE"
            self.current_briefing_report = None

    async def _monitor_merge_candidates(self):
        """
        Smart Merge Suggestions (Fleet Command):
        Identifies PRs that are:
        1. Open
        2. Passing CI (Green)
        3. Stable (Open for > 24 hours)
        4. Mergeable (No conflicts)
        """
        print("[AutomationEngine] Checking for smart merge candidates...")
        now = time.time()
        token = self.project_manager.get_github_token()
        if not token: return

        client = GitHubClient(token)
        fleet = self.project_manager.load_fleet()

        for repo in fleet:
            try:
                owner = repo.get('owner')
                name = repo.get('name')
                if not owner or not name: continue

                # List PRs
                prs = await client.list_pull_requests(owner, name)
                if not prs: continue

                for pr in prs:
                    pr_url = pr.get('html_url')
                    title = pr.get('title')
                    number = pr.get('number')

                    # 1. Check Age
                    created_at_str = pr.get('created_at')
                    if not created_at_str: continue
                    if created_at_str.endswith('Z'): created_at_str = created_at_str[:-1]
                    created_dt = datetime.fromisoformat(created_at_str)
                    age_seconds = (datetime.utcnow() - created_dt).total_seconds()

                    # Read dynamic threshold from config (default to constant if not set)
                    # Support overriding per project or global
                    threshold = self.project_manager.get_project_config().get("auto_merge_threshold", self.MERGE_CANDIDATE_THRESHOLD)

                    if age_seconds < threshold:
                        continue # Too young

                    # Check cooldown
                    last_nag = self.last_nag_times.get(f"merge_{pr_url}", 0)
                    if now - last_nag < self.NAG_COOLDOWN:
                         continue

                    # 2. Check Mergeability (Detailed Fetch)
                    full_pr = await client.get_pull_request(owner, name, number)
                    if not full_pr or not full_pr.get('mergeable'):
                        continue # Conflicts or unknown state

                    # 3. Check CI Status (Head Commit)
                    head_sha = full_pr.get('head', {}).get('sha')
                    if not head_sha: continue

                    # Check Combined Status
                    status = await client.get_commit_status(owner, name, head_sha)
                    state = status.get('state', 'pending') # pending, success, failure, error

                    # Also check Check Runs (Actions) if state is not explicitly failure
                    # GitHub API 'status' covers legacy statuses. 'check-runs' covers Actions.
                    # A 'success' status is great. 'pending' might mean actions are running OR no legacy status exists.

                    is_green = False

                    if state == 'failure' or state == 'error':
                        is_green = False
                    else:
                        # State is 'success' OR 'pending' OR 'unknown'
                        # WE MUST CHECK ACTIONS regardless of 'success' status because
                        # 'success' might only refer to a 3rd party status (e.g. Netlify) while GitHub Actions fail.

                        check_runs = await client.get_check_runs(owner, name, head_sha)
                        if check_runs:
                            runs = check_runs.get('check_runs', [])
                            if not runs:
                                # No check runs found.
                                # If status was 'success', we can trust it.
                                # If status was 'pending', maybe it really is just pending with no checks?
                                is_green = (state == 'success')
                            else:
                                # Verify all completed and success
                                all_passed = True
                                for run in runs:
                                    # If any run failed, it's not green.
                                    if run.get('conclusion') == 'failure' or run.get('conclusion') == 'timed_out' or run.get('conclusion') == 'cancelled':
                                        all_passed = False
                                        break
                                    # If any run is still in progress, it's not "Green" yet (it's pending)
                                    if run.get('status') != 'completed':
                                        all_passed = False
                                        break

                                # If we passed all check runs, AND the commit status is not failing...
                                if all_passed:
                                    # If status is 'pending', but checks passed, it might be waiting on something else?
                                    # Safe bet: Require status to be success OR pending (if checks cover it)
                                    is_green = True
                                else:
                                    is_green = False
                        else:
                            # No checks system found via API. Trust Status.
                            is_green = (state == 'success')

                    if is_green:
                        msg = f"Sir, Pull Request #{number} ('{title}') on {owner}/{name} is passing all checks and has been stable for over 24 hours. Shall I merge it for you?"
                        print(f"[AutomationEngine] SMART MERGE: {msg}")
                        await self.ada.handle_external_event({
                            "type": "notification",
                            "message": msg
                        })
                        self.last_nag_times[f"merge_{pr_url}"] = now

            except Exception as e:
                print(f"[AutomationEngine] Error checking merge candidates for {repo.get('name')}: {e}")

    async def _monitor_stalled_items(self):
        """Checks for stalled Jules sessions and PRs and notifies (nags) the user."""
        print("[AutomationEngine] Checking for stalled items...")
        now = time.time()
        now_dt = datetime.now()

        # 1. Check Jules Sessions
        if self.ada and self.ada.jules_agent:
            sessions = await self.ada.jules_agent.list_sessions()
            for session in sessions:
                state = session.get('state')
                if state in ['COMPLETED', 'FAILED']:
                    continue

                # Check updateTime
                update_time_str = session.get('updateTime') or session.get('createTime')
                if not update_time_str:
                    continue

                try:
                     # Handle Z suffix
                    if update_time_str.endswith('Z'):
                         update_time_str = update_time_str[:-1]

                    # Simple parsing (assuming UTC for Z or local if no Z, but API usually returns UTC)
                    last_update_dt = datetime.fromisoformat(update_time_str)

                    # datetime.utcnow() returns naive UTC. If parsed date is naive and came from 'Z', it is UTC.
                    time_diff = (datetime.utcnow() - last_update_dt).total_seconds()

                    if time_diff > self.STALL_THRESHOLD:
                        session_id = session.get('name')
                        title = session.get('title', 'Untitled Task')

                        # Check cooldown
                        last_nag = self.last_nag_times.get(session_id, 0)
                        if now - last_nag > self.NAG_COOLDOWN:
                            msg = f"Sir, Jules session '{title}' has been stalling for over 2 hours. Shall I intervene?"
                            print(f"[AutomationEngine] NAGGING: {msg}")
                            await self.ada.handle_external_event({
                                "type": "notification",
                                "message": msg
                            })
                            self.last_nag_times[session_id] = now

                except Exception as e:
                    print(f"[AutomationEngine] Error checking session {session.get('name')}: {e}")

        # 2. Check Pull Requests
        token = self.project_manager.get_github_token()
        if token:
            client = GitHubClient(token)
            fleet = self.project_manager.load_fleet()

            for repo in fleet:
                try:
                    owner = repo.get('owner')
                    name = repo.get('name')
                    if not owner or not name: continue

                    prs = await client.list_pull_requests(owner, name)
                    if not prs: continue

                    for pr in prs:
                        updated_at_str = pr.get('updated_at')
                        if not updated_at_str: continue

                        if updated_at_str.endswith('Z'):
                            updated_at_str = updated_at_str[:-1]

                        updated_dt = datetime.fromisoformat(updated_at_str)
                        time_diff = (datetime.utcnow() - updated_dt).total_seconds()

                        if time_diff > self.STALL_THRESHOLD:
                            pr_url = pr.get('html_url')
                            title = pr.get('title')
                            number = pr.get('number')

                            last_nag = self.last_nag_times.get(pr_url, 0)
                            if now - last_nag > self.NAG_COOLDOWN:
                                msg = f"Sir, Pull Request #{number} ('{title}') on repository {owner}/{name} has been stalled for over 2 hours. Shall I merge it?"
                                print(f"[AutomationEngine] NAGGING: {msg}")
                                await self.ada.handle_external_event({
                                    "type": "notification",
                                    "message": msg
                                })
                                self.last_nag_times[pr_url] = now
                except Exception as e:
                     print(f"[AutomationEngine] Error checking PRs for {repo.get('name')}: {e}")

    async def _check_schedules(self):
        """Iterates through tasks and executes scheduled ones."""
        # Ensure we are using the current project's task list
        current_path = self.project_manager.get_current_project_path()

        # Create fresh manager for current project using the existing class
        # This avoids import issues regardless of execution context
        temp_manager = self.task_manager.__class__(current_path)
        tasks = temp_manager.list_tasks()

        now_ts = time.time()
        now_dt = datetime.now()

        for task in tasks:
            if task.get('status') != 'active':
                continue

            trigger = task.get('trigger', {})
            if trigger.get('type') != 'schedule':
                continue

            value = trigger.get('value')
            if not value: continue

            should_run = False

            # --- INTERVAL MODE ---
            if value.get('mode') == 'interval':
                interval_min = int(value.get('interval_minutes', 0))
                if interval_min > 0:
                    last_run = task.get('last_run')
                    if last_run:
                        # Check if enough time passed
                        elapsed_min = (now_ts - last_run) / 60
                        if elapsed_min >= interval_min:
                            should_run = True
                    else:
                        # First run: run now or schedule for later?
                        # Usually for interval, we run immediately or wait 1 interval.
                        # Let's say we run immediately upon creation/startup if never run.
                        should_run = True

            # --- DAILY MODE ---
            elif value.get('mode') == 'daily':
                target_time = value.get('time') # HH:MM
                days = value.get('days', []) # ["Mon", "Tue"] or empty for all

                if target_time:
                    # Check Day
                    current_day = now_dt.strftime("%a") # Mon, Tue...
                    if days and current_day not in days:
                        should_run = False
                    else:
                        # Check Time
                        # We want to run if current time matches HH:MM
                        # AND we haven't run today yet.
                        current_hm = now_dt.strftime("%H:%M")

                        if current_hm == target_time:
                            # Check if already ran today
                            last_run = task.get('last_run')
                            if last_run:
                                last_run_dt = datetime.fromtimestamp(last_run)
                                if last_run_dt.date() == now_dt.date():
                                    should_run = False # Already ran today
                                else:
                                    should_run = True
                            else:
                                should_run = True

            if should_run:
                print(f"[AutomationEngine] Triggering scheduled task: {task['title']}")
                await self._execute_task(task)

    async def trigger_event(self, event_type, event_data):
        """Public method to trigger event-based tasks."""
        # event_type: 'git_commit', 'trello_move', etc.
        # event_data: dict with details
        print(f"[AutomationEngine] Received event: {event_type}")

        # Fleet Scan: Check ALL projects for triggers
        projects = self.project_manager.list_projects()

        for project_name in projects:
            project_path = self.project_manager.get_project_path(project_name)
            temp_manager = self.task_manager.__class__(project_path)
            tasks = temp_manager.list_tasks()

            for task in tasks:
                if task.get('status') != 'active':
                    continue

                trigger = task.get('trigger', {})
                if trigger.get('type') == 'git' and event_type == 'git_commit':
                    # Check if repo matches
                    # Trigger value might be "owner/repo" or just "repo"
                    target_repo = trigger.get('value')
                    event_repo = event_data.get('repo') # "owner/name"

                    if target_repo and event_repo:
                        if target_repo == event_repo or target_repo in event_repo:
                            print(f"[AutomationEngine] Git Event matched task: '{task['title']}' in project '{project_name}'")
                            await self._execute_task(task, context=event_data, project_context=project_name)

    async def _generate_fix(self, script_path, error_log):
        """Uses Gemini to generate a fix for a failed script."""
        if not self.client:
            print("[AutomationEngine] Gemini Client not available for self-healing.")
            return None

        try:
            # Read script
            if not os.path.exists(script_path):
                return None

            with open(script_path, 'r', encoding='utf-8') as f:
                script_content = f.read()

            prompt = f"""
You are an expert Python debugger.
I am running a script that failed. I need you to analyze the code and the error trace, and provide the FULL FIXED CODE.

Original Script ({script_path}):
```python
{script_content}
```

Error Trace:
```
{error_log}
```

INSTRUCTIONS:
1. Return ONLY the python code block for the fixed file.
2. Do not include explanations outside the code block.
3. Fix the specific error mentioned.
"""
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model="gemini-2.0-flash", # Use a fast/capable model
                contents=prompt
            )

            if response.text:
                # Extract code block
                content = response.text
                if "```python" in content:
                    content = content.split("```python")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                return content
            return None

        except Exception as e:
            print(f"[AutomationEngine] Healing generation failed: {e}")
            return None

    def apply_fix(self, task_id):
        """Applies the proposed fix for a failed task."""
        current_path = self.project_manager.get_current_project_path()
        # Note: If tasks are cross-project, this might need better project resolution
        # But apply_fix is usually triggered from War Room which is context-aware?
        # Actually, self.task_manager is initialized with current project path in server.py
        # But if the failed task was from another project (triggered by git event), we need that project context.
        # For now, assume current project or scan.

        # Try to find task in current project first
        task = None

        # We need to find the task to get the 'healing' data
        tasks = self.task_manager.list_tasks()
        task = next((t for t in tasks if t['id'] == task_id), None)

        target_manager = self.task_manager

        if not task:
            # Check other projects? (Expensive/Complex)
            # For this iteration, assume current project context in War Room matches.
            return False, "Task not found."

        healing = task.get('healing')
        if not healing:
            return False, "No fix available for this task."

        original_path = healing.get('script_path')
        fix_code = healing.get('fix_code')

        if not original_path or not fix_code:
            return False, "Invalid healing data."

        try:
            # 1. Backup
            if os.path.exists(original_path):
                timestamp = int(time.time())
                backup_path = f"{original_path}.{timestamp}.bak"
                shutil.copy2(original_path, backup_path)

            # 2. Overwrite
            with open(original_path, 'w', encoding='utf-8') as f:
                f.write(fix_code)

            # 3. Reset Task
            updates = {
                "status": "active",
                "healing": None # Clear healing data
            }
            target_manager.update_task(task_id, updates)

            return True, f"Fix applied. Original backed up to {os.path.basename(backup_path)}."

        except Exception as e:
            return False, f"Failed to apply fix: {e}"

    async def _execute_task(self, task, context=None, project_context=None):
        """Executes the action defined in the task."""
        action = task.get('action', {})
        act_type = action.get('type')
        act_value = action.get('value')

        success = False
        result_msg = ""

        # Resolve TaskManager for the correct project
        if project_context:
            target_path = self.project_manager.get_project_path(project_context)
        else:
            target_path = self.project_manager.get_current_project_path()

        temp_manager = self.task_manager.__class__(target_path)

        try:
            if act_type == 'notify':
                msg = f"Automation '{task['title']}' triggered: {act_value}"
                print(f"[AutomationEngine] ACTION: Notify - {msg}")
                if self.ada:
                    # Send via UI notification
                    if self.ada.on_display_content:
                        self.ada.on_display_content({
                            "content_type": "notification",
                            "data": {"text": msg},
                            "duration": 10000
                        })
                    # Send via Slack
                    if self.ada.slack_agent:
                        asyncio.create_task(self.ada.slack_agent.send_message(msg))
                success = True

            elif act_type == 'jules_task':
                print(f"[AutomationEngine] ACTION: Jules Task")
                if self.ada:
                    prompt = ""
                    source = None
                    if isinstance(act_value, dict):
                        prompt = act_value.get('prompt')
                        source = act_value.get('source')
                    else:
                        prompt = str(act_value)

                    if project_context and project_context != self.project_manager.current_project:
                        prompt = f"Context: You are working on project '{project_context}'.\n\nTask: {prompt}"

                    if context:
                        # Append context to prompt
                        prompt += f"\n\nTrigger Context:\n{json.dumps(context, indent=2)}"

                    # Use ada's handler
                    # This launches a background task
                    msg = await self.ada.handle_jules_request(prompt, source)
                    result_msg = msg
                    success = True

            elif act_type == 'run_script':
                script_path = act_value
                # If relative, resolve to project path
                if not os.path.isabs(script_path):
                    script_path = str(target_path / script_path)

                print(f"[AutomationEngine] ACTION: Run Script - {script_path}")

                if not os.path.exists(script_path):
                    raise FileNotFoundError(f"Script not found: {script_path}")

                # Execute Script
                # Determine runner based on extension
                if script_path.endswith('.py'):
                    cmd = ["python", script_path]
                elif script_path.endswith('.sh'):
                    cmd = ["bash", script_path]
                elif script_path.endswith('.js'):
                    cmd = ["node", script_path]
                else:
                    # Default/Fallback
                    cmd = [script_path]

                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()

                if process.returncode != 0:
                    error_log = stderr.decode().strip() or stdout.decode().strip() or "Unknown Error"
                    raise Exception(f"Script failed with code {process.returncode}:\n{error_log}")

                print(f"[AutomationEngine] Script Success: {stdout.decode()[:100]}...")
                success = True

            # Update Task State (Success)
            updates = {
                "last_run": time.time(),
                "status": "active" # Ensure it stays active if it was previously failed?
            }
            # Calculate next run? (Optional, good for UI)
            # For interval, next_run = now + interval
            trigger = task.get('trigger', {}).get('value', {})
            if task.get('trigger', {}).get('type') == 'schedule':
                if trigger.get('mode') == 'interval':
                     interval = int(trigger.get('interval_minutes', 0)) * 60
                     updates["next_run"] = time.time() + interval
                # For daily, next_run is next occurrence of HH:MM (tomorrow or today)

            temp_manager.update_task(task['id'], updates)

        except Exception as e:
            print(f"[AutomationEngine] Execution Failed: {e}")

            # --- SELF HEALING LOGIC ---
            if act_type == 'run_script':
                print("[AutomationEngine] Attempting to generate fix...")
                fix_code = await self._generate_fix(act_value, str(e))

                if fix_code:
                    print("[AutomationEngine] Fix generated. Updating task state.")
                    updates = {
                        "status": "failed",
                        "healing": {
                            "script_path": act_value, # Save original path from action value
                            "error": str(e),
                            "fix_code": fix_code,
                            "timestamp": time.time()
                        }
                    }
                    temp_manager.update_task(task['id'], updates)

                    # Notify User
                    msg = f"Task '{task['title']}' failed. I have analyzed the error and generated a fix. Please review and apply it in the War Room."
                    if self.ada:
                         if self.ada.on_display_content:
                            self.ada.on_display_content({
                                "content_type": "notification",
                                "data": {"text": msg},
                                "duration": 15000
                            })
                         # Trigger voice
                         if self.ada.session:
                             asyncio.create_task(self.ada.session.send(input=f"System Notification: {msg}", end_of_turn=False))
                else:
                    print("[AutomationEngine] Could not generate fix.")
