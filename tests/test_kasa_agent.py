"""
Tests for Kasa Smart Home Agent.
Uses REAL devices from settings.json.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# Try to import the agent, skip all tests if dependencies missing
try:
    from kasa_agent import KasaAgent
    HAS_KASA = True
except ImportError as e:
    HAS_KASA = False
    IMPORT_ERROR = str(e)

pytestmark = pytest.mark.skipif(not HAS_KASA, reason=f"Kasa dependencies not installed: {IMPORT_ERROR if not HAS_KASA else ''}")


@pytest.fixture
def mock_kasa_device():
    """Fixture to create a mock Kasa device."""
    mock_device = AsyncMock()
    mock_device.alias = "Living Room Lamp"
    mock_device.host = "192.168.1.100"
    mock_device.is_on = False
    mock_device.is_dimmable = True
    mock_device.is_color = True
    mock_device.brightness = 50
    mock_device.hsv = (0, 100, 100)
    return mock_device


class TestKasaDiscovery:
    """Tests for device discovery."""
    
    def test_agent_initialization(self, kasa_devices):
        """Test KasaAgent initializes with known devices."""
        agent = KasaAgent(known_devices=kasa_devices)
        assert agent is not None
        assert hasattr(agent, 'devices')
        print(f"KasaAgent initialized with {len(kasa_devices)} known devices")
    
    @pytest.mark.anyio
    async def test_initialize_known_devices(self, kasa_devices, mock_kasa_device):
        """Test initializing devices from settings."""
        with patch("kasa.Discover.discover_single", return_value=mock_kasa_device):
            agent = KasaAgent(known_devices=kasa_devices)
            await agent.initialize()
            print(f"Initialized {len(agent.devices)} devices")

            # If we have known devices, they should be loaded
            if kasa_devices:
                assert len(agent.devices) > 0
    
    @pytest.mark.anyio
    async def test_discover_devices(self, mock_kasa_device):
        """Test discovering devices on network."""
        with patch("kasa.Discover.discover", return_value={"192.168.1.100": mock_kasa_device}):
            agent = KasaAgent()
            devices = await agent.discover_devices()

            print(f"Discovered {len(devices)} devices:")
            for device in devices:
                print(f"  - {device.get('alias', 'unknown')} @ {device.get('ip', 'unknown')}")

            # Discovery should return a list (may be empty if no devices)
            assert isinstance(devices, list)


class TestKasaDeviceControl:
    """Tests for device control - only runs if devices exist."""
    
    @pytest.fixture
    async def agent_with_devices(self, kasa_devices, mock_kasa_device):
        """Get an initialized agent with devices."""
        with patch("kasa.Discover.discover_single", return_value=mock_kasa_device):
            agent = KasaAgent(known_devices=kasa_devices)
            await agent.initialize()
            return agent
    
    @pytest.mark.anyio
    async def test_get_device_by_alias(self, agent_with_devices, kasa_devices):
        """Test finding device by alias."""
        agent = agent_with_devices
        
        if not kasa_devices:
            pytest.skip("No Kasa devices configured in settings.json")
        
        # Try to find first configured device by alias
        device_config = kasa_devices[0]
        if not device_config:
             pytest.skip("Invalid device config (None)")

        alias = device_config.get('alias')
        if alias:
            device = agent.get_device_by_alias(alias)
            print(f"Found device by alias '{alias}': {device}")
    
    @pytest.mark.anyio
    async def test_turn_on_device(self, agent_with_devices, kasa_devices):
        """Test turning on a device."""
        agent = agent_with_devices
        
        if not kasa_devices:
            pytest.skip("No Kasa devices configured")
        
        if not kasa_devices:
            pytest.skip("No Kasa devices configured")
        
        device_config = kasa_devices[0]
        if not device_config:
             pytest.skip("Invalid device config")

        ip = device_config.get('ip')
        if ip:
            result = await agent.turn_on(ip)
            print(f"Turn on result for {ip}: {result}")
            assert result is True
    
    @pytest.mark.anyio
    async def test_turn_off_device(self, agent_with_devices, kasa_devices):
        """Test turning off a device."""
        agent = agent_with_devices
        
        if not kasa_devices:
            pytest.skip("No Kasa devices configured")
        
        if not kasa_devices:
            pytest.skip("No Kasa devices configured")
        
        device_config = kasa_devices[0]
        if not device_config:
             pytest.skip("Invalid device config")

        ip = device_config.get('ip')
        if ip:
            result = await agent.turn_off(ip)
            print(f"Turn off result for {ip}: {result}")
            assert result is True
    
    @pytest.mark.anyio
    async def test_set_brightness(self, agent_with_devices, kasa_devices):
        """Test setting brightness."""
        agent = agent_with_devices
        
        if not kasa_devices:
            pytest.skip("No Kasa devices configured")
        
        if not kasa_devices:
            pytest.skip("No Kasa devices configured")
        
        device_config = kasa_devices[0]
        if not device_config:
             pytest.skip("Invalid device config")

        ip = device_config.get('ip')
        if ip:
            result = await agent.set_brightness(ip, 50)
            print(f"Set brightness result for {ip}: {result}")
            assert result is True
    
    @pytest.mark.anyio
    async def test_set_color(self, agent_with_devices, kasa_devices):
        """Test setting color."""
        agent = agent_with_devices
        
        if not kasa_devices:
            pytest.skip("No Kasa devices configured")
        
        if not kasa_devices:
            pytest.skip("No Kasa devices configured")
        
        device_config = kasa_devices[0]
        if not device_config:
             pytest.skip("Invalid device config")

        ip = device_config.get('ip')
        if ip:
            result = await agent.set_color(ip, "blue")
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
