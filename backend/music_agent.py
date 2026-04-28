import asyncio
import queue
import time
import threading
import logging
import random
import subprocess
import shutil
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
        self._stop_event = threading.Event()
        self.main_loop = None
        self._audio_queue = None # Set by ada.py if pushing to global mix
        self.internal_queue = queue.Queue(maxsize=2000) # Pre-buffer up to ~5.5 minutes of audio
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
        self.main_loop = asyncio.get_running_loop()
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
            except queue.Empty:
                break

        # Drain audio queue to immediately stop playback
        if self._audio_queue:
            while not self._audio_queue.empty():
                try:
                    self._audio_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

        # Send EOF to unblock the _stream_reader task
        try:
            self.internal_queue.put_nowait(None)
        except queue.Full:
            pass

        # Immediately replace the queue so new streams start fresh
        self.internal_queue = queue.Queue(maxsize=2000)

        if self.ffmpeg_process:
            try:
                self.ffmpeg_process.terminate()
                self.ffmpeg_process.wait(timeout=2.0)
            except Exception:
                try:
                    self.ffmpeg_process.kill()
                    self.ffmpeg_process.wait(timeout=2.0)
                except Exception:
                    pass
            self.ffmpeg_process = None

    async def play(self, query):
        """Searches for a query and streams it."""
        self.logger.info(f"Searching for: {query}")
        try:
            # 1. Search
            # We first search with no filter. If no playlist/album is explicitly requested, we just use top result.
            # However, if query explicitly mentions 'playlist' or 'album', we can try to filter search.
            is_playlist_query = "playlist" in query.lower()
            is_album_query = "album" in query.lower()

            filter_type = None
            if is_playlist_query:
                filter_type = "playlists"
            elif is_album_query:
                filter_type = "albums"

            if filter_type:
                 results = await asyncio.to_thread(self.yt.search, query, filter=filter_type)
                 # Fallback if no results with filter
                 if not results:
                     results = await asyncio.to_thread(self.yt.search, query)
            else:
                 results = await asyncio.to_thread(self.yt.search, query)

            if not results:
                return f"No results found for {query}"

            top_result = results[0]

            # Use fallback for artist types as they are not playable directly like a playlist or video
            if filter_type is None and top_result.get('resultType') == 'artist':
                # Attempt to find a valid videoId in other results
                for r in results:
                    if r.get('videoId') or r.get('resultType') in ['playlist', 'album']:
                        top_result = r
                        break

            # Check if it's a playlist or album
            result_type = top_result.get('resultType')
            if result_type in ['playlist', 'album']:
                browse_id = top_result.get('browseId')
                if browse_id:
                    if browse_id.startswith('VL'):
                        browse_id = browse_id[2:]

                    self.logger.info(f"Extracting playlist/album with browseId: {browse_id}")

                    def get_playlist_tracks(bid):
                        ydl_opts = {
                            'extract_flat': True,
                            'quiet': True,
                            'ignoreerrors': True,
                        }
                        tracks = []
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            url = f"https://www.youtube.com/playlist?list={bid}"
                            info = ydl.extract_info(url, download=False)
                            if info and 'entries' in info:
                                for entry in info['entries']:
                                    if entry and entry.get('id'):
                                        tracks.append({
                                            'videoId': entry.get('id'),
                                            'title': entry.get('title', 'Unknown Title'),
                                            'artists': [{'name': entry.get('channel', 'Unknown Artist')}],
                                            'duration_seconds': entry.get('duration', 0)
                                        })
                        return tracks

                    tracks = await asyncio.to_thread(get_playlist_tracks, browse_id)
                    if not tracks:
                        return f"Could not extract tracks from {result_type} '{query}'"

            else:
                # Standard video logic
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
            if 'artists' in tracks[0] and tracks[0]['artists']:
                artists = ", ".join([a['name'] for a in tracks[0]['artists']])
            return f"Playing {title} by {artists}"

        except Exception as e:
            self.logger.error(f"Play failed: {e}")
            return f"Failed to play music: {e}"


    async def create_playlist(self, name, queries):
        """Creates a playlist from a list of queries and starts playing it."""
        self.logger.info(f"Creating playlist '{name}' with queries: {queries}")

        if not queries:
            return "No queries provided for the playlist."

        tracks = []

        for query in queries:
            try:
                results = await asyncio.to_thread(self.yt.search, query)
                if results:
                    top_result = results[0]

                    # Handle if the top result is an artist - fallback to a playable track
                    if top_result.get('resultType') == 'artist':
                        for r in results:
                            if r.get('videoId'):
                                top_result = r
                                break

                    video_id = top_result.get('videoId')
                    if video_id:
                        # We just need the basic track info, we won't fetch the full watch playlist for every track
                        tracks.append(top_result)
                    else:
                        self.logger.warning(f"Could not find playable video ID for query: {query}")
                else:
                    self.logger.warning(f"No results found for query: {query}")
            except Exception as e:
                self.logger.error(f"Error searching for '{query}': {e}")

        if not tracks:
            return f"Failed to find any playable tracks for the playlist '{name}'."

        self.playlist = tracks
        self.current_track_index = 0

        # Start playing first track
        if self._play_task:
            self._play_task.cancel()
        self._play_task = asyncio.create_task(self._play_current_track())

        return f"Created playlist '{name}' with {len(tracks)} tracks and started playing."

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

            # Fetch lyrics
            try:
                watch = await asyncio.to_thread(self.yt.get_watch_playlist, videoId=video_id)
                lyrics_id = watch.get("lyrics")
                if lyrics_id:
                    lyrics_data = await asyncio.to_thread(self.yt.get_lyrics, lyrics_id)
                    if lyrics_data and 'lyrics' in lyrics_data:
                        self.current_track['lyrics'] = lyrics_data['lyrics']
                    else:
                        self.current_track['lyrics'] = None
                else:
                    self.current_track['lyrics'] = None
            except Exception as e:
                self.logger.error(f"Failed to fetch lyrics: {e}")
                self.current_track['lyrics'] = None

            # Start Streaming via FFmpeg
            await self._kill_ffmpeg()

            try:
                import imageio_ffmpeg
                ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
            except ImportError:
                ffmpeg_path = shutil.which("ffmpeg")

            if not ffmpeg_path:
                raise Exception("ffmpeg is not installed on the system.")

            cmd = [
                ffmpeg_path,
                '-reconnect', '1',
                '-reconnect_streamed', '1',
                '-reconnect_delay_max', '5',
                '-rw_timeout', '10000000', # 10 seconds in microseconds to prevent indefinite hangs
                '-user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36', # Masquerade as a browser
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
                stderr=subprocess.DEVNULL
            )

            self.is_playing = True
            self.paused = False

            # Start reading from stdout
            threading.Thread(target=self._ffmpeg_reader_sync, daemon=True).start()
            threading.Thread(target=self._stream_reader_sync, daemon=True).start()

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

    def _ffmpeg_reader_sync(self):
        """Reads from ffmpeg stdout and pushes to internal queue as fast as possible."""
        chunk_size = 131072
        while self.is_playing and self.ffmpeg_process:
            if self.ffmpeg_process.poll() is not None:
                break

            data = self.ffmpeg_process.stdout.read(chunk_size)
            if not data:
                break

            self.internal_queue.put(data)

        # Put None to signal EOF to the playback task
        self.internal_queue.put(None)

    def _stream_reader_sync(self):
        """Reads from internal queue and pushes to audio queue at playback speed."""
        start_time = time.time()
        last_emit_time = start_time

        # For 24kHz, 1 channel, 16-bit PCM: 48000 bytes/sec.
        bytes_per_sec = 24000 * 1 * 2
        total_bytes_played = 0

        # Buffer for smaller chunks
        small_chunk_buffer = b""
        SMALL_CHUNK_SIZE = 4096

        while self.is_playing:
            if self.paused:
                time.sleep(0.1)
                # Adjust start time to account for pause duration
                start_time += 0.1
                last_emit_time += 0.1
                continue

            current_time = time.time()
            elapsed = current_time - start_time
            self.current_track['progress'] = elapsed

            # Emit progress periodically (e.g., every 1 second)
            if current_time - last_emit_time >= 1.0:
                if self.sio and self.main_loop:
                    asyncio.run_coroutine_threadsafe(
                        self.sio.emit('music_status', {
                            "status": "playing",
                            "track": self.current_track
                        }),
                        self.main_loop
                    )
                last_emit_time = current_time

            if len(small_chunk_buffer) < SMALL_CHUNK_SIZE:
                # Read chunk directly from internal cache queue
                data = self.internal_queue.get()

                if not data:
                    self.logger.info("Internal audio queue finished.")
                    self.is_playing = False
                    break

                small_chunk_buffer += data

            if len(small_chunk_buffer) >= SMALL_CHUNK_SIZE:
                process_data = small_chunk_buffer[:SMALL_CHUNK_SIZE]
                small_chunk_buffer = small_chunk_buffer[SMALL_CHUNK_SIZE:]
            else:
                process_data = small_chunk_buffer
                small_chunk_buffer = b""

            # Push to ADA's queue if available
            if self._audio_queue:
                import array
                import sys
                import audioop

                # Ensure data length is even for 16-bit PCM
                if len(process_data) % 2 != 0:
                    process_data = process_data[:-1]

                # Apply volume scaling
                if self.volume != 1.0:
                    process_data = audioop.mul(process_data, 2, self.volume)

                arr = array.array('h', process_data)

                # Visualization logic
                if self.sio and self.main_loop:
                    try:
                        current_time = time.time()
                        # Rate limit visualizer emission to approx 15 fps (66ms) to avoid flooding the socket
                        if not hasattr(self, '_last_vis_emit') or (current_time - self._last_vis_emit) >= 0.066:
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
                            async def safe_emit():
                                try:
                                    await self.sio.emit('music_vis_data', {"data": vis_data})
                                except Exception as emit_err:
                                    self.logger.debug(f"Emit error: {emit_err}")

                            asyncio.run_coroutine_threadsafe(safe_emit(), self.main_loop)
                    except Exception as e:
                        self.logger.debug(f"Vis error: {e}")

                try:
                    self._audio_queue.put_nowait(process_data)
                except queue.Full:
                    pass

            # Manual rate-limiting to simulate real-time playback and handle drift
            total_bytes_played += len(process_data)
            expected_time = total_bytes_played / bytes_per_sec

            # calculate actual elapsed time
            actual_elapsed = time.time() - start_time
            sleep_delay = expected_time - actual_elapsed

            if sleep_delay > 0:
                time.sleep(sleep_delay)

        if not self._stop_event.is_set():
             # Natural end of track, go to next
             self.current_track_index += 1
             if self.main_loop:
                 asyncio.run_coroutine_threadsafe(self._play_current_track(), self.main_loop)
        else:
             self.is_playing = False
             if self.sio and self.main_loop:
                 asyncio.run_coroutine_threadsafe(self.sio.emit('music_status', {
                    "status": "stopped",
                    "track": None
                }), self.main_loop)

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
