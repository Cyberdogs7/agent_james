import asyncio
import logging
import random
from playwright.async_api import async_playwright

class MusicAgent:
    def __init__(self, sio=None):
        self.sio = sio
        self.browser = None
        self.context = None
        self.page = None
        self.is_playing = False
        self.current_track = {"title": "Unknown", "artist": "Unknown", "time": "0:00"}
        self.logger = logging.getLogger("MusicAgent")
        self.logger.setLevel(logging.INFO)
        self._stop_event = asyncio.Event()
        self._vis_task = None
        self._status_task = None

    async def start(self):
        """Launches the browser and navigates to YouTube Music."""
        if self.browser:
            return

        self.logger.info("Starting MusicAgent...")
        try:
            p = await async_playwright().start()
            # Launch headless for now, maybe headed for debugging if needed
            self.browser = await p.chromium.launch(headless=True, args=["--autoplay-policy=no-user-gesture-required"])
            self.context = await self.browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            self.page = await self.context.new_page()
            await self.page.goto("https://music.youtube.com")

            # Handle potential "Sign in" or cookie popups
            try:
                # Click "Reject all" cookies if present (common in EU)
                # Selectors might vary, try common ones
                await self.page.click("button[aria-label='Reject all']", timeout=2000)
            except:
                pass

            self.logger.info("MusicAgent started successfully.")

            # Start background loops
            self._vis_task = asyncio.create_task(self._vis_loop())
            self._status_task = asyncio.create_task(self._status_loop())

        except Exception as e:
            self.logger.error(f"Failed to start MusicAgent: {e}")

    async def stop(self):
        """Stops the browser and background tasks."""
        self._stop_event.set()
        if self._vis_task:
            self._vis_task.cancel()
        if self._status_task:
            self._status_task.cancel()

        if self.browser:
            await self.browser.close()
            self.browser = None
        self.logger.info("MusicAgent stopped.")

    async def play(self, query):
        """Searches for a query and plays the first result."""
        if not self.browser:
            await self.start()

        self.logger.info(f"Searching for: {query}")
        try:
            # Click search button
            await self.page.click("ytmusic-search-box", timeout=5000)
            await self.page.fill("input#input", query)
            await self.page.keyboard.press("Enter")

            # Wait for results
            await self.page.wait_for_selector("ytmusic-shelf-renderer", timeout=5000)

            # Click the first result (usually "Top result" or "Songs")
            # We target the play button on the first result
            # Try a generic approach: click the first item in the list
            # Usually the top result has a play button overlay
            await self.page.click("ytmusic-card-shelf-renderer ytmusic-play-button-renderer", timeout=2000)

        except Exception:
            # Fallback: try clicking the first item in the list directly
            try:
                await self.page.click("ytmusic-responsive-list-item-renderer", timeout=2000)
            except Exception as e:
                self.logger.error(f"Failed to play music: {e}")
                return f"Failed to play music: {e}"

        self.is_playing = True
        return f"Playing {query} on YouTube Music."

    async def control(self, action):
        """Controls playback."""
        if not self.browser:
            return "Music agent not running."

        self.logger.info(f"Music Control: {action}")
        try:
            if action == "play" or action == "resume":
                # Check if paused
                # The play/pause button is usually #play-pause-button
                # If it has 'title="Pause"', it's playing. If 'title="Play"', it's paused.
                title = await self.page.get_attribute("#play-pause-button", "title")
                if title == "Play":
                    await self.page.click("#play-pause-button")
                    self.is_playing = True
                    return "Resumed playback."
                else:
                    return "Already playing."

            elif action == "pause":
                title = await self.page.get_attribute("#play-pause-button", "title")
                if title == "Pause":
                    await self.page.click("#play-pause-button")
                    self.is_playing = False
                    return "Paused playback."
                else:
                    return "Already paused."

            elif action == "next":
                await self.page.click(".next-button")
                return "Skipped to next track."

            elif action == "previous" or action == "prev":
                await self.page.click(".previous-button")
                return "Skipped to previous track."

            elif action == "volume_up":
                # Volume slider is tricky. Use keyboard shortcut 'up arrow' focused on player?
                # Or try to set volume via JS
                # document.querySelector('video').volume += 0.1
                await self.page.evaluate("document.querySelector('video').volume = Math.min(1, document.querySelector('video').volume + 0.1)")
                return "Volume up."

            elif action == "volume_down":
                await self.page.evaluate("document.querySelector('video').volume = Math.max(0, document.querySelector('video').volume - 0.1)")
                return "Volume down."

        except Exception as e:
            self.logger.error(f"Control error: {e}")
            return f"Failed to perform action {action}: {e}"

    async def _status_loop(self):
        """Periodically scrapes track info."""
        while not self._stop_event.is_set():
            if self.browser and self.page:
                try:
                    # Scrape info
                    # Title: .content-info-wrapper .title
                    # Artist: .content-info-wrapper .subtitle
                    # Time: .time-info

                    title = await self.page.text_content(".content-info-wrapper .title", timeout=1000)
                    artist = await self.page.text_content(".content-info-wrapper .subtitle", timeout=1000)
                    time_info = await self.page.text_content(".time-info", timeout=1000)

                    # Update state
                    self.current_track = {
                        "title": title or "Unknown",
                        "artist": artist or "Unknown",
                        "time": time_info or "0:00"
                    }

                    # Determine status
                    play_btn_title = await self.page.get_attribute("#play-pause-button", "title", timeout=1000)
                    status = "playing" if play_btn_title == "Pause" else "paused"
                    self.is_playing = (status == "playing")

                    # Emit status
                    if self.sio:
                        await self.sio.emit('music_status', {
                            "status": status,
                            "track": self.current_track
                        })

                except Exception:
                    pass

            await asyncio.sleep(2)

    async def _vis_loop(self):
        """Emits dummy visualization data."""
        while not self._stop_event.is_set():
            if self.is_playing and self.sio:
                # Generate 64 random bytes (0-255)
                # Make it look somewhat like a spectrum (more bass)
                data = []
                for i in range(64):
                    # Simple noise
                    val = random.randint(0, 255)
                    # Apply some 'bass' bias
                    if i < 10: val = max(val, random.randint(100, 255))
                    data.append(val)

                await self.sio.emit('music_vis_data', {"data": data})

            # 30 FPS approx
            await asyncio.sleep(0.033)
