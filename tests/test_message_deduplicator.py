import pytest
from backend.message_deduplicator import MessageDeduplicator

def test_check_and_add_basic():
    dedup = MessageDeduplicator()
    assert dedup.check_and_add("msg1") is True
    assert dedup.check_and_add("msg1") is False
    assert dedup.check_and_add("msg2") is True
    assert dedup.check_and_add("msg2") is False

def test_check_and_add_none():
    dedup = MessageDeduplicator()
    assert dedup.check_and_add(None) is True
    assert dedup.check_and_add(None) is False

def test_max_size_limit():
    max_size = 5
    dedup = MessageDeduplicator(max_size=max_size)

    # Fill it up
    for i in range(max_size):
        assert dedup.check_and_add(f"msg{i}") is True

    # Add one more, should evict msg0
    assert dedup.check_and_add("new_msg") is True

    # msg0 should now be True (new) again because it was evicted
    # Adding msg0 will evict the next oldest: msg1
    assert dedup.check_and_add("msg0") is True

    # msg1 should now be True (new) because it was evicted when msg0 was added
    assert dedup.check_and_add("msg1") is True

def test_unhashable_id():
    dedup = MessageDeduplicator()
    # This should not crash the application and should return True
    assert dedup.check_and_add({"key": "value"}) is True
