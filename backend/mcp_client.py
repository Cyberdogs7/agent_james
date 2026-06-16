import asyncio
import logging
import webbrowser
import re
from websockets.exceptions import ConnectionClosedError
from mcp import ClientSession
from mcp.client.sse import sse_client

logger = logging.getLogger("ada.mcp_client")

class MCPClientManager:
    def __init__(self, tool_registry, reconnect_callback=None):
        self.tool_registry = tool_registry
        self.reconnect_callback = reconnect_callback
        self.sessions = {}
        self.active_tasks = []

    async def start(self):
        """Loads configuration and starts MCP sessions."""
        config = self.load_config()
        for server_name, server_config in config.items():
            task = asyncio.create_task(self.run_server_session(server_name, server_config))
            self.active_tasks.append(task)

    def load_config(self):
        """Loads server definitions from mcp_servers.json or returns default."""
        default_config = {
            "higgsfield": {
                "type": "sse",
                "url": "https://mcp.higgsfield.ai/mcp"
            }
        }
        import os
        import json
        config_path = "mcp_servers.json"
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    user_config = json.load(f)
                    if "mcpServers" in user_config:
                        return user_config["mcpServers"]
                    return user_config
            except Exception as e:
                logger.error(f"Failed to load mcp_servers.json: {e}")
        return default_config

    async def run_server_session(self, name, config):
        """Manages lifecycle of a single server connection."""
        transport_type = config.get("type", "sse")
        if transport_type == "sse":
            url = config.get("url")
            if not url:
                logger.error(f"No URL specified for SSE server {name}")
                return
            
            backoff = 1
            while True:
                try:
                    await self.connect_sse(name, url)
                except (ConnectionClosedError, asyncio.TimeoutError, Exception) as e:
                    if isinstance(e, asyncio.CancelledError):
                        break
                    logger.warning(f"Connection to '{name}' failed: {e}. Retrying in {backoff}s...")
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 60)
        else:
            logger.warning(f"Unsupported transport type {transport_type} for {name}")

    async def connect_sse(self, name, url):
        """Establishes an SSE connection, retrieves tools, and maps them to the registry."""
        print(f"[MCP] Connecting to SSE server '{name}' at {url}...", flush=True)
        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                self.sessions[name] = session
                print(f"[MCP] Initialized session with '{name}'.", flush=True)
                
                # Fetch tools from the server
                tools = await session.list_tools()
                print(f"[MCP] Discovered {len(tools.tools)} tools from '{name}'.", flush=True)
                
                has_new_tool = False
                for tool in tools.tools:
                    # Normalize tool names to fit Gemini's requirements
                    tool_name = f"{name}_{tool.name.replace('-', '_').replace(':', '_')}"
                    gemini_schema = self.convert_to_gemini_schema(tool_name, tool)
                    
                    # Closure to bind tool execution parameters
                    async def make_handler(t_name, orig_name, sess):
                        async def handler(**kwargs):
                            print(f"[MCP] Calling tool '{orig_name}' on '{name}' with args: {kwargs}", flush=True)
                            try:
                                res = await sess.call_tool(orig_name, arguments=kwargs)
                                text_content = []
                                for content in res.content:
                                    if hasattr(content, "text"):
                                        text_content.append(content.text)
                                    elif isinstance(content, dict) and "text" in content:
                                        text_content.append(content["text"])
                                return "\n".join(text_content) if text_content else str(res)
                            except Exception as err:
                                err_str = str(err)
                                # Match OAuth login links in error messages (like those from hosted Higgsfield SSE)
                                login_url_match = re.search(
                                    r'(https?://[^\s]+(?:login|oauth|authorize|authenticate)[^\s]*)', 
                                    err_str, 
                                    re.IGNORECASE
                                )
                                if login_url_match:
                                    login_url = login_url_match.group(0)
                                    print(f"\n[MCP AUTH] Connection requires authentication. Opening browser to:\n{login_url}\n", flush=True)
                                    webbrowser.open(login_url)
                                    return f"Authentication required. I have opened the login page in your browser. Please log in to your Higgsfield account and try the request again."
                                raise err
                        return handler

                    handler_fn = await make_handler(tool_name, tool.name, session)
                    self.tool_registry.register(tool_name, handler_fn)
                    
                    # Add to dynamic declarations so it gets registered in Gemini's LiveConnectConfig
                    self.tool_registry._dynamic_declarations.append(gemini_schema)
                    has_new_tool = True
                    print(f"[MCP] Registered tool '{tool_name}'", flush=True)
                    
                if has_new_tool and self.reconnect_callback:
                    print(f"[MCP] New tools registered. Reconnecting voice session to sync...", flush=True)
                    self.reconnect_callback()
                    
                # Keep the session running
                while True:
                    await asyncio.sleep(3600)

    def convert_to_gemini_schema(self, name, tool):
        """Converts inputSchema into GenAI JSON schema structure."""
        params = {
            "type": "OBJECT",
            "properties": {},
            "required": []
        }
        
        schema = getattr(tool, "inputSchema", {}) or {}
        if isinstance(schema, dict):
            properties = schema.get("properties", {})
            required = schema.get("required", [])
            
            for prop_name, prop_val in properties.items():
                p_type = prop_val.get("type", "string").upper()
                p_desc = prop_val.get("description", "")
                params["properties"][prop_name] = {
                    "type": p_type,
                    "description": p_desc
                }
            params["required"] = required
            
        return {
            "name": name,
            "description": tool.description,
            "parameters": params
        }

    async def stop(self):
        """Stops all active MCP client tasks."""
        for task in self.active_tasks:
            task.cancel()
        if self.active_tasks:
            await asyncio.gather(*self.active_tasks, return_exceptions=True)
            self.active_tasks = []
