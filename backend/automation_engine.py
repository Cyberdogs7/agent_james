import asyncio
import time
import json
import traceback
from datetime import datetime, timedelta

try:
    from backend.github_client import GitHubClient
except ImportError:
    from github_client import GitHubClient

class AutomationEngine:
    def __init__(self, task_manager, project_manager, ada_instance=None):
        self.task_manager = task_manager
        self.project_manager = project_manager
        self.ada = ada_instance
        self.running = False
        self.stop_event = asyncio.Event()
        self.last_nag_times = {} # {id: timestamp}
        self._last_stalled_check = 0

        # Configuration
        self.STALL_THRESHOLD = 7200  # 2 hours
        self.NAG_COOLDOWN = 86400    # 24 hours
        self.CHECK_INTERVAL = 300    # 5 minutes

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

                            last_nag = self.last_nag_times.get(pr_url, 0)
                            if now - last_nag > self.NAG_COOLDOWN:
                                msg = f"Sir, the Pull Request '{title}' on {name} is waiting for review. Shall I merge it?"
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

        # Refresh tasks from current project
        current_path = self.project_manager.get_current_project_path()
        temp_manager = self.task_manager.__class__(current_path)
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
                        print(f"[AutomationEngine] Git Event matched task: {task['title']}")
                        # Inject event data into action context if needed?
                        # For now, just run it.
                        await self._execute_task(task, context=event_data)

    async def _execute_task(self, task, context=None):
        """Executes the action defined in the task."""
        action = task.get('action', {})
        act_type = action.get('type')
        act_value = action.get('value')

        success = False
        result_msg = ""

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
                    # Send via Voice (if appropriate?)
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

                    if context:
                        # Append context to prompt
                        prompt += f"\n\nContext:\n{json.dumps(context, indent=2)}"

                    # Use ada's handler
                    # This launches a background task
                    msg = await self.ada.handle_jules_request(prompt, source)
                    result_msg = msg
                    success = True

            elif act_type == 'run_script':
                print(f"[AutomationEngine] ACTION: Run Script (Simulated) - {act_value}")
                # Placeholder
                success = True

            # Update Task State
            updates = {
                "last_run": time.time()
            }
            # Calculate next run? (Optional, good for UI)
            # For interval, next_run = now + interval
            trigger = task.get('trigger', {}).get('value', {})
            if task.get('trigger', {}).get('type') == 'schedule':
                if trigger.get('mode') == 'interval':
                     interval = int(trigger.get('interval_minutes', 0)) * 60
                     updates["next_run"] = time.time() + interval
                # For daily, next_run is next occurrence of HH:MM (tomorrow or today)

            # Ensure we update the correct task manager
            current_path = self.project_manager.get_current_project_path()
            temp_manager = self.task_manager.__class__(current_path)
            temp_manager.update_task(task['id'], updates)

        except Exception as e:
            print(f"[AutomationEngine] Execution Failed: {e}")
            traceback.print_exc()
