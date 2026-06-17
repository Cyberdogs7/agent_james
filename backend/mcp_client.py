import asyncio
import logging
import webbrowser
import re
import subprocess
import shutil
from websockets.exceptions import ConnectionClosedError

# Custom exception to signal that authentication via browser is required
class AuthRequiredError(Exception):
    """Raised when the MCP server indicates authentication is needed (e.g., 401)."""
    pass
from mcp import ClientSession
from mcp.client.sse import sse_client

logger = logging.getLogger("ada.mcp_client")

# ---------------------------------------------------------------------------
# Higgsfield CLI helpers
# ---------------------------------------------------------------------------

def _higgsfield_cli_path():
    """Locate the higgsfield CLI executable."""
    return shutil.which("higgsfield")


async def _run_higgsfield_cli(*args, timeout=300):
    """
    Run a higgsfield CLI command and return (stdout, stderr, returncode).
    Uses asyncio subprocess so it doesn't block the event loop.
    """
    cli = _higgsfield_cli_path()
    if not cli:
        raise FileNotFoundError(
            "Higgsfield CLI not found. Install it with: npm install -g @higgsfield/cli"
        )
    cmd = [cli] + list(args)
    print(f"[Higgsfield CLI] Running: {' '.join(cmd)}", flush=True)
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        raise TimeoutError(f"Higgsfield CLI timed out after {timeout}s")
    return stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace"), proc.returncode


def _check_cli_auth_error(stdout: str, stderr: str) -> bool:
    """Return True if the CLI output indicates an authentication failure."""
    combined = (stdout + stderr).lower()
    return any(k in combined for k in ("not authenticated", "unauthorized", "please login", "auth login", "401"))


async def higgsfield_generate_image_cli(prompt: str, model: str = "nano_banana_2",
                                         aspect_ratio: str = "1:1", resolution: str = "1k",
                                         **kwargs) -> str:
    """
    Generate an image via the local Higgsfield CLI.
    Falls back to opening the auth browser if the CLI reports an auth error.
    """
    args = [
        "generate", "create", model,
        "--prompt", prompt,
        "--aspect_ratio", aspect_ratio,
        "--resolution", resolution,
        "--wait",
    ]
    # Forward any extra kwargs as --key value pairs
    for k, v in kwargs.items():
        args += [f"--{k.replace('_', '-')}", str(v)]

    stdout, stderr, rc = await _run_higgsfield_cli(*args)
    combined = stdout + stderr

    if _check_cli_auth_error(stdout, stderr):
        print(
            "\n[Higgsfield CLI] Authentication required. Opening browser for login...\n"
            "After logging in, please retry the image generation request.",
            flush=True,
        )
        # Try to open the login page
        await _run_higgsfield_cli("auth", "login")
        return (
            "Authentication required. I've opened the browser so you can log into "
            "Higgsfield. Once you've completed the login, please ask me again to "
            "generate the image."
        )

    if rc != 0:
        logger.error(f"[Higgsfield CLI] Image generation failed (rc={rc}):\n{combined}")
        return f"Image generation failed. CLI output:\n{combined.strip()}"

    print(f"[Higgsfield CLI] Image generation output:\n{stdout.strip()}", flush=True)
    return stdout.strip() or "Image generation complete."


async def higgsfield_generate_video_cli(prompt: str, model: str = "kling3_0",
                                         duration: int = 5,
                                         aspect_ratio: str = "16:9",
                                         start_image: str = None,
                                         **kwargs) -> str:
    """
    Generate a video via the local Higgsfield CLI.
    Falls back to opening the auth browser if the CLI reports an auth error.
    """
    args = [
        "generate", "create", model,
        "--prompt", prompt,
        "--duration", str(duration),
        "--aspect_ratio", aspect_ratio,
        "--wait",
    ]
    if start_image:
        args += ["--start-image", start_image]
    for k, v in kwargs.items():
        args += [f"--{k.replace('_', '-')}", str(v)]

    stdout, stderr, rc = await _run_higgsfield_cli(*args)
    combined = stdout + stderr

    if _check_cli_auth_error(stdout, stderr):
        print(
            "\n[Higgsfield CLI] Authentication required. Opening browser for login...\n"
            "After logging in, please retry the video generation request.",
            flush=True,
        )
        await _run_higgsfield_cli("auth", "login")
        return (
            "Authentication required. I've opened the browser so you can log into "
            "Higgsfield. Once you've completed the login, please ask me again to "
            "generate the video."
        )

    if rc != 0:
        logger.error(f"[Higgsfield CLI] Video generation failed (rc={rc}):\n{combined}")
        return f"Video generation failed. CLI output:\n{combined.strip()}"

    print(f"[Higgsfield CLI] Video generation output:\n{stdout.strip()}", flush=True)
    return stdout.strip() or "Video generation complete."


