import asyncio
import time
import tempfile
import os

def sync_write(path, content):
    with open(path, "w") as f:
        f.write(content)

async def measure_blocking_sync(path, content):
    start = time.perf_counter()
    sync_write(path, content)
    return time.perf_counter() - start

async def measure_blocking_async(path, content):
    start = time.perf_counter()
    def write():
        with open(path, "w") as f:
            f.write(content)
    await asyncio.to_thread(write)
    return time.perf_counter() - start

async def main():
    content = "A" * 1024 * 1024 * 50 # 50 MB
    fd, path = tempfile.mkstemp()
    os.close(fd)

    try:
        t_sync = await measure_blocking_sync(path, content)
        print(f"Sync write took {t_sync:.4f}s")

        t_async = await measure_blocking_async(path, content)
        print(f"Async write (to_thread) took {t_async:.4f}s")
    finally:
        os.unlink(path)

asyncio.run(main())
