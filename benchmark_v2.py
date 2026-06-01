import asyncio
import time
import os
import shutil
import tempfile
from unittest.mock import AsyncMock, patch, MagicMock

# Mock out genai so we don't need real API keys
os.environ["GEMINI_API_KEY"] = "dummy"

from backend.cad_agent import CadAgent

async def run_benchmark():
    # Setup dummy temp file
    temp_dir = tempfile.mkdtemp()
    script_path = os.path.join(temp_dir, "current_design.py")

    # Let's create a slightly larger file to simulate real python code
    dummy_code = "import build123d\n" + "x = 1\n" * 1000 + "export_stl(result_part, 'C:\\\\Users\\\\Bob\\\\output.stl')\n"
    with open(script_path, "w") as f:
        f.write(dummy_code)

    agent = CadAgent()
    agent.generate_prototype = AsyncMock() # fallback mock

    # Measure event loop blocking
    start = time.perf_counter()

    with patch.object(agent, '_run_cad_generation', new_callable=AsyncMock) as mock_run:
        mock_run.return_value = {"format": "stl", "data": "dummy"}

        # Run many iterations concurrently
        tasks = []
        for _ in range(2000):
            tasks.append(agent.iterate_prototype("Make it bigger", output_dir=temp_dir))

        await asyncio.gather(*tasks)

    duration = time.perf_counter() - start
    print(f"Time taken for 2000 iterations (setup phase): {duration:.4f} seconds")

    shutil.rmtree(temp_dir)

if __name__ == "__main__":
    asyncio.run(run_benchmark())
