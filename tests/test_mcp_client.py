import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from mcp_client import MCPClientManager
from tool_registry import ToolRegistry

class MockMCPTool:
    def __init__(self, name, description, inputSchema):
        self.name = name
        self.description = description
        self.inputSchema = inputSchema

class MockMCPToolsResponse:
    def __init__(self, tools):
        self.tools = tools

class TestMCPClientManager:
    def test_init_and_config_loading_defaults(self):
        """Test that MCPClientManager loads default config when mcp_servers.json is absent."""
        registry = ToolRegistry()
        manager = MCPClientManager(registry)
        config = manager.load_config()
        assert "higgsfield" in config
        assert config["higgsfield"]["type"] == "sse"
        assert config["higgsfield"]["url"] == "https://mcp.higgsfield.ai/mcp"

    def test_schema_conversion_basic(self):
        """Test converting an MCP tool schema into Gemini tool schema format."""
        registry = ToolRegistry()
        manager = MCPClientManager(registry)

        mcp_tool = MockMCPTool(
            name="generate-video",
            description="Generates a cinematic video.",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Visual details for the generation."
                    },
                    "duration": {
                        "type": "integer",
                        "description": "Length of video in seconds."
                    }
                },
                "required": ["prompt"]
            }
        )

        gemini_schema = manager.convert_to_gemini_schema("higgsfield_generate_video", mcp_tool)
        assert gemini_schema["name"] == "higgsfield_generate_video"
        assert gemini_schema["description"] == "Generates a cinematic video."
        assert gemini_schema["parameters"]["type"] == "OBJECT"
        assert "prompt" in gemini_schema["parameters"]["properties"]
        assert gemini_schema["parameters"]["properties"]["prompt"]["type"] == "STRING"
        assert gemini_schema["parameters"]["properties"]["prompt"]["description"] == "Visual details for the generation."
        assert gemini_schema["parameters"]["properties"]["duration"]["type"] == "INTEGER"
        assert gemini_schema["parameters"]["required"] == ["prompt"]

    @pytest.mark.asyncio
    @patch("mcp_client.sse_client")
    async def test_connect_sse_and_register(self, mock_sse_client):
        """Test connecting via SSE, fetching tools, and registering them in ToolRegistry."""
        registry = ToolRegistry()
        reconnect_called = False

        def on_reconnect():
            nonlocal reconnect_called
            reconnect_called = True

        manager = MCPClientManager(registry, reconnect_callback=on_reconnect)

        # Mock sse_client context manager yielding (read, write)
        mock_read = MagicMock()
        mock_write = MagicMock()
        
        # Async context manager mock
        async_cm = AsyncMock()
        async_cm.__aenter__.return_value = (mock_read, mock_write)
        mock_sse_client.return_value = async_cm

        # Mock ClientSession
        mock_tool = MockMCPTool(
            name="generate-video",
            description="Cinematic generation.",
            inputSchema={"type": "object", "properties": {"prompt": {"type": "string"}}}
        )
        mock_tools_resp = MockMCPToolsResponse([mock_tool])

        mock_session = AsyncMock()
        mock_session.list_tools.return_value = mock_tools_resp

        mock_session_ctx = MagicMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock()

        # Patch ClientSession in mcp_client
        with patch("mcp_client.ClientSession", return_value=mock_session_ctx):
            # We run connect_sse but since it loops forever, we wrap it in wait_for or cancel it
            task = asyncio.create_task(manager.connect_sse("higgsfield", "https://mcp.higgsfield.ai/mcp"))
            
            # Let it run for a brief moment to initialize and fetch tools
            await asyncio.sleep(0.1)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Verify tool registration in ToolRegistry
        assert "higgsfield_generate_video" in registry._handlers
        assert len(registry._dynamic_declarations) == 1
        assert registry._dynamic_declarations[0]["name"] == "higgsfield_generate_video"
        assert reconnect_called is True
