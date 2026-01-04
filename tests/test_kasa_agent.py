"""
Tests for Kasa Smart Home Agent.
Uses REAL devices from settings.json.
"""
import pytest
import asyncio
from unittest.mock import patch, AsyncMock

# Try to import the agent, skip all tests if dependencies missing
try:
    from backend.kasa_agent import KasaAgent
    HAS_KASA = True
except ImportError as e:
    HAS_KASA = False
    IMPORT_ERROR = str(e)

pytestmark = pytest.mark.skipif(not HAS_KASA, reason=f"Kasa dependencies not installed: {IMPORT_ERROR if not HAS_KASA else ''}")


class TestKasaDiscovery:
    """Tests for device discovery."""
    
    def test_agent_initialization(self, kasa_devices):
        """Test KasaAgent initializes with known devices."""
        agent = KasaAgent(known_devices=kasa_devices)
        assert agent is not None
        assert hasattr(agent, 'devices')
        print(f"KasaAgent initialized with {len(kasa_devices)} known devices")
    
    @pytest.mark.asyncio
    @patch('backend.kasa_agent.Discover.discover_single', new_callable=AsyncMock)
    async def test_initialize_known_devices(self, mock_discover, kasa_devices):
        """Test initializing devices from settings."""
        # Configure the mock to return a mock device
        mock_device = AsyncMock()
        mock_device.alias = "Mock Device"
        mock_discover.return_value = mock_device

        agent = KasaAgent(known_devices=kasa_devices)
        await agent.initialize()
        print(f"Initialized {len(agent.devices)} devices")
        
        # If we have known devices, they should be loaded
        if kasa_devices:
            assert len(agent.devices) > 0

    @pytest.mark.asyncio
    async def test_discover_devices(self):
        """Test discovering devices on network."""
        agent = KasaAgent()
        # This will still try a real discovery, which might be slow but shouldn't fail CI
        # If it becomes a problem, this also needs mocking.
        devices = await agent.discover_devices()
        
        print(f"Discovered {len(devices)} devices:")
        for device in devices:
            print(f"  - {device.get('alias', 'unknown')} @ {device.get('ip', 'unknown')}")
        
        # Discovery should return a list (may be empty if no devices)
        assert isinstance(devices, list)


class TestKasaDeviceControl:
    """Tests for device control - only runs if devices exist."""
    
    @pytest.fixture
    async def agent_with_devices(self, kasa_devices):
        """Get an initialized agent with devices."""
        with patch('backend.kasa_agent.Discover.discover_single', new_callable=AsyncMock) as mock_discover:
            mock_device = AsyncMock()
            # Set default attributes for the mock device
            mock_device.alias = "Mock Bulb"
            mock_device.is_on = False
            mock_device.is_bulb = True
            mock_device.is_dimmable = True
            mock_device.is_color = True
            mock_discover.return_value = mock_device

            agent = KasaAgent(known_devices=kasa_devices)
            await agent.initialize()
            # Attach the mock to the agent for inspection in tests if needed
            agent.mock_discover = mock_discover
            agent.mock_device = mock_device
            yield agent

    @pytest.mark.asyncio
    async def test_get_device_by_alias(self, agent_with_devices, kasa_devices):
        """Test finding device by alias."""
        agent = agent_with_devices
        
        if not kasa_devices:
            pytest.skip("No Kasa devices configured")
        
        first_device_info = next(iter(kasa_devices.values()))
        alias = first_device_info.get('alias')

        # We need to configure the mock's alias to match what we're looking for
        agent.mock_device.alias = alias

        device = agent.get_device_by_alias(alias)
        assert device is not None
        assert device.alias == alias
        print(f"Found device by alias '{alias}': {device}")
    
    @pytest.mark.asyncio  
    async def test_turn_on_device(self, agent_with_devices, kasa_devices):
        """Test turning on a device."""
        agent = agent_with_devices
        
        if not kasa_devices:
            pytest.skip("No Kasa devices configured")
        
        ip = next(iter(kasa_devices.keys()))
        result = await agent.turn_on(ip)
        
        agent.mock_device.turn_on.assert_called_once()
        print(f"Turn on result for {ip}: {result}")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_turn_off_device(self, agent_with_devices, kasa_devices):
        """Test turning off a device."""
        agent = agent_with_devices
        
        if not kasa_devices:
            pytest.skip("No Kasa devices configured")
        
        ip = next(iter(kasa_devices.keys()))
        result = await agent.turn_off(ip)
        
        agent.mock_device.turn_off.assert_called_once()
        print(f"Turn off result for {ip}: {result}")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_set_brightness(self, agent_with_devices, kasa_devices):
        """Test setting brightness."""
        agent = agent_with_devices
        
        if not kasa_devices:
            pytest.skip("No Kasa devices configured")

        ip = next(iter(kasa_devices.keys()))
        result = await agent.set_brightness(ip, 50)

        agent.mock_device.set_brightness.assert_called_once_with(50)
        print(f"Set brightness result for {ip}: {result}")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_set_color(self, agent_with_devices, kasa_devices):
        """Test setting color."""
        agent = agent_with_devices
        
        if not kasa_devices:
            pytest.skip("No Kasa devices configured")
        
        ip = next(iter(kasa_devices.keys()))
        result = await agent.set_color(ip, "blue")
        
        # hsv for blue is (240, 100, 100)
        agent.mock_device.set_hsv.assert_called_once_with(240, 100, 100)
        print(f"Set color result for {ip}: {result}")
        assert result is True


class TestKasaColorConversion:
    """Test color name to HSV conversion."""
    
    def test_name_to_hsv_red(self):
        """Test red color conversion."""
        agent = KasaAgent()
        hsv = agent.name_to_hsv("red")
        assert hsv is not None
        assert hsv[0] == 0  # Hue for red
    
    def test_name_to_hsv_blue(self):
        """Test blue color conversion."""
        agent = KasaAgent()
        hsv = agent.name_to_hsv("blue")
        assert hsv is not None
        assert hsv[0] == 240  # Hue for blue
    
    def test_name_to_hsv_unknown(self):
        """Test unknown color returns None."""
        agent = KasaAgent()
        hsv = agent.name_to_hsv("notacolor")
        assert hsv is None
