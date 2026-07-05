# Issue: YouTube Music Saved Playlists Not Accessible After Sign-In

## Root Causes

### 1. Incorrect SAPISIDHASH Generation (Critical)
**File:** `backend/providers/youtube_music.py:108-110`

The current code generates the authorization header as:
```python
headers["authorization"] = f"SAPISIDHASH {sapisid}"
```

This is wrong. The SAPISIDHASH must be computed as:
```
SAPISIDHASH {timestamp}_{sha1(timestamp + " " + origin + " " + sapisid)}
```

Without the correct hash, all authenticated API calls (including `get_library_playlists`) will fail with 401 errors, even though cookies are valid.

### 2. No Error Recovery on Auth Failure
**File:** `backend/music_agent.py:735-751`

When `get_library_playlists()` throws an exception (e.g., 401 from expired/invalid auth), the error is caught and returned as a string, but `self._authenticated` is **never set to False**. The agent stays in a broken "authenticated" state where every library call fails silently.

### 3. No Cookie Expiration Handling
**File:** `backend/oauth_manager.py:66-81`

Browser-captured credentials don't set `token_expiry`, so `is_authenticated()` always returns True for stored credentials — even when cookies have expired. The user gets no clear signal to re-login.

## Proposed Fixes

### Fix 1: Compute SAPISIDHASH correctly (`youtube_music.py`)
Replace the incorrect hash generation with proper SHA1-based computation:
```python
import hashlib
import time

sapisid = auth_cookies.get("__Secure-3PAPISID") or auth_cookies.get("SAPISID")
if sapisid:
    timestamp = str(int(time.time()))
    origin = "https://music.youtube.com"
    hash_input = f"{timestamp} {origin} {sapisid}"
    sapisid_hash = hashlib.sha1(hash_input.encode()).hexdigest()
    headers["authorization"] = f"SAPISIDHASH {timestamp}_{sapisid_hash}"
```

### Fix 2: Add error recovery in library methods (`music_agent.py`)
In each authenticated method (`get_library_playlists`, `get_library_songs`, `get_history`, etc.), catch exceptions and set `self._authenticated = False` so the user gets a clear "not signed in" message instead of a cryptic API error.

### Fix 3: Add cookie expiration check (`oauth_manager.py`)
Add a `last_verified` timestamp to browser-captured credentials. In `is_authenticated()`, treat credentials older than a configurable threshold (e.g., 30 days) as expired, prompting re-authentication.

## Files to Modify
1. `backend/providers/youtube_music.py` — Fix SAPISIDHASH computation
2. `backend/music_agent.py` — Add error recovery to all authenticated methods
3. `backend/oauth_manager.py` — Add expiration check for browser credentials