# Gemini tool schema declarations for the CLI tools (static fallback)
_HIGGSFIELD_CLI_DECLARATIONS = [
    {
        "name": "higgsfield_generate_image",
        "description": (
            "Generate an image using Higgsfield AI. Uses the local Higgsfield CLI "
            "as a reliable fallback when the MCP server is unavailable."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "prompt": {
                    "type": "STRING",
                    "description": "Detailed visual description of the image to generate.",
                },
                "model": {
                    "type": "STRING",
                    "description": (
                        "Image model name (default: nano_banana_2). "
                        "Run `higgsfield model list` for available models."
                    ),
                },
                "aspect_ratio": {
                    "type": "STRING",
                    "description": "Aspect ratio, e.g. '1:1', '16:9', '4:3' (default: '1:1').",
                },
                "resolution": {
                    "type": "STRING",
                    "description": "Output resolution, e.g. '1k', '2k', '4k' (default: '1k').",
                },
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "higgsfield_generate_video",
        "description": (
            "Generate a cinematic video using Higgsfield AI. Uses the local Higgsfield CLI "
            "as a reliable fallback when the MCP server is unavailable."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "prompt": {
                    "type": "STRING",
                    "description": "Detailed visual description of the video to generate.",
                },
                "model": {
                    "type": "STRING",
                    "description": (
                        "Video model name (default: kling3_0). "
                        "Run `higgsfield model list` for available models."
                    ),
                },
                "duration": {
                    "type": "INTEGER",
                    "description": "Video length in seconds (default: 5).",
                },
                "aspect_ratio": {
                    "type": "STRING",
                    "description": "Aspect ratio, e.g. '16:9', '9:16', '1:1' (default: '16:9').",
                },
                "start_image": {
                    "type": "STRING",
                    "description": "Optional path or URL to an image to use as the first frame.",
                },
            },
            "required": ["prompt"],
        },
    },
]


class MCPClientManager:
    def __init__(self, tool_registry, reconnect_callback=None):
        self.tool_registry = tool_registry
        self.reconnect_callback = reconnect_callback
        self.sessions = {}
        # Tracks whether we have already opened the auth browser for this session
        self.auth_pending = False
        self.active_tasks = []

    async def start(self):
        """Loads configuration, registers CLI fallback tools, and starts MCP sessions."""
        # Register CLI-based fallback tools immediately so generation is always
        # available even when the MCP SSE server is unreachable or returns 401.
        self._register_cli_fallbacks()

        config = self.load_config()
        for server_name, server_config in config.items():
            task = asyncio.create_task(self.run_server_session(server_name, server_config))
            self.active_tasks.append(task)

    def _register_cli_fallbacks(self):
        """
        Registers higgsfield_generate_image and higgsfield_generate_video as static
        CLI-backed tools. If the MCP SSE connection later succeeds, the same tool names
        will be overwritten with the live session handlers.
        """
        cli_available = bool(_higgsfield_cli_path())
        if not cli_available:
            logger.warning(
                "[MCP] Higgsfield CLI not found on PATH. "
                "Install via: npm install -g @higgsfield/cli  "
                "CLI fallback tools will be registered but will report an error on use."
            )

        self.tool_registry.register("higgsfield_generate_image", higgsfield_generate_image_cli)
        self.tool_registry.register("higgsfield_generate_video", higgsfield_generate_video_cli)

        # Only add declarations if they haven't been added yet (avoid duplicates on reconnect)
        existing_names = {d.get("name") for d in self.tool_registry._dynamic_declarations}
        for decl in _HIGGSFIELD_CLI_DECLARATIONS:
            if decl["name"] not in existing_names:
                self.tool_registry._dynamic_declarations.append(decl)

        status = "available" if cli_available else "NOT available (install @higgsfield/cli)"
        print(f"[MCP] Registered Higgsfield CLI fallback tools (CLI {status}).", flush=True)

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
                except asyncio.CancelledError:
                    break
                except (ConnectionClosedError, asyncio.TimeoutError, Exception) as e:
                    # If the server responded with a 401 or we explicitly raised AuthRequiredError,
                    # attempt CLI auth and continue retrying in background.
                    if isinstance(e, AuthRequiredError) or ('401' in str(e)):
                        if not self.auth_pending:
                            self.auth_pending = True
                            print(
                                "\n[MCP] Higgsfield MCP returned 401. "
                                "Attempting CLI login to refresh credentials...",
                                flush=True,
                            )
                            try:
                                # Attempt non-interactive CLI auth refresh
                                cli = _higgsfield_cli_path()
                                if cli:
                                    proc = await asyncio.create_subprocess_exec(
                                        cli, "auth", "login",
                                        stdout=asyncio.subprocess.PIPE,
                                        stderr=asyncio.subprocess.PIPE,
                                    )
                                    auth_out, auth_err = await asyncio.wait_for(
                                        proc.communicate(), timeout=180
                                    )
                                    print(
                                        f"[MCP] CLI auth result (rc={proc.returncode}):\n"
                                        f"{auth_out.decode(errors='replace').strip()}",
                                        flush=True,
                                    )
                                else:
                                    print(
                                        "[MCP] Higgsfield CLI not found. "
                                        "Please install via: npm install -g @higgsfield/cli",
                                        flush=True,
                                    )
                            except Exception as auth_err_exc:
                                logger.warning(f"[MCP] CLI auth attempt failed: {auth_err_exc}")
                            finally:
                                self.auth_pending = False
                            backoff = 5
                        else:
                            await asyncio.sleep(backoff)
                        continue
                    
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
                                    # Signal to outer loop that auth is required
                                    raise AuthRequiredError("Authentication required – browser opened.")
                                raise err
                        return handler

                    handler_fn = await make_handler(tool_name, tool.name, session)
                    # Overwrite CLI fallback with live session handler
                    self.tool_registry.register(tool_name, handler_fn)
                    
                    # Update dynamic declarations (replace existing CLI declaration if present)
                    existing = self.tool_registry._dynamic_declarations
                    self.tool_registry._dynamic_declarations = [
                        d for d in existing if d.get("name") != tool_name
                    ]
                    self.tool_registry._dynamic_declarations.append(gemini_schema)
                    has_new_tool = True
                    print(f"[MCP] Registered tool '{tool_name}' (live session)", flush=True)
                    
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
