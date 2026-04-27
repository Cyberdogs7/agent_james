import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
from unittest.mock import patch
from backend import db

@pytest.fixture
def test_db():
    fd, temp_path = tempfile.mkstemp()
    os.close(fd)

    with patch('backend.db.DB_PATH', Path(temp_path)):
        db.init_db()
        yield temp_path

    os.remove(temp_path)

def test_add_get_update_delete(test_db):
    # Add
    acc_id = db.add_account("key1", "name1", 5, 10)
    assert acc_id is not None

    # Get
    accs = db.get_all_accounts()
    assert len(accs) == 1
    assert accs[0]['api_key'] == "key1"

    # Update
    db.update_account(acc_id, "key1_new", "name1_new", 10, 20)
    accs = db.get_all_accounts()
    assert accs[0]['api_key'] == "key1_new"

    # Delete
    db.delete_account(acc_id)
    accs = db.get_all_accounts()
    assert len(accs) == 0

def test_add_account_duplicate_api_key(test_db):
    db.add_account("duplicate_key", "name1")
    result = db.add_account("duplicate_key", "name2")
    assert result is None

def test_add_account_minimal_fields(test_db):
    acc_id = db.add_account("minimal_key")
    assert acc_id is not None
    accs = db.get_all_accounts()
    assert len(accs) == 1
    assert accs[0]['api_key'] == "minimal_key"
    assert accs[0]['name'] is None
    assert accs[0]['concurrent_sessions_limit'] is None
    assert accs[0]['total_sessions_limit'] is None

def test_add_account_all_fields(test_db):
    acc_id = db.add_account("full_key", "Full Name", 10, 100)
    assert acc_id is not None
    accs = db.get_all_accounts()
    assert len(accs) == 1
    acc = accs[0]
    assert acc['api_key'] == "full_key"
    assert acc['name'] == "Full Name"
    assert acc['concurrent_sessions_limit'] == 10
    assert acc['total_sessions_limit'] == 100
