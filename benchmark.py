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
    with open(script_path, "w") as f:
        f.write("import build123d\n# some dummy code\nexport_stl(result_part, 'output.stl')\n")

    agent = CadAgent()

    # We just want to measure iterate_prototype up to the point it runs the model,
    # or we can patch _run_cad_generation to return quickly.
    with patch.object(agent, '_run_cad_generation', new_callable=AsyncMock) as mock_run:
        mock_run.return_value = {"format": "stl", "data": "dummy"}

        start = time.perf_counter()

        # Run many iterations concurrently
        tasks = []
        for _ in range(1000):
            tasks.append(agent.iterate_prototype("Make it bigger", output_dir=temp_dir))

        await asyncio.gather(*tasks)

        duration = time.perf_counter() - start
        print(f"Time taken for 1000 iterations (setup phase): {duration:.4f} seconds")

    shutil.rmtree(temp_dir)

if __name__ == "__main__":
    asyncio.run(run_benchmark())
