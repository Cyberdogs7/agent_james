import asyncio
import logging
import random
import shutil
import subprocess
import threading
import time
from ytmusicapi import YTMusic
import yt_dlp

class MusicAgent:
    def __init__(self, sio=None):
        self.sio = sio
        self.yt = YTMusic()
        self.current_track = {"title": "Unknown", "artist": "Unknown", "time": "0:00"}
        self.is_playing = False
        self.logger = logging.getLogger("MusicAgent")
        self.logger.setLevel(logging.INFO)

        self.ffmpeg_process = None
        self._stop_event = asyncio.Event()
        self._audio_queue = None # Set by ada.py if pushing to global mix

        # Internal state
        self.volume = 1.0
        self.paused = False

    def set_audio_queue(self, queue):
        """Allows ADA to inject the main audio queue."""
        self._audio_queue = queue

    async def start(self):
        """No-op for API version, but kept for compatibility."""
        self.logger.info("MusicAgent (API) ready.")

    async def stop(self):
        """Stops playback."""
        self._stop_event.set()
        await self._kill_ffmpeg()
        self.is_playing = False
        self.logger.info("MusicAgent stopped.")

    async def _kill_ffmpeg(self):
        if self.ffmpeg_process:
            try:
                self.ffmpeg_process.terminate()
                self.ffmpeg_process.wait()
            except:
                pass
            self.ffmpeg_process = None

    async def play(self, query):
        """Searches for a query and streams it."""
        self.logger.info(f"Searching for: {query}")

        if not shutil.which('ffmpeg'):
            err_msg = "Failed to play music: ffmpeg is not installed or not found in system PATH. Please install ffmpeg to enable music playback."
            self.logger.error(err_msg)
            return err_msg

        try:
            # 1. Search
            # Run in thread to avoid blocking
            results = await asyncio.to_thread(self.yt.search, query, filter="songs")
            if not results:
                return f"No results found for {query}"

            top_result = results[0]
            video_id = top_result['videoId']
            title = top_result['title']
            artists = ", ".join([a['name'] for a in top_result['artists']])

            self.current_track = {
                "title": title,
                "artist": artists,
                "time": "Streaming"
            }
            self.logger.info(f"Found: {title} by {artists} ({video_id})")

            # 2. Get Stream URL via yt-dlp
            # Run in thread
            ydl_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True
            }

            def get_url(vid):
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
                    return info['url']

            stream_url = await asyncio.to_thread(get_url, video_id)

            # 3. Start Streaming via FFmpeg
            await self._kill_ffmpeg()

            # FFmpeg command to output PCM S16LE 24000Hz Mono (matching ADA's default)
            # ADA uses 24000Hz for receive/playback
            cmd = [
                'ffmpeg',
                '-re', # Read at native frame rate (important for streaming)
                '-i', stream_url,
                '-f', 's16le',
                '-acodec', 'pcm_s16le',
                '-ac', '1', # Mono
                '-ar', '24000', # Sample Rate
                '-vn', # No video
                '-loglevel', 'quiet',
                '-' # Output to pipe
            ]

            self.ffmpeg_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=1024 * 10
            )

            self.is_playing = True
            self.paused = False

            # Start background reader task
            asyncio.create_task(self._stream_reader())

            # Emit status
            if self.sio:
                await self.sio.emit('music_status', {
                    "status": "playing",
                    "track": self.current_track
                })

            return f"Playing {title} by {artists}"

        except Exception as e:
            self.logger.error(f"Play failed: {e}")
            return f"Failed to play music: {e}"

    async def _stream_reader(self):
        """Reads from ffmpeg stdout and pushes to audio queue."""
        chunk_size = 1024

        while self.is_playing and self.ffmpeg_process:
            if self.paused:
                await asyncio.sleep(0.1)
                continue

            if self.ffmpeg_process.poll() is not None:
                self.logger.info("FFmpeg process finished.")
                self.is_playing = False
                break

            # Read chunk in thread
            data = await asyncio.to_thread(self.ffmpeg_process.stdout.read, chunk_size)

            if not data:
                break

            # Push to ADA's queue if available
            if self._audio_queue:
                # We can apply volume here if we want to do DSP, but for now just raw
                # Visualization logic
                if self.sio:
                    # Simple volume-based vis
                    # Sample a few bytes
                    import struct
                    import math

                    # Async emit to avoid blocking audio loop
                    if random.random() < 0.1: # Don't flood
                        try:
                            # Generate pseudo-spectrum
                            vis_data = [min(255, b + random.randint(0, 50)) for b in data[:64]]
                            asyncio.create_task(self.sio.emit('music_vis_data', {"data": vis_data}))
                        except:
                            pass

                await self._audio_queue.put(data)

            # Since we used -re in ffmpeg, it limits speed, but we should yield
            await asyncio.sleep(0) # Yield

        self.is_playing = False
        if self.sio:
             await self.sio.emit('music_status', {
                "status": "stopped",
                "track": None
            })

    async def control(self, action):
        """Controls playback."""
        self.logger.info(f"Music Control: {action}")

        if action == "play" or action == "resume":
            if not self.is_playing: return "No track loaded."
            self.paused = False
            if self.ffmpeg_process:
                # Sending SIGCONT is unix specific, but we are just controlling the loop reading
                # For ffmpeg -re, stopping read might cause buffer overflow?
                # Better to just discard data if paused? No, resume should pick up.
                # Actually, simplest pause is to stop reading from stdout in the loop
                pass
            return "Resumed."

        elif action == "pause":
            if self.is_playing:
                self.paused = True
                return "Paused."
            return "Not playing."

        elif action == "stop":
            await self.stop()
            return "Stopped."

        elif action == "volume_up":
            # Just a stub unless we implement DSP volume scaling on chunks
            self.volume = min(1.0, self.volume + 0.1)
            return "Volume up (Software)."

        elif action == "volume_down":
            self.volume = max(0.0, self.volume - 0.1)
            return "Volume down (Software)."

        return "Action not supported."
