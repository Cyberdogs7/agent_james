import unittest
import os
import json
import tempfile
import shutil
from pathlib import Path
from backend.task_manager import TaskManager

class TestTaskManager(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()
        self.task_manager = TaskManager(self.test_dir)

    def tearDown(self):
        # Clean up
        shutil.rmtree(self.test_dir)

    def test_create_and_get_tasks(self):
        # Initial state should be empty
        self.assertEqual(len(self.task_manager.list_tasks()), 0)

        # Create a task
        # create_task(title, trigger_type, trigger_value, action_type, action_value)
        task = self.task_manager.create_task("Test Task", "manual", None, "jules_task", {"prompt": "foo"})

        # Verify task structure
        self.assertIsNotNone(task.get("id"))
        self.assertEqual(task["title"], "Test Task")
        self.assertEqual(task["trigger"]["type"], "manual")
        self.assertEqual(task["action"]["type"], "jules_task")
        self.assertEqual(task["action"]["value"]["prompt"], "foo")

        # Verify retrieval
        tasks = self.task_manager.list_tasks()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["id"], task["id"])

    def test_delete_task(self):
        # Create a task
        task = self.task_manager.create_task("To Delete")
        task_id = task["id"]

        # Verify it exists
        self.assertEqual(len(self.task_manager.list_tasks()), 1)

        # Delete it
        self.task_manager.delete_task(task_id)

        # Verify it's gone
        self.assertEqual(len(self.task_manager.list_tasks()), 0)

    def test_persistence(self):
        # Create a task
        self.task_manager.create_task("Persistent Task")

        # Create a new manager instance pointing to the same dir
        new_manager = TaskManager(self.test_dir)

        # Verify data persists
        self.assertEqual(len(new_manager.list_tasks()), 1)
        self.assertEqual(new_manager.list_tasks()[0]["title"], "Persistent Task")

if __name__ == '__main__':
    unittest.main()
