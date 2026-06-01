import asyncio
import time
import os
import shutil
import tempfile

def _read_and_sanitize(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r") as f:
        code = f.read()
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

async def wrapper(path):
    return await asyncio.to_thread(_read_and_sanitize, path)

async def benchmark_old():
    temp_dir = tempfile.mkdtemp()
    script_path = os.path.join(temp_dir, "current_design.py")

    dummy_code = "import build123d\n" + "x = 1\n" * 1000 + "export_stl(result_part, 'C:\\\\Users\\\\Bob\\\\output.stl')\n"
    with open(script_path, "w") as f:
        f.write(dummy_code)

    start = time.perf_counter()
    tasks = []

    for _ in range(200):
        batch = [asyncio.create_task(wrapper(script_path)) for _ in range(10)]
        await asyncio.gather(*batch)

    duration = time.perf_counter() - start
    print(f"Old version: {duration:.4f} seconds")
    shutil.rmtree(temp_dir)

if __name__ == "__main__":
    asyncio.run(benchmark_old())
