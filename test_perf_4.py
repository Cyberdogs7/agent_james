import asyncio
import time
import os
import shutil
import tempfile
import aiofiles

async def test_full_flow():
    temp_dir = tempfile.mkdtemp()

    # 1. To_thread (old)
    def _write_script_old(path, code):
        with open(path, "w") as f:
            f.write(code)

    async def run_old_write():
        path = os.path.join(temp_dir, "script1.py")
        code = "print('hello')" * 1000
        start = time.perf_counter()
        for _ in range(100):
            batch = [asyncio.to_thread(_write_script_old, path, code) for _ in range(10)]
            await asyncio.gather(*batch)
        return time.perf_counter() - start

    # 2. Aiofiles (new)
    async def _write_script_new(path, code):
        async with aiofiles.open(path, "w") as f:
            await f.write(code)

    async def run_new_write():
        path = os.path.join(temp_dir, "script2.py")
        code = "print('hello')" * 1000
        start = time.perf_counter()
        for _ in range(100):
            batch = [asyncio.create_task(_write_script_new(path, code)) for _ in range(10)]
            await asyncio.gather(*batch)
        return time.perf_counter() - start

    t1 = await run_old_write()
    t2 = await run_new_write()
    print(f"Write old: {t1:.4f}s, Write new: {t2:.4f}s")

    shutil.rmtree(temp_dir)

if __name__ == "__main__":
    asyncio.run(test_full_flow())
