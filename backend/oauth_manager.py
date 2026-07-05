import json
import asyncio
import time
import os
import webbrowser
from pathlib import Path
from typing import Optional, Dict, Any, Callable

# Browser credentials older than this are considered expired (30 days)
BROWSER_CREDENTIAL_MAX_AGE_DAYS = 30

try:
    from backend.db import (
        store_oauth_credential, get_oauth_credential, 
        delete_oauth_credential, list_oauth_credentials
    )
except ImportError:
    from db import (
        store_oauth_credential, get_oauth_credential,
        delete_oauth_credential, list_oauth_credentials
    )


class OAuthManager:
    """
    Generic OAuth/browser-based authentication manager.
    
    Supports two auth modes:
    - browser: Opens Playwright browser, user logs in, cookies captured
    - oauth: Standard OAuth 2.0 flow (authorization URL -> callback -> token exchange)
    
    Providers register their config, and the manager handles the rest.
    """
    
    def __init__(self, sio=None):
        self.sio = sio
        self._providers: Dict[str, Dict[str, Any]] = {}
        self._clients: Dict[str, Any] = {}
        self._login_in_progress: Optional[str] = None
        self._login_complete_event = asyncio.Event()
        
    def register_provider(self, name: str, config: Dict[str, Any]):
        """
        Register an auth provider.
        
        Config keys:
            name: Provider identifier
            auth_type: "browser" or "oauth"
            login_url: URL to open in browser
            handler: Async function to handle auth (capture cookies/tokens)
            client_factory: Function to create authenticated client from credentials
            scopes: List of OAuth scopes (for oauth type)
            auth_url: OAuth authorization URL (for oauth type)
            token_url: OAuth token exchange URL (for oauth type)
            client_id: OAuth client ID (for oauth type)
            client_secret: OAuth client secret (for oauth type)
        """
        self._providers[name] = config
        print(f"[OAuthManager] Registered provider: {name} (type: {config.get('auth_type', 'browser')})")
        
    def get_provider(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a registered provider config."""
        return self._providers.get(name)
    
    def list_providers(self) -> list:
        """List all registered provider names."""
        return list(self._providers.keys())
    
    def is_authenticated(self, provider: str) -> bool:
        """Check if we have valid credentials for a provider."""
        creds = get_oauth_credential(provider)
        if not creds:
            return False
        
        # Check if credentials have expired (if expiry is set)
        if creds.get("token_expiry"):
            try:
                expiry = float(creds["token_expiry"])
                if time.time() > expiry:
                    return False
            except (ValueError, TypeError):
                pass
        
        # For browser-based auth, check if credentials are too old
        config = self._providers.get(provider, {})
        if config.get("auth_type") == "browser" and not creds.get("token_expiry"):
            last_verified = creds.get("last_verified")
            if last_verified:
                try:
                    age_days = (time.time() - float(last_verified)) / 86400
                    if age_days > BROWSER_CREDENTIAL_MAX_AGE_DAYS:
                        return False
                except (ValueError, TypeError):
                    pass
        
        return True
    
    def get_credentials(self, provider: str) -> Optional[Dict[str, Any]]:
        """Get stored credentials for a provider."""
        return get_oauth_credential(provider)
    
    def store_credentials(self, provider: str, credentials: Dict[str, Any]):
        """Store credentials for a provider."""
        store_oauth_credential(provider, credentials)
        print(f"[OAuthManager] Stored credentials for {provider}")
    
    def clear_credentials(self, provider: str):
        """Clear stored credentials for a provider."""
        delete_oauth_credential(provider)
        self._clients.pop(provider, None)
        print(f"[OAuthManager] Cleared credentials for {provider}")
    
    async def start_login(self, provider: str, sio=None) -> Dict[str, Any]:
        """
        Start the login flow for a provider.
        
        For browser auth: Opens browser, waits for user to log in, captures cookies
        For oauth: Opens browser to auth URL, waits for callback
        
        Returns dict with status and message.
        """
        if provider not in self._providers:
            return {"status": "error", "message": f"Unknown provider: {provider}"}
        
        if self._login_in_progress:
            return {"status": "error", "message": f"Login already in progress for: {self._login_in_progress}"}
        
        config = self._providers[provider]
        auth_type = config.get("auth_type", "browser")
        
        self._login_in_progress = provider
        self._login_complete_event.clear()
        
        try:
            if auth_type == "browser":
                result = await self._browser_login(provider, config, sio)
            elif auth_type == "oauth":
                result = await self._oauth_login(provider, config, sio)
            else:
                result = {"status": "error", "message": f"Unknown auth type: {auth_type}"}
            
            return result
        finally:
            self._login_in_progress = None
    
    async def _browser_login(self, provider: str, config: Dict, sio=None) -> Dict[str, Any]:
        """Handle browser-based login (e.g., YouTube Music)."""
        handler = config.get("handler")
        if not handler:
            return {"status": "error", "message": f"No handler configured for {provider}"}
        
        try:
            # Call the provider's handler to capture credentials
            credentials = await handler(config, sio)
            
            if credentials:
                # Add timestamp for browser credential age tracking
                config = self._providers.get(provider, {})
                if config.get("auth_type") == "browser":
                    credentials["last_verified"] = str(time.time())
                
                self.store_credentials(provider, credentials)
                
                # Create client if factory is provided
                client_factory = config.get("client_factory")
                if client_factory:
                    self._clients[provider] = client_factory(credentials)
                
                return {
                    "status": "success", 
                    "message": f"Successfully authenticated with {provider}",
                    "provider": provider
                }
            else:
                return {"status": "error", "message": f"Login failed or was cancelled for {provider}"}
                
        except Exception as e:
            print(f"[OAuthManager] Browser login error for {provider}: {e}")
            return {"status": "error", "message": f"Login error: {str(e)}"}
    
    async def _oauth_login(self, provider: str, config: Dict, sio=None) -> Dict[str, Any]:
        """Handle standard OAuth 2.0 login flow."""
        try:
            from aiohttp import web
            import aiohttp
            
            client_id = config.get("client_id") or os.getenv(f"{provider.upper()}_CLIENT_ID")
            client_secret = config.get("client_secret") or os.getenv(f"{provider.upper()}_CLIENT_SECRET")
            
            if not client_id or not client_secret:
                return {"status": "error", "message": f"Missing client_id/client_secret for {provider}"}
            
            scopes = config.get("scopes", [])
            auth_url = config.get("auth_url")
            token_url = config.get("token_url")
            redirect_port = config.get("redirect_port", 8181)
            redirect_uri = f"http://localhost:{redirect_port}/callback"
            
            if not auth_url or not token_url:
                return {"status": "error", "message": f"Missing auth_url/token_url for {provider}"}
            
            # Build authorization URL
            scope_str = " ".join(scopes) if scopes else ""
            auth_params = {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": scope_str,
                "access_type": "offline",
                "prompt": "consent"
            }
            
            query_string = "&".join(f"{k}={v}" for k, v in auth_params.items())
            full_auth_url = f"{auth_url}?{query_string}"
            
            # Start temporary callback server
            auth_code = None
            
            async def handle_callback(request):
                nonlocal auth_code
                code = request.query.get("code")
                if code:
                    auth_code = code
                    return web.Response(
                        text="<html><body><h1>Authorization Complete!</h1><p>You may close this tab.</p></body></html>",
                        content_type="text/html"
                    )
                else:
                    error = request.query.get("error", "unknown")
                    return web.Response(
                        text=f"<html><body><h1>Authorization Failed</h1><p>Error: {error}</p></body></html>",
                        content_type="text/html"
                    )
            
            app = web.Application()
            app.router.add_get("/callback", handle_callback)
            
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, "localhost", redirect_port)
            await site.start()
            
            # Open browser to auth URL
            webbrowser.open(full_auth_url)
            
            # Wait for callback (with timeout)
            timeout = 120  # 2 minutes
            start_time = time.time()
            while auth_code is None and (time.time() - start_time) < timeout:
                await asyncio.sleep(0.5)
            
            await runner.cleanup()
            
            if not auth_code:
                return {"status": "error", "message": "Authorization timed out"}
            
            # Exchange code for tokens
            import httpx
            
            token_data = {
                "code": auth_code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(token_url, data=token_data)
                response.raise_for_status()
                tokens = response.json()
            
            # Add token expiry timestamp
            if "expires_in" in tokens:
                tokens["token_expiry"] = str(time.time() + tokens["expires_in"])
            
            self.store_credentials(provider, tokens)
            
            # Create client if factory is provided
            client_factory = config.get("client_factory")
            if client_factory:
                self._clients[provider] = client_factory(tokens)
            
            return {
                "status": "success",
                "message": f"Successfully authenticated with {provider}",
                "provider": provider
            }
            
        except Exception as e:
            print(f"[OAuthManager] OAuth login error for {provider}: {e}")
            return {"status": "error", "message": f"Login error: {str(e)}"}
    
    def get_client(self, provider: str) -> Optional[Any]:
        """Get the authenticated client for a provider."""
        if provider in self._clients:
            return self._clients[provider]
        
        # Try to create client from stored credentials
        creds = self.get_credentials(provider)
        if creds:
            config = self._providers.get(provider, {})
            client_factory = config.get("client_factory")
            if client_factory:
                self._clients[provider] = client_factory(creds)
                return self._clients[provider]
        
        return None
    
    async def refresh_if_needed(self, provider: str) -> bool:
        """Refresh credentials if needed (for OAuth providers with refresh tokens)."""
        config = self._providers.get(provider, {})
        if config.get("auth_type") != "oauth":
            return True  # Browser auth doesn't have refresh
        
        creds = self.get_credentials(provider)
        if not creds:
            return False
        
        # Check if token is expired or about to expire
        expiry = creds.get("token_expiry")
        if expiry:
            try:
                if time.time() < float(expiry) - 300:  # 5 min buffer
                    return True  # Still valid
            except (ValueError, TypeError):
                pass
        
        # Try to refresh
        refresh_token = creds.get("refresh_token")
        if not refresh_token:
            return False
        
        try:
            import httpx
            
            client_id = config.get("client_id") or os.getenv(f"{provider.upper()}_CLIENT_ID")
            client_secret = config.get("client_secret") or os.getenv(f"{provider.upper()}_CLIENT_SECRET")
            token_url = config.get("token_url")
            
            refresh_data = {
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(token_url, data=refresh_data)
                response.raise_for_status()
                new_tokens = response.json()
            
            # Merge with existing (keep refresh_token if not in response)
            if "refresh_token" not in new_tokens:
                new_tokens["refresh_token"] = refresh_token
            
            if "expires_in" in new_tokens:
                new_tokens["token_expiry"] = str(time.time() + new_tokens["expires_in"])
            
            self.store_credentials(provider, new_tokens)
            
            # Update client
            client_factory = config.get("client_factory")
            if client_factory:
                self._clients[provider] = client_factory(new_tokens)
            
            return True
            
        except Exception as e:
            print(f"[OAuthManager] Token refresh failed for {provider}: {e}")
            return False
