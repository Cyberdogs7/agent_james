import asyncio
import time
import json
import logging
from datetime import datetime

class AutomationEngine:
    def __init__(self, project_manager, task_manager, jules_agent=None, trello_agent=None):
        self.project_manager = project_manager
        # task_manager argument is expected to be an instance, but we will use its class
        # to re-instantiate it for the current project context.
        self.task_manager_cls = task_manager.__class__
        self.jules_agent_cls = jules_agent.__class__ if jules_agent else None
        self.trello_agent = trello_agent

        self.running = False
        self.notification_queue = asyncio.Queue()
        self.min_interval = 30
        self.max_interval = 120
        self.current_interval = self.min_interval

        # State for detecting changes
        self._trello_card_lists = {} # card_id -> list_id

        # Callback for when a notification is queued (to wake up server)
        self.on_notification = None

    def set_notification_callback(self, callback):
        self.on_notification = callback

    async def start(self):
        self.running = True
        print("[AutomationEngine] Service Started.")
        while self.running:
            try:
                changes_found = await self.check_triggers()

                # Backoff logic
                if changes_found:
                    self.current_interval = self.min_interval
                else:
                    self.current_interval = min(self.current_interval * 1.5, self.max_interval)

                # Sleep in chunks to allow faster shutdown
                for _ in range(int(self.current_interval)):
                    if not self.running: break
                    await asyncio.sleep(1)

            except Exception as e:
                print(f"[AutomationEngine] Error in loop: {e}")
                await asyncio.sleep(self.min_interval)

    def stop(self):
        print("[AutomationEngine] Stopping service...")
        self.running = False

    async def check_triggers(self):
        # Re-instantiate TaskManager for current project
        current_project_path = self.project_manager.get_current_project_path()
        task_manager = self.task_manager_cls(current_project_path)

        tasks = task_manager.list_tasks()
        if not tasks:
            return False

        changes_detected = False

        # 1. Fetch Global Events (Git, Trello) once per tick to avoid repeated API calls

        # --- Git Monitoring ---
        git_events = []
        try:
            # monitors all repos in fleet
            git_events = await self.project_manager.monitor_git_repos()
        except Exception as e:
            print(f"[AutomationEngine] Git monitor failed: {e}")

        # --- Trello Monitoring ---
        trello_events = []
        has_trello_task = any(t['trigger']['type'] == 'trello' for t in tasks)
        if has_trello_task and self.trello_agent:
            try:
                trello_events = await self._poll_trello_changes()
            except Exception as e:
                print(f"[AutomationEngine] Trello monitor failed: {e}")

        # 2. Evaluate Tasks
        for task in tasks:
            if task.get('status') != 'active':
                continue

            triggered = False
            context = {}

            trigger = task.get('trigger', {})
            trigger_type = trigger.get('type')
            trigger_val = trigger.get('value')

            if trigger_type == 'git':
                # Check if any git event matches this task's repo
                # value can be "owner/repo" or "*"
                for event in git_events:
                    if trigger_val == '*' or event['repo'] == trigger_val:
                        triggered = True
                        context = event
                        break # Trigger once per tick per task

            elif trigger_type == 'trello':
                # Check trello events
                for event in trello_events:
                     triggered = True
                     context = event
                     break

            elif trigger_type == 'schedule':
                triggered = self._check_schedule(task)
                if triggered:
                    context = {"time": datetime.now().isoformat()}

            if triggered:
                changes_detected = True
                print(f"[AutomationEngine] Task '{task['title']}' triggered!")

                # Execute Action
                await self.execute_action(task, context)

                # Update last run timestamp in task
                task['last_run'] = time.time()
                # Use private method or raw list update to save back
                self._update_task_last_run(task_manager, task)

        if git_events or trello_events:
            changes_detected = True

        return changes_detected

    def _update_task_last_run(self, task_manager, updated_task):
        # Helper to save the updated task timestamp back to disk
        all_tasks = task_manager.list_tasks()
        for i, t in enumerate(all_tasks):
            if t['id'] == updated_task['id']:
                all_tasks[i] = updated_task
                break
        task_manager.save_tasks(all_tasks)

    def _check_schedule(self, task):
        # interval: "10m", "1h"
        # daily: "09:00"
        val = task['trigger']['value']
        last_run = task.get('last_run')
        now = time.time()

        # If never run, run immediately? Or treat created_at as start?
        # Let's treat created_at as start to avoid instant trigger loop if interval is small
        if not last_run:
            last_run = task.get('created_at', now)

        if not val:
            return False

        if 'm' in val or 'h' in val:
            # Interval
            try:
                unit = val[-1]
                amount = int(val[:-1])
                seconds = amount * 60 if unit == 'm' else amount * 3600

                if now - last_run >= seconds:
                    return True
            except:
                pass

        elif ':' in val:
            # Daily HH:MM
            try:
                target_hour, target_min = map(int, val.split(':'))
                dt_now = datetime.now()
                target_dt = dt_now.replace(hour=target_hour, minute=target_min, second=0, microsecond=0)

                # If target time has passed today
                if dt_now > target_dt:
                    start_of_day = dt_now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()

                    # Run if:
                    # 1. We haven't run today (last_run < start_of_day)
                    # 2. OR this is the first run (last_run == created_at) AND created_at was BEFORE target

                    created_at = task.get('created_at', 0)
                    is_first_run_cycle = (last_run == created_at)
                    created_before_target = (created_at < target_dt.timestamp())

                    if last_run < start_of_day:
                        return True
                    elif is_first_run_cycle and created_before_target:
                        return True
            except:
                pass

        return False

    async def _poll_trello_changes(self):
        """Detects if cards have moved lists on the primary board."""
        events = []
        if not self.trello_agent:
            return events

        # 1. Get first board
        boards = await self.trello_agent.list_boards()
        if not boards:
            return events

        board_id = boards[0]['id']

        # 2. Get all cards
        # We need a flat list of cards with their list_id
        # list_cards returns cards for a specific list.
        # So we need lists first.
        lists = await self.trello_agent.list_lists(board_id)
        if not lists:
            return events

        list_map = {l['id']: l['name'] for l in lists}

        current_state = {}

        # Fetch cards for all lists (parallelize)
        tasks = [self.trello_agent.list_cards(l['id']) for l in lists]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, res in enumerate(results):
            if isinstance(res, list):
                list_id = lists[i]['id']
                for card in res:
                    card_id = card['id']
                    current_state[card_id] = list_id

                    # Check for change
                    prev_list_id = self._trello_card_lists.get(card_id)
                    if prev_list_id and prev_list_id != list_id:
                        # MOVED!
                        prev_list_name = list_map.get(prev_list_id, "Unknown")
                        new_list_name = list_map.get(list_id, "Unknown")
                        events.append({
                            "type": "trello_move",
                            "card": card['name'],
                            "from": prev_list_name,
                            "to": new_list_name,
                            "message": f"Trello card '{card['name']}' moved from {prev_list_name} to {new_list_name}"
                        })

        self._trello_card_lists = current_state
        return events

    async def execute_action(self, task, context):
        action = task['action']
        act_type = action.get('type')
        act_val = action.get('value')

        if act_type == 'notify':
            # Construct message
            base_msg = act_val if isinstance(act_val, str) else f"Automation '{task['title']}' triggered."
            if context.get('message'):
                base_msg += f" Details: {context['message']}"

            await self.queue_notification(base_msg)

        elif act_type == 'spawn_agent':
            prompt = ""
            source = None
            if isinstance(act_val, dict):
                prompt = act_val.get('prompt', '')
                source = act_val.get('source')
            else:
                prompt = str(act_val)

            # Inject context
            full_prompt = f"{prompt}\n\n[System Context - Trigger Event]:\n{json.dumps(context, indent=2)}"

            # Instantiate JulesAgent with current project config
            config = self.project_manager.get_project_config()
            api_key = config.get("jules_api_key")

            if self.jules_agent_cls:
                agent = self.jules_agent_cls(api_key=api_key)

                print(f"[AutomationEngine] Spawning agent for task: {task['title']}")
                # Fire and forget
                asyncio.create_task(agent.spawn_agent(full_prompt, source))
                # Also notify that we spawned it
                await self.queue_notification(f"I've automatically spawned a Jules Agent for: {task['title']}")

        elif act_type == 'run_script':
            # Placeholder
            print(f"[AutomationEngine] Script execution triggered: {act_val}")

    async def queue_notification(self, message):
        print(f"[AutomationEngine] Queuing notification: {message}")
        handled = False
        # Invoke callback if set (to push immediately if session active)
        if self.on_notification:
            handled = await self.on_notification(message)

        # Only queue if not handled immediately
        if not handled:
            await self.notification_queue.put(message)

    def get_pending_notifications(self):
        msgs = []
        while not self.notification_queue.empty():
            msgs.append(self.notification_queue.get_nowait())
        return msgs
