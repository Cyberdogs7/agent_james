import pytest
import os
import asyncio
from unittest.mock import MagicMock, patch, sys

# Mock dependencies before importing PrinterAgent
sys.modules['aiohttp'] = MagicMock()
sys.modules['zeroconf'] = MagicMock()

from backend.printer_agent import PrinterAgent

def test_orcaslicer_output_dir_dot():
    """Test that OrcaSlicer uses '.' for --outputdir when output_path has no directory prefix."""
    agent = PrinterAgent()
    # Force slicer_path to be OrcaSlicer
    agent.slicer_path = "/path/to/OrcaSlicer"

    # Mock os.path.exists to return True for the stl file
    with patch("os.path.exists", return_value=True):
        # Mock subprocess.run to avoid actually calling a slicer
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            # Use asyncio.run to call the async method
            asyncio.run(agent.slice_stl("test.stl"))

            # Verify the command
            args, kwargs = mock_run.call_args
            cmd = args[0]

            assert "--outputdir" in cmd
            idx = cmd.index("--outputdir")
            assert cmd[idx + 1] == "."

def test_orcaslicer_output_dir_with_path():
    """Test that OrcaSlicer uses the correct directory for --outputdir when output_path has a directory prefix."""
    agent = PrinterAgent()
    agent.slicer_path = "/path/to/OrcaSlicer"

    with patch("os.path.exists", return_value=True):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            # Use asyncio.run to call the async method
            asyncio.run(agent.slice_stl("models/test.stl", output_path="output/test.gcode"))

            # Verify the command
            args, kwargs = mock_run.call_args
            cmd = args[0]

            assert "--outputdir" in cmd
            idx = cmd.index("--outputdir")
            assert cmd[idx + 1] == "output"
