import asyncio
import time
import os
import shutil
import tempfile
import aiofiles
import aiofiles.ospath
import aiofiles.os
import base64

async def read_and_sanitize_aio(path: str) -> str:
    if not await aiofiles.ospath.exists(path):
        return ""
    async with aiofiles.open(path, "r") as f:
        code = await f.read()
    # Sanitize existing code: replace any absolute paths with 'output.stl'
    import re
    code = re.sub(
        r"['\"]C:\\\\?Users\\\\?[^'\"]+\\\\?output[^'\"]*\.stl['\"]",
        "'output.stl'",
        code
    )
    code = re.sub(
        r"['\"]C:/Users/[^'\"]+/output[^'\"]*\.stl['\"]",
        "'output.stl'",
        code
    )
    return code

def _read_and_sanitize_sync(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r") as f:
        code = f.read()
    import re
    code = re.sub(
        r"['\"]C:\\\\?Users\\\\?[^'\"]+\\\\?output[^'\"]*\.stl['\"]",
        "'output.stl'",
        code
    )
    code = re.sub(
        r"['\"]C:/Users/[^'\"]+/output[^'\"]*\.stl['\"]",
        "'output.stl'",
        code
    )
    return code

async def read_and_sanitize_sync_wrapper(path: str) -> str:
    return await asyncio.to_thread(_read_and_sanitize_sync, path)

async def test_performance():
    temp_dir = tempfile.mkdtemp()
    script_path = os.path.join(temp_dir, "current_design.py")

    dummy_code = "import build123d\n" + "x = 1\n" * 1000 + "export_stl(result_part, 'C:\\\\Users\\\\Bob\\\\output.stl')\n"
    with open(script_path, "w") as f:
        f.write(dummy_code)

    # We test concurrency of 100 tasks, run 10 times
    async def run_aio():
        start = time.perf_counter()
        for _ in range(10):
            batch = [asyncio.create_task(read_and_sanitize_aio(script_path)) for _ in range(100)]
            await asyncio.gather(*batch)
        return time.perf_counter() - start

    async def run_sync():
        start = time.perf_counter()
        for _ in range(10):
            batch = [asyncio.create_task(read_and_sanitize_sync_wrapper(script_path)) for _ in range(100)]
            await asyncio.gather(*batch)
        return time.perf_counter() - start

    t_sync = await run_sync()
    t_aio = await run_aio()

    print(f"Sync version (ThreadPool): {t_sync:.4f}s")
    print(f"Aiofiles version: {t_aio:.4f}s")
    shutil.rmtree(temp_dir)

if __name__ == "__main__":
    asyncio.run(test_performance())
