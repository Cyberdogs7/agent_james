import asyncio
import logging
import random
import subprocess
import threading
import time
from ytmusicapi import YTMusic
import yt_dlp
import imageio_ffmpeg

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
        self.internal_queue = asyncio.Queue(maxsize=2000) # Pre-buffer up to ~5.5 minutes of audio
        self._download_task = None

        # Internal state
        self.volume = 1.0
        self.paused = False
        self.playlist = []
        self.current_track_index = -1
        self._play_task = None

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
        if self.sio:
             await self.sio.emit('music_status', {
                "status": "stopped",
                "track": None
            })
        self.logger.info("MusicAgent stopped.")

    async def _kill_ffmpeg(self):
        if self._download_task:
            self._download_task.cancel()
            self._download_task = None

        # Drain internal queue
        while not self.internal_queue.empty():
            try:
                self.internal_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        # Send EOF to unblock the _stream_reader task
        try:
            self.internal_queue.put_nowait(None)
        except asyncio.QueueFull:
            pass

        if self.ffmpeg_process:
            try:
                self.ffmpeg_process.terminate()
                await asyncio.wait_for(self.ffmpeg_process.wait(), timeout=2.0)
            except:
                try:
                    self.ffmpeg_process.kill()
                except:
                    pass
            self.ffmpeg_process = None

    async def play(self, query):
        """Searches for a query and streams it."""
        self.logger.info(f"Searching for: {query}")
        try:
            # 1. Search
            # Run in thread to avoid blocking
            results = await asyncio.to_thread(self.yt.search, query)
            if not results:
                return f"No results found for {query}"

            top_result = results[0]
            video_id = top_result.get('videoId')
            if not video_id:
                 # Attempt to find a valid videoId in other results
                 for r in results:
                     if r.get('videoId'):
                         top_result = r
                         video_id = r.get('videoId')
                         break

            if not video_id:
                return f"Could not find a playable video for {query}"

            # 2. Get Watch Playlist
            def get_playlist(vid):
                return self.yt.get_watch_playlist(videoId=vid)

            watch_playlist = await asyncio.to_thread(get_playlist, video_id)
            tracks = watch_playlist.get("tracks", [])

            if not tracks:
                 # Fallback to single track
                 tracks = [top_result]

            self.playlist = tracks
            self.current_track_index = 0

            # Start playing first track
            if self._play_task:
                self._play_task.cancel()
            self._play_task = asyncio.create_task(self._play_current_track())

            title = tracks[0].get('title', 'Unknown')
            artists = "Unknown"
            if 'artists' in tracks[0]:
                artists = ", ".join([a['name'] for a in tracks[0]['artists']])
            return f"Playing {title} by {artists}"

        except Exception as e:
            self.logger.error(f"Play failed: {e}")
            return f"Failed to play music: {e}"

    async def _play_current_track(self):
        """Plays the track at self.current_track_index in self.playlist."""
        if not self.playlist or self.current_track_index < 0 or self.current_track_index >= len(self.playlist):
            self.is_playing = False
            return

        track = self.playlist[self.current_track_index]
        video_id = track.get('videoId')
        title = track.get('title', 'Unknown')
        artists = "Unknown"
        if 'artists' in track:
             artists = ", ".join([a['name'] for a in track['artists'] if 'name' in a])

        if not video_id:
            # Skip to next
            self.current_track_index += 1
            await self._play_current_track()
            return

        self.current_track = {
            "title": title,
            "artist": artists,
            "time": "Streaming"
        }
        self.logger.info(f"Playing: {title} by {artists} ({video_id})")

        try:
            # Get Stream URL via yt-dlp
            ydl_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True
            }

            def get_url(vid):
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
                    return info['url'], info.get('duration'), info.get('duration_string')

            stream_url, duration, duration_string = await asyncio.to_thread(get_url, video_id)

            self.current_track['duration'] = duration
            if duration_string:
                self.current_track['time'] = duration_string

            # Start Streaming via FFmpeg
            await self._kill_ffmpeg()

            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
            cmd = [
                ffmpeg_path,
                '-reconnect', '1',
                '-reconnect_streamed', '1',
                '-reconnect_delay_max', '5',
                '-i', stream_url,
                '-f', 's16le',
                '-acodec', 'pcm_s16le',
                '-ac', '1', # Mono
                '-ar', '24000', # Sample Rate
                '-vn', # No video
                '-loglevel', 'quiet',
                '-' # Output to pipe
            ]

            self.ffmpeg_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                limit=1024 * 64
            )

            self.is_playing = True
            self.paused = False

            # Start reading from stdout
            self._download_task = asyncio.create_task(self._ffmpeg_reader())
            asyncio.create_task(self._stream_reader())

            if self.sio:
                await self.sio.emit('music_status', {
                    "status": "playing",
                    "track": self.current_track
                })

            return f"Playing {title} by {artists} (Reminder: Music is now playing. Follow Music Playback Behavior: use GIFs instead of voice for simple responses.)"

        except Exception as e:
            self.logger.error(f"Playback failed for track {video_id}: {e}")
            self.current_track_index += 1
            await asyncio.sleep(1) # Backoff
            asyncio.create_task(self._play_current_track())

    async def _ffmpeg_reader(self):
        """Reads from ffmpeg stdout and pushes to internal queue as fast as possible."""
        chunk_size = 8192
        while self.is_playing and self.ffmpeg_process:
            if self.ffmpeg_process.returncode is not None:
                break

            data = await self.ffmpeg_process.stdout.read(chunk_size)
            if not data:
                break

            await self.internal_queue.put(data)

        # Put None to signal EOF to the playback task
        await self.internal_queue.put(None)

    async def _stream_reader(self):
        """Reads from internal queue and pushes to audio queue at playback speed."""
        start_time = asyncio.get_event_loop().time()
        last_emit_time = start_time

        # For 24kHz, 1 channel, 16-bit PCM: 48000 bytes/sec.
        bytes_per_sec = 24000 * 1 * 2
        total_bytes_played = 0

        while self.is_playing:
            if self.paused:
                await asyncio.sleep(0.1)
                # Adjust start time to account for pause duration
                start_time += 0.1
                last_emit_time += 0.1
                continue

            current_time = asyncio.get_event_loop().time()
            elapsed = current_time - start_time
            self.current_track['progress'] = elapsed

            # Emit progress periodically (e.g., every 1 second)
            if current_time - last_emit_time >= 1.0:
                if self.sio:
                    asyncio.create_task(self.sio.emit('music_status', {
                        "status": "playing",
                        "track": self.current_track
                    }))
                last_emit_time = current_time

            # Read chunk directly from internal cache queue
            data = await self.internal_queue.get()

            if not data:
                self.logger.info("Internal audio queue finished.")
                self.is_playing = False
                break

            # Push to ADA's queue if available
            if self._audio_queue:
                import array
                import sys
                import time

                # Ensure data length is even for 16-bit PCM
                if len(data) % 2 != 0:
                    data = data[:-1]

                arr = array.array('h', data)

                # Apply volume scaling
                if self.volume != 1.0:
                    # Ensure little-endian byte order matches struct behavior
                    if sys.byteorder != 'little':
                        arr.byteswap()

                    vol_int = int(self.volume * 256)
                    for i in range(len(arr)):
                        arr[i] = max(-32768, min(32767, (arr[i] * vol_int) >> 8))

                    if sys.byteorder != 'little':
                        arr.byteswap()

                    data = arr.tobytes()

                # Visualization logic
                if self.sio:
                    try:
                        current_time = time.time()
                        # Rate limit visualizer emission to approx 30 fps (33ms) to avoid flooding the socket
                        if not hasattr(self, '_last_vis_emit') or (current_time - self._last_vis_emit) >= 0.033:
                            self._last_vis_emit = current_time
                            # Extract real amplitude chunks for the visualizer
                            step = max(1, len(arr) // 64)
                            vis_data = []
                            for i in range(64):
                                start_idx = i * step
                                end_idx = min(len(arr), start_idx + step)
                                if start_idx < len(arr):
                                    chunk = arr[start_idx:end_idx]
                                    max_val = max(max(chunk), abs(min(chunk))) if chunk else 0
                                    val = min(255, int((max_val / 32768.0) * 255))
                                else:
                                    val = 0
                                vis_data.append(val)

                            # Async emit to avoid blocking audio loop
                            asyncio.create_task(self.sio.emit('music_vis_data', {"data": vis_data}))
                    except Exception as e:
                        self.logger.debug(f"Vis error: {e}")

                await self._audio_queue.put(data)

            # Manual rate-limiting to simulate real-time playback and handle drift
            total_bytes_played += len(data)
            expected_time = total_bytes_played / bytes_per_sec

            # calculate actual elapsed time
            actual_elapsed = asyncio.get_event_loop().time() - start_time
            sleep_delay = expected_time - actual_elapsed

            if sleep_delay > 0:
                await asyncio.sleep(sleep_delay)

        if not self._stop_event.is_set():
             # Natural end of track, go to next
             self.current_track_index += 1
             asyncio.create_task(self._play_current_track())
        else:
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
            if self.sio:
                await self.sio.emit('music_status', {
                    "status": "playing",
                    "track": self.current_track
                })
            return "Resumed. (Reminder: Music is now playing. Follow Music Playback Behavior: use GIFs instead of voice for simple responses.)"

        elif action == "pause":
            if self.is_playing:
                self.paused = True
                if self.sio:
                    await self.sio.emit('music_status', {
                        "status": "paused",
                        "track": self.current_track
                    })
                return "Paused. (Music is stopped/paused. You may resume normal voice responses.)"
            return "Not playing."

        elif action == "stop":
            await self.stop()
            return "Stopped. (Music is stopped/paused. You may resume normal voice responses.)"

        elif action == "next":
            if not self.playlist:
                return "No playlist loaded."
            self.current_track_index += 1
            self._stop_event.set()
            await self._kill_ffmpeg()
            self._stop_event.clear()
            if self._play_task:
                 self._play_task.cancel()
            self._play_task = asyncio.create_task(self._play_current_track())
            return "Skipped to next track."

        elif action == "previous":
            if not self.playlist:
                return "No playlist loaded."
            self.current_track_index = max(0, self.current_track_index - 1)
            self._stop_event.set()
            await self._kill_ffmpeg()
            self._stop_event.clear()
            if self._play_task:
                 self._play_task.cancel()
            self._play_task = asyncio.create_task(self._play_current_track())
            return "Skipped to previous track."

        elif action == "shuffle":
            if not self.playlist:
                return "No playlist loaded."
            current = self.playlist[self.current_track_index]
            random.shuffle(self.playlist)
            try:
                self.current_track_index = self.playlist.index(current)
            except ValueError:
                self.current_track_index = 0
            return "Playlist shuffled."

        elif action == "volume_up":
            # Software volume scaling on chunks
            self.volume = min(1.0, self.volume + 0.1)
            return f"Volume up to {int(self.volume * 100)}%."

        elif action == "volume_down":
            self.volume = max(0.0, self.volume - 0.1)
            return f"Volume down to {int(self.volume * 100)}%."

        return "Action not supported."
