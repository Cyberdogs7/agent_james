"""
Tests for AI Tool Definitions and Handlers.
"""
import pytest
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add backend to path
BACKEND_DIR = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))


class TestToolDefinitions:
    """Test tool definition schemas."""
    
    def test_generate_cad_tool_schema(self):
        """Test generate_cad tool has correct schema."""
        from cad_agent import generate_cad_tool
        
        assert generate_cad_tool['name'] == 'generate_cad'
        assert 'description' in generate_cad_tool
        assert 'parameters' in generate_cad_tool
        assert generate_cad_tool['parameters']['type'] == 'OBJECT'
        assert 'prompt' in generate_cad_tool['parameters']['properties']
        print(f"generate_cad tool: {generate_cad_tool['name']}")
    
    def test_run_web_agent_tool_schema(self):
        """Test run_web_agent tool has correct schema."""
        from web_agent import run_web_agent_tool
        
        assert run_web_agent_tool['name'] == 'run_web_agent'
        assert 'description' in run_web_agent_tool
        assert 'parameters' in run_web_agent_tool
        assert 'prompt' in run_web_agent_tool['parameters']['properties']
        print(f"run_web_agent tool: {run_web_agent_tool['name']}")
    
    def test_print_stl_tool_schema(self):
        """Test print_stl tool has correct schema."""
        from printer_agent import print_stl_tool
        
        assert print_stl_tool['name'] == 'print_stl'
        assert 'description' in print_stl_tool
        assert 'parameters' in print_stl_tool
        print(f"print_stl tool: {print_stl_tool['name']}")
    
    def test_discover_printers_tool_schema(self):
        """Test discover_printers tool has correct schema."""
        from printer_agent import discover_printers_tool
        
        assert discover_printers_tool['name'] == 'discover_printers'
        assert 'description' in discover_printers_tool
        print(f"discover_printers tool: {discover_printers_tool['name']}")
    
    def test_list_smart_devices_tool_schema(self):
        """Test list_smart_devices tool has correct schema."""
        from kasa_agent import list_smart_devices_tool
        
        assert list_smart_devices_tool['name'] == 'list_smart_devices'
        assert 'description' in list_smart_devices_tool
        print(f"list_smart_devices tool: {list_smart_devices_tool['name']}")
    
    def test_control_light_tool_schema(self):
        """Test control_light tool has correct schema."""
        from kasa_agent import control_light_tool
        
        assert control_light_tool['name'] == 'control_light'
        assert 'parameters' in control_light_tool
        props = control_light_tool['parameters']['properties']
        assert 'target' in props
        assert 'action' in props
        print(f"control_light tool: {control_light_tool['name']}")
    
    def test_list_projects_tool_schema(self):
        """Test list_projects tool has correct schema."""
        from project_manager import list_projects_tool
        
        assert list_projects_tool['name'] == 'list_projects'
        print(f"list_projects tool: {list_projects_tool['name']}")
    
    def test_iterate_cad_tool_schema(self):
        """Test iterate_cad tool has correct schema."""
        from cad_agent import iterate_cad_tool
        
        assert iterate_cad_tool['name'] == 'iterate_cad'
        print(f"iterate_cad tool: {iterate_cad_tool['name']}")

    def test_run_jules_agent_tool_schema(self):
        """Test run_jules_agent tool has correct schema."""
        from tools import run_jules_agent_tool

        assert run_jules_agent_tool['name'] == 'run_jules_agent'
        assert 'description' in run_jules_agent_tool
        assert 'parameters' in run_jules_agent_tool
        assert 'prompt' in run_jules_agent_tool['parameters']['properties']
        assert 'source' in run_jules_agent_tool['parameters']['properties']
        assert "source" not in run_jules_agent_tool['parameters']['required']
        print(f"run_jules_agent tool: {run_jules_agent_tool['name']}")


    def test_list_jules_sources_tool_schema(self):
        """Test list_jules_sources tool has correct schema."""
        from tools import list_jules_sources_tool

        assert list_jules_sources_tool['name'] == 'list_jules_sources'
        assert 'description' in list_jules_sources_tool
        print(f"list_jules_sources tool: {list_jules_sources_tool['name']}")

    def test_list_jules_activities_tool_schema(self):
        """Test list_jules_activities tool has correct schema."""
        from tools import list_jules_activities_tool

        assert list_jules_activities_tool['name'] == 'list_jules_activities'
        assert 'description' in list_jules_activities_tool
        assert 'parameters' in list_jules_activities_tool
        assert 'session_id' in list_jules_activities_tool['parameters']['properties']
        print(f"list_jules_activities tool: {list_jules_activities_tool['name']}")


