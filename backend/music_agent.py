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
            # Launch headless
            self.browser = await p.chromium.launch(headless=True, args=["--autoplay-policy=no-user-gesture-required"])
            self.context = await self.browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            self.page = await self.context.new_page()
            await self.page.goto("https://music.youtube.com")

            # Handle "Sign in" or cookie popups
            try:
                # Common consent buttons
                await self.page.click("button[aria-label='Reject all']", timeout=2000)
            except:
                pass

            try:
                await self.page.click("yt-button-renderer#dismiss-button", timeout=2000)
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
            # 1. Activate Search
            # Try clicking the search icon if the input isn't visible
            try:
                await self.page.click("ytmusic-search-box", timeout=3000)
            except:
                pass # Maybe already active or different layout

            # Fill input (ensure we target the visible input)
            await self.page.fill("input.ytmusic-search-box", query)
            await self.page.keyboard.press("Enter")

            # 2. Wait for Results
            # Wait for at least one shelf or list item
            await self.page.wait_for_selector("ytmusic-shelf-renderer, ytmusic-card-shelf-renderer, ytmusic-responsive-list-item-renderer", timeout=10000)

            # 3. Click "Play" on Top Result or First Song
            # Strategy A: Look for the big "Play" button in the "Top result" card
            # Strategy B: Hover over the first list item and click the play overlay

            # Try finding the "Top result" play button
            try:
                top_result_play = self.page.locator("ytmusic-card-shelf-renderer ytmusic-play-button-renderer").first
                if await top_result_play.is_visible(timeout=2000):
                    await top_result_play.click()
                    self.is_playing = True
                    return f"Playing {query} (Top Result)."
            except:
                pass

            # Try finding the first song in a list
            # We target the overlay play button which appears on hover, OR just click the item with force=True
            try:
                first_item = self.page.locator("ytmusic-responsive-list-item-renderer").first
                await first_item.scroll_into_view_if_needed()
                await first_item.hover() # Hover to show play button

                # Try clicking the play button inside it
                play_btn = first_item.locator("ytmusic-play-button-renderer")
                if await play_btn.count() > 0:
                    await play_btn.first.click(force=True, timeout=3000)
                else:
                    # Just click the item itself (might open album page, but often plays)
                    await first_item.click(force=True, timeout=3000)

                self.is_playing = True
                return f"Playing {query} (First Song)."
            except Exception as e:
                self.logger.error(f"Failed to click item: {e}")

        except Exception as e:
            self.logger.error(f"Search/Play failed: {e}")
            return f"Failed to play music: {e}"

        return f"Request sent for {query}."

    async def control(self, action):
        """Controls playback."""
        if not self.browser:
            return "Music agent not running."

        self.logger.info(f"Music Control: {action}")
        try:
            if action == "play" or action == "resume":
                # Toggle play/pause button if it indicates "Play"
                play_pause_btn = self.page.locator("#play-pause-button")
                title = await play_pause_btn.get_attribute("title")
                if title == "Play":
                    await play_pause_btn.click()
                    self.is_playing = True
                    return "Resumed playback."
                return "Already playing or button not found."

            elif action == "pause":
                play_pause_btn = self.page.locator("#play-pause-button")
                title = await play_pause_btn.get_attribute("title")
                if title == "Pause":
                    await play_pause_btn.click()
                    self.is_playing = False
                    return "Paused playback."
                return "Already paused."

            elif action == "next":
                await self.page.click(".next-button")
                return "Skipped to next track."

            elif action == "previous" or action == "prev":
                await self.page.click(".previous-button")
                return "Skipped to previous track."

            elif action == "volume_up":
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
                    title = await self.page.text_content(".content-info-wrapper .title", timeout=1000)
                    artist = await self.page.text_content(".content-info-wrapper .subtitle", timeout=1000)
                    time_info = await self.page.text_content(".time-info", timeout=1000)

                    self.current_track = {
                        "title": title or "Unknown",
                        "artist": artist or "Unknown",
                        "time": time_info or "0:00"
                    }

                    play_btn_title = await self.page.get_attribute("#play-pause-button", "title", timeout=1000)
                    status = "playing" if play_btn_title == "Pause" else "paused"
                    self.is_playing = (status == "playing")

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
                data = []
                for i in range(64):
                    val = random.randint(0, 255)
                    if i < 10: val = max(val, random.randint(100, 255))
                    data.append(val)

                await self.sio.emit('music_vis_data', {"data": data})

            await asyncio.sleep(0.033)
