import os
import json
import pytest
from backend.project_manager import ProjectManager, VALID_VOICES, DEFAULT_SYSTEM_PROMPT

def test_project_manager_initialization(temp_dir):
    pm = ProjectManager(temp_dir)
    assert pm.current_project == "temp"
    assert (pm.projects_dir / "temp").exists()

def test_set_voice(temp_dir):
    pm = ProjectManager(temp_dir)

    # Test valid voice
    voice = VALID_VOICES[0]
    success, msg = pm.set_voice(voice)
    assert success

    config = pm.get_project_config()
    assert config["voice_name"] == voice

    # Test invalid voice
    success, msg = pm.set_voice("InvalidVoice")
    assert not success
    assert "Invalid voice name" in msg

    config = pm.get_project_config()
    assert config["voice_name"] == voice # Should remain unchanged

def test_update_persona(temp_dir):
    pm = ProjectManager(temp_dir)

    new_persona = "You are a pirate."
    success, msg = pm.update_persona(new_persona)
    assert success

    config = pm.get_project_config()
    assert config["system_prompt"] == new_persona

def test_get_project_path(temp_dir):
    pm = ProjectManager(temp_dir)
    path = pm.get_project_path("My Project")
    assert path.name == "My Project"
    assert path.parent == pm.projects_dir

def test_list_git_projects(temp_dir):
    pm = ProjectManager(temp_dir)

    # Create a git project
    pm.create_project("git_project")
    git_proj_path = pm.get_project_path("git_project")
    (git_proj_path / ".git").mkdir()

    # Create a non-git project
    pm.create_project("non_git_project")

    git_projects = pm.list_git_projects()
    assert "git_project" in git_projects
    assert "non_git_project" not in git_projects