class TestJulesToolHandlers:
    """Test Jules tool handlers."""


    def test_handle_list_jules_sources_method_exists(self):
        """Test handle_list_jules_sources exists."""
        from ada import AudioLoop
        assert hasattr(AudioLoop, 'handle_list_jules_sources')

    def test_handle_list_jules_activities_method_exists(self):
        """Test handle_list_jules_activities exists."""
        from ada import AudioLoop
        assert hasattr(AudioLoop, 'handle_list_jules_activities')


class TestAudioLoopClass:
    """Test AudioLoop class structure."""
    
    def test_audioloop_class_exists(self):
        """Test AudioLoop class can be imported."""
        from ada import AudioLoop
        assert AudioLoop is not None
        print("AudioLoop class imported successfully")
    
    def test_audioloop_methods(self):
        """Test AudioLoop has required methods."""
        from ada import AudioLoop
        
        required_methods = [
            'run',
            'stop',
            'send_frame',
            'listen_audio',
            'receive_audio',
            'play_audio',
            'handle_cad_request',
            'handle_web_agent_request',
            'resolve_tool_confirmation',
            'update_permissions',
            'set_paused',
            'clear_audio_queue',
        ]
        
        for method in required_methods:
            assert hasattr(AudioLoop, method), f"Missing method: {method}"
            print(f"  ✓ {method}")


class TestFileOperations:
    """Test file operation handlers."""
    
    def test_read_directory_method_exists(self):
        """Test read_directory exists."""
        from filesystem_agent import FileSystemAgent
        assert hasattr(FileSystemAgent, 'read_directory')
    
    def test_read_file_method_exists(self):
        """Test read_file exists."""
        from filesystem_agent import FileSystemAgent
        assert hasattr(FileSystemAgent, 'read_file')
    
    def test_write_file_method_exists(self):
        """Test write_file exists."""
        from filesystem_agent import FileSystemAgent
        assert hasattr(FileSystemAgent, 'write_file')


class TestLiveConnectConfig:
    """Test Gemini Live Connect configuration."""

    def test_config_generation(self):
        """Test that the LiveConnectConfig is generated correctly."""
        from ada import AudioLoop
        from google.genai import types

        # Mock the agent classes
        mock_project_manager = MagicMock()
        mock_project_manager.get_project_config.return_value = {}
        mock_project_manager.tools = []

        mock_kasa_agent = MagicMock()
        mock_kasa_agent.tools = []

        # Instantiate AudioLoop with mocked agents
        audio_loop = AudioLoop(
            project_manager=mock_project_manager,
            kasa_agent=mock_kasa_agent
        )
        config = audio_loop._get_live_connect_config()

        assert config is not None, "Config object should not be None"
        assert isinstance(config, types.LiveConnectConfig), "Config should be a LiveConnectConfig instance"
        assert 'AUDIO' in config.response_modalities, "Response modalities should include AUDIO"
        print("LiveConnectConfig generated successfully with correct modality")


class TestToolPermissions:
    """Test tool permission handling."""
    
    def test_update_permissions_method(self):
        """Test update_permissions method exists."""
        from ada import AudioLoop
        assert hasattr(AudioLoop, 'update_permissions')
        print("update_permissions method exists")


class TestAgentImports:
    """Test agent module imports in ada.py."""
    
    def test_cad_agent_import(self):
        """Test CadAgent is imported."""
        from ada import CadAgent
        assert CadAgent is not None
        print("CadAgent imported")
    
    def test_web_agent_import(self):
        """Test WebAgent is imported."""
        from ada import WebAgent
        assert WebAgent is not None
        print("WebAgent imported")
    
    def test_kasa_agent_import(self):
        """Test KasaAgent is imported."""
        from ada import KasaAgent
        assert KasaAgent is not None
        print("KasaAgent imported")
    
    def test_printer_agent_import(self):
        """Test PrinterAgent is imported."""
        from ada import PrinterAgent
        assert PrinterAgent is not None
        print("PrinterAgent imported")

    def test_jules_agent_import(self):
        """Test JulesAgent is imported."""
        from ada import JulesAgent
        assert JulesAgent is not None
        print("JulesAgent imported")


class TestToolConfirmation:
    """Test tool confirmation handling."""
    
    def test_resolve_tool_confirmation_method(self):
        """Test resolve_tool_confirmation exists."""
        from ada import AudioLoop
        assert hasattr(AudioLoop, 'resolve_tool_confirmation')
        print("resolve_tool_confirmation method exists")
