import asyncio
import time
import os
import shutil
import tempfile
import aiofiles
import aiofiles.ospath

async def _read_and_sanitize_aio(path: str) -> str:
    if not await aiofiles.ospath.exists(path):
        return ""
    async with aiofiles.open(path, "r") as f:
        code = await f.read()
    # Sanitize existing code: replace any absolute paths with 'output.stl'
    import re

    # Actually, the problem mentioned in memory is that CPU bound should use to_thread.
    # aiofiles.open and aiofiles.ospath.exists are standard.
    # Let's read it here, and maybe we can do the re.sub locally.

    # Let's offload re.sub to thread
    def cpu_bound(c):
        import re
        c = re.sub(
            r"['\"]C:\\\\?Users\\\\?[^'\"]+\\\\?output[^'\"]*\.stl['\"]",
            "'output.stl'",
            c
        )
        c = re.sub(
            r"['\"]C:/Users/[^'\"]+/output[^'\"]*\.stl['\"]",
            "'output.stl'",
            c
        )
        return c

    code = await asyncio.to_thread(cpu_bound, code)
    return code

async def benchmark_aio():
    temp_dir = tempfile.mkdtemp()
    script_path = os.path.join(temp_dir, "current_design.py")

    dummy_code = "import build123d\n" + "x = 1\n" * 1000 + "export_stl(result_part, 'C:\\\\Users\\\\Bob\\\\output.stl')\n"
    with open(script_path, "w") as f:
        f.write(dummy_code)

    start = time.perf_counter()
    tasks = []
    for _ in range(2000):
        tasks.append(_read_and_sanitize_aio(script_path))

    await asyncio.gather(*tasks)
    duration = time.perf_counter() - start
    print(f"Aiofiles version: {duration:.4f} seconds")
    shutil.rmtree(temp_dir)

if __name__ == "__main__":
    asyncio.run(benchmark_aio())
