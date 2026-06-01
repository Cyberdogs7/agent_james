import asyncio
import time
import os
import shutil
import tempfile
import aiofiles
import aiofiles.ospath
import base64

def _read_output_stl_old(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode('utf-8')
    return None

async def _read_output_stl_new(path):
    if await aiofiles.ospath.exists(path):
        async with aiofiles.open(path, "rb") as f:
            data = await f.read()
        # cpu bound
        def _encode(d):
            import base64
            return base64.b64encode(d).decode('utf-8')
        return await asyncio.to_thread(_encode, data)
    return None

async def bench():
    temp_dir = tempfile.mkdtemp()
    script_path = os.path.join(temp_dir, "output.stl")

    with open(script_path, "wb") as f:
        f.write(b"0" * 1024 * 1024) # 1MB file

    start = time.perf_counter()
    for _ in range(10):
        batch = [asyncio.to_thread(_read_output_stl_old, script_path) for _ in range(100)]
        await asyncio.gather(*batch)
    print(f"Old sync version: {time.perf_counter() - start:.4f}s")

    start = time.perf_counter()
    for _ in range(10):
        batch = [asyncio.create_task(_read_output_stl_new(script_path)) for _ in range(100)]
        await asyncio.gather(*batch)
    print(f"New aiofiles version: {time.perf_counter() - start:.4f}s")

    shutil.rmtree(temp_dir)

if __name__ == "__main__":
    asyncio.run(bench())
