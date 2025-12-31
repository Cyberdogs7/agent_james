"""
Tests for Printer Agent.
"""
import pytest
import asyncio
import os
import shutil
from unittest.mock import AsyncMock, patch

# Try to import the agent, skip all tests if dependencies missing
try:
    from printer_agent import PrinterAgent, Printer
    HAS_PRINTER_AGENT = True
except ImportError as e:
    HAS_PRINTER_AGENT = False
    IMPORT_ERROR = str(e)

pytestmark = pytest.mark.skipif(not HAS_PRINTER_AGENT, reason=f"PrinterAgent dependencies not installed: {IMPORT_ERROR if not HAS_PRINTER_AGENT else ''}")


@pytest.fixture
def printer_agent():
    """Fixture to create a PrinterAgent instance for testing."""
    return PrinterAgent()


class TestPrinterDiscovery:
    """Tests for device discovery."""

    @pytest.mark.anyio
    async def test_discover_printers(self, printer_agent):
        """Test discovering printers on network."""
        with patch("printer_agent.Zeroconf", new_callable=AsyncMock) as mock_zeroconf:
            printers = await printer_agent.discover_printers(timeout=0.1)
            assert isinstance(printers, list)


class TestPrinterWithSettings:
    """Tests for printers loaded from settings."""

    @pytest.fixture
    def agent_with_printers(self, printer_devices):
        """Get an agent with pre-loaded printers."""
        agent = PrinterAgent()
        for p in printer_devices:
            agent.add_printer_manually(**p)
        return agent

    def test_load_printers_from_settings(self, agent_with_printers, printer_devices):
        """Test printers are loaded from settings."""
        assert len(agent_with_printers.printers) == len(printer_devices)

    def test_resolve_printer_by_name(self, agent_with_printers, printer_devices):
        """Test resolving a printer by its name."""
        if not printer_devices:
            pytest.skip("No printers configured")
        
        name = printer_devices[0]["name"]
        printer = agent_with_printers._resolve_printer(name)
        assert printer is not None
        assert printer.name == name

    def test_resolve_printer_by_host(self, agent_with_printers, printer_devices):
        """Test resolving a printer by its host IP."""
        if not printer_devices:
            pytest.skip("No printers configured")
        
        host = printer_devices[0]["host"]
        printer = agent_with_printers._resolve_printer(host)
        assert printer is not None
        assert printer.host == host


class TestPrinterStatus:
    """Tests for getting printer status."""

    @pytest.mark.anyio
    async def test_get_print_status(self, printer_agent):
        """Test getting print status."""
        # This test is more of a placeholder as it requires a live device.
        # We can mock the underlying API calls in more advanced tests.
        pass


class TestSlicerProfiles:
    """Tests for slicer profile detection."""
    
    def test_find_matching_profile(self, printer_agent):
        """Test finding a matching slicer profile."""
        # This test depends on having OrcaSlicer/PrusaSlicer installed
        # with default profiles.
        if not printer_agent._orca_profiles_dir:
            pytest.skip("OrcaSlicer profiles not found")

        profiles = printer_agent.get_profiles_for_printer("Creality K1")
        assert profiles["machine"] is not None


class TestSlicing:
    """Tests for STL slicing."""

    @pytest.mark.anyio
    @pytest.mark.skipif(
        not shutil.which("orca-slicer") and not shutil.which("prusa-slicer"),
        reason="No slicer executable found in PATH"
    )
    async def test_slice_stl_file(self, printer_agent):
        """Test slicing an STL file."""
        # Create a dummy STL file
        dummy_stl_path = "dummy.stl"
        with open(dummy_stl_path, "w") as f:
            f.write("solid dummy\nendsolid dummy\n")

        gcode_path = await printer_agent.slice_stl(dummy_stl_path, printer_name="Creality K1")
        
        assert gcode_path is not None
        assert os.path.exists(gcode_path)
        
        # Cleanup
        os.remove(dummy_stl_path)
        os.remove(gcode_path)
