import time
import json
import pytest
from backend.project_manager import ProjectManager

def test_jules_ui_state(temp_dir):
    pm = ProjectManager(temp_dir)
    # Use a persistent project, not 'temp' which is wiped on init
    pm.create_project("test_p")
    pm.switch_project("test_p")

    session_id = "test_session_1"

    # 1. Initial State
    state = pm.get_jules_session_state(session_id)
    assert state == {}

    # 2. Mark Seen
    pm.mark_jules_session_seen(session_id)
    state = pm.get_jules_session_state(session_id)
    assert "seen_at" in state
    first_seen = state["seen_at"]
    assert first_seen > 0

    # Verify persistence
    pm2 = ProjectManager(temp_dir) # reload
    # Must switch to the same project
    pm2.switch_project("test_p")

    state2 = pm2.get_jules_session_state(session_id)
    assert state2.get("seen_at") == first_seen

    # 3. Dismiss
    pm.dismiss_jules_session(session_id)
    state = pm.get_jules_session_state(session_id)
    assert state["dismissed"] is True

    # 4. Mark Seen again should not overwrite
    time.sleep(0.1)
    pm.mark_jules_session_seen(session_id)
    state = pm.get_jules_session_state(session_id)
    assert state["seen_at"] == first_seen
