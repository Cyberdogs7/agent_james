import queue
import asyncio

q = queue.Queue()
try:
    q.get_nowait()
except asyncio.QueueEmpty:
    print("Caught asyncio.QueueEmpty")
except Exception as e:
    print("Caught Exception:", type(e))
