"""
YouTube Music provider — Browser-based authentication via ytmusicapi.

Opens a Playwright browser to YouTube Music, lets the user log in,
captures the session cookies, and creates an authenticated YTMusic instance.
"""

import json
import asyncio
import os
from typing import Dict, Any, Optional

try:
    from ytmusicapi import YTMusic
    from ytmusicapi.auth.browser import setup_browser
except ImportError:
    YTMusic = None
    setup_browser = None


async def _capture_youtube_music_cookies(config: Dict, sio=None) -> Optional[Dict]:
    """
    Open Playwright browser to YouTube Music, wait for user login,
    capture cookies and return them as a dict.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[YouTubeMusic] Playwright not installed")
        return None
    
    login_url = config.get("login_url", "https://music.youtube.com")
    
    print(f"[YouTubeMusic] Opening browser to {login_url}")
    
    # Notify frontend that login is starting
    if sio:
        await sio.emit("oauth_status", {
            "provider": "youtube_music",
            "status": "starting",
            "message": "Opening browser for YouTube Music login..."
        })
    
    try:
        async with async_playwright() as p:
            # Launch visible browser so user can log in
            try:
                browser = await p.chromium.launch(headless=False, channel="chrome")
            except Exception as e:
                print(f"[YouTubeMusic] Failed to launch chrome channel, falling back to default chromium: {e}")
                browser = await p.chromium.launch(headless=False)
                
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            )
            
            page = await context.new_page()
            
            # Navigate to YouTube Music
            await page.goto(login_url, wait_until="networkidle")
            
            print("[YouTubeMusic] Browser opened. Waiting for user to log in...")
            
            # Notify frontend
            if sio:
                await sio.emit("oauth_status", {
                    "provider": "youtube_music",
                    "status": "waiting",
                    "message": "Please log in to YouTube Music in the browser window. Click 'I'm logged in' when done."
                })
            
            # Wait for user to indicate they're logged in via socket event
            # Or detect login by monitoring cookies/localStorage
            logged_in = await _wait_for_login(page, context, sio)
            
            if not logged_in:
                print("[YouTubeMusic] Login timed out or was cancelled")
                await browser.close()
                return None
            
            # Capture cookies
            cookies = await context.cookies()
            
            # Capture localStorage for additional auth data
            local_storage = await page.evaluate("""() => {
                const data = {};
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i);
                    data[key] = localStorage.getItem(key);
                }
                return data;
            }""")
            
            # Capture the essential headers that ytmusicapi needs
            # Extract SAPISID and other auth-related cookies
            auth_cookies = {}
            for cookie in cookies:
                auth_cookies[cookie["name"]] = cookie["value"]
            
            # Build the headers dict that ytmusicapi expects
            headers = {
                "cookie": "; ".join(f"{c['name']}={c['value']}" for c in cookies if "youtube" in c.get("domain", "")),
                "x-goog-authuser": auth_cookies.get("AUTH_USER", "0"),
            }
            
            # Add SAPISID-based auth if present
            sapisid = auth_cookies.get("__Secure-3PAPISID") or auth_cookies.get("SAPISID")
            if sapisid:
                headers["authorization"] = f"SAPISIDHASH {sapisid}"
            
            # Build credentials dict
            credentials = {
                "headers": headers,
                "cookies": auth_cookies,
                "local_storage": local_storage,
                "all_cookies": cookies,
            }
            
            # Get account info if possible
            try:
                account_name = await page.evaluate("""() => {
                    const el = document.querySelector('#img[alt]');
                    return el ? el.alt : null;
                }""")
                if account_name:
                    credentials["account_name"] = account_name
            except Exception:
                pass
            
            print(f"[YouTubeMusic] Captured {len(cookies)} cookies")
            
            await browser.close()
            
            return credentials
        
    except Exception as e:
        print(f"[YouTubeMusic] Error during login: {e}")
        return None


async def _wait_for_login(page, context, sio=None, timeout=300) -> bool:
    """
    Wait for user to complete login.
    
    Detects login by:
    1. Listening for a socket event from frontend ("youtube_music_login_complete")
    2. Monitoring for presence of auth cookies
    """
    # Create an event to signal login completion
    login_event = asyncio.Event()
    
    # Register socket handler if sio is available
    if sio:
        async def on_login_complete(data):
            print("[YouTubeMusic] Received login confirmation from frontend")
            login_event.set()
        
        sio.on("youtube_music_login_complete", on_login_complete)
    
    start_time = asyncio.get_event_loop().time()
    
    while not login_event.is_set():
        # Check timeout
        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed > timeout:
            print("[YouTubeMusic] Login timeout")
            return False
            
        if page.is_closed():
            print("[YouTubeMusic] Browser page was closed by user")
            # If closed, maybe they finished login, so check cookies one last time
            try:
                cookies = await context.cookies()
                youtube_cookies = [c for c in cookies if "youtube" in c.get("domain", "")]
                auth_cookie_names = ["__Secure-3PAPISID", "SAPISID", "SID", "HSID", "SSID", "APISID"]
                found = [c["name"] for c in youtube_cookies if c["name"] in auth_cookie_names]
                if len(found) >= 2:
                    return True
            except Exception:
                pass
            return False
        
        # Also check for auth cookies as a fallback detection
        try:
            cookies = await context.cookies()
            youtube_cookies = [c for c in cookies if "youtube" in c.get("domain", "")]
            auth_cookie_names = ["__Secure-3PAPISID", "SAPISID", "SID", "HSID", "SSID", "APISID"]
            found = [c["name"] for c in youtube_cookies if c["name"] in auth_cookie_names]
            
            if len(found) >= 2:  # Multiple auth cookies on youtube domain = likely logged in
                # Wait a tiny bit for any final redirects to finish
                await asyncio.sleep(2)
                print(f"[YouTubeMusic] Detected login via cookies: {found}")
                return True
        except Exception:
            pass
        
        await asyncio.sleep(1)
    
    return True


def _create_ytmusic_client(credentials: Dict) -> "YTMusic":
    """
    Create an authenticated YTMusic instance from captured credentials.
    
    ytmusicapi expects a headers dict or a file path to a headers JSON.
    We'll create the headers dict directly.
    """
    if YTMusic is None:
        print("[YouTubeMusic] ytmusicapi not installed")
        return None
    
    headers = credentials.get("headers", {})
    
    # ytmusicapi can accept headers dict directly
    # But we need to format it correctly - it expects the raw HTTP headers
    # Let's try creating a temporary file with the headers
    
    import tempfile
    import json
    
    # Build the proper header format for ytmusicapi
    # It expects specific header names
    ytmusic_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    # Add cookie header
    if "cookie" in headers:
        ytmusic_headers["cookie"] = headers["cookie"]
    
    # Add auth user
    if "x-goog-authuser" in headers:
        ytmusic_headers["x-goog-authuser"] = headers["x-goog-authuser"]
        
    # Add authorization header (critical for ytmusicapi to recognize BROWSER auth)
    if "authorization" in headers:
        ytmusic_headers["authorization"] = headers["authorization"]
    
    # Try to use the browser auth setup
    try:
        # Create a temp file with the headers
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(ytmusic_headers, f)
            temp_path = f.name
        
        yt = YTMusic(auth=temp_path)
        
        # Clean up temp file
        try:
            os.unlink(temp_path)
        except Exception:
            pass
        
        return yt
    except Exception as e:
        print(f"[YouTubeMusic] Error creating YTMusic client: {e}")
        return None


def get_provider_config() -> Dict[str, Any]:
    """Return the provider config for YouTube Music."""
    return {
        "name": "youtube_music",
        "auth_type": "browser",
        "login_url": "https://music.youtube.com",
        "handler": _capture_youtube_music_cookies,
        "client_factory": _create_ytmusic_client,
        "description": "YouTube Music - access your library, playlists, liked songs, and history",
    }
