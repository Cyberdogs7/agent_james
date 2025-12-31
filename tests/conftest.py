import pytest

@pytest.fixture
def kasa_devices():
    return [
        {
            "ip": "192.168.1.100",
            "alias": "Living Room Lamp"
        }
    ]

@pytest.fixture
def printer_devices():
    return [
        {
            "name": "Ender 3",
            "host": "192.168.1.101",
            "port": 80,
            "printer_type": "octoprint"
        }
    ]
