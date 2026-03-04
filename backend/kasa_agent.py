import asyncio
import os
from kasa import Discover, SmartDevice, SmartBulb, SmartPlug

class KasaAgent:
    def __init__(self, known_devices=None, on_update=None):
        self.devices = {}
        self.known_devices_config = known_devices or []
        self.on_update = on_update
        self.include_raw = os.environ.get("INCLUDE_RAW_LOGS", "False") == "True"

    def set_on_update(self, callback):
        """Sets the callback function for device updates."""
        self.on_update = callback

    def _log(self, *args, **kwargs):
        if self.include_raw:
            print(*args, **kwargs)

    async def initialize(self):
        """Initializes devices from the saved configuration."""
        if self.known_devices_config:
            self._log(f"[KasaAgent] Initializing {len(self.known_devices_config)} known devices...")
            tasks = []
            # The config can be a list of dicts from a file, or a dict from the test fixture
            if isinstance(self.known_devices_config, dict):
                for ip, info in self.known_devices_config.items():
                    alias = info.get('alias')
                    tasks.append(self._add_known_device(ip, alias, info))
            else:
                for d in self.known_devices_config:
                    if not d: continue
                    ip = d.get('ip')
                    alias = d.get('alias')
                    if ip:
                        # Create a device instance from IP
                        tasks.append(self._add_known_device(ip, alias, d))
            
            if tasks:
                await asyncio.gather(*tasks)

    async def _add_known_device(self, ip, alias, info):
        """Adds a device from settings without discovery scan."""
        try:
            # We can't know the exact class (Bulb/Plug) without connecting, 
            # but Discover.discover_single might work, or just SmartDevice(ip)
            # SmartDevice is the base class.
            dev = await Discover.discover_single(ip)
            if dev:
                await dev.update()
                self.devices[ip] = dev
                self._log(f"[KasaAgent] Loaded known device: {dev.alias} ({ip})")
            else:
                 self._log(f"[KasaAgent] Could not connect to known device at {ip}")
        except Exception as e:
            self._log(f"[KasaAgent] Error loading known device {ip}: {e}")

    async def discover_devices(self):
        """Discovers devices on the local network."""
        self._log("Discovering Kasa devices (Broadcast)...")
        # Use explicit broadcast and slightly longer timeout for Windows reliability
        found_devices = await Discover.discover(target="255.255.255.255", timeout=5)
        self._log(f"[KasaAgent] Raw discovery found {len(found_devices)} devices.")
        
        # We don't wipe self.devices completely, we merge/update
        # But if a device is NOT found, we might want to keep it if it was known?
        # User said: "If a device that is in settings can not be found just list as not found."
        # This implies we might want to mark them offline.
        
        for ip, dev in found_devices.items():
            await dev.update()
            self.devices[ip] = dev
            
        device_list = self.get_devices_list()
        self._log(f"Total Kasa devices (found + cached): {len(device_list)}")
        return device_list

    def get_devices_list(self):
        """Returns a list of device dictionaries for the frontend."""
        device_list = []
        for ip, dev in self.devices.items():
            # Determine type and capabilities
            dev_type = "unknown"
            if dev.is_bulb:
                dev_type = "bulb"
            elif dev.is_plug:
                dev_type = "plug"
            elif dev.is_strip:
                dev_type = "strip"
            elif dev.is_dimmer:
                dev_type = "dimmer"

            device_info = {
                "ip": ip,
                "alias": dev.alias,
                "model": dev.model,
                "type": dev_type,
                "is_on": dev.is_on,
                "brightness": dev.brightness if dev.is_bulb or dev.is_dimmer else None,
                "hsv": dev.hsv if dev.is_bulb and dev.is_color else None,
                "has_color": dev.is_color if dev.is_bulb else False,
                "has_brightness": dev.is_dimmable if dev.is_bulb or dev.is_dimmer else False
            }
            device_list.append(device_info)
        return device_list

    def get_formatted_list(self):
        """Returns a formatted string of devices for the LLM."""
        frontend_list = self.get_devices_list()

        dev_summaries = []
        for d in frontend_list:
            info = f"{d['alias']} (IP: {d['ip']}, Type: {d['type']})"
            if d['is_on']:
                info += " [ON]"
            else:
                info += " [OFF]"
            dev_summaries.append(info)

        result_str = "No devices found in cache."
        if dev_summaries:
            result_str = "Found Devices (Cached):\n" + "\n".join(dev_summaries)

        # Trigger frontend update as well since we are fetching
        if self.on_update:
             self.on_update(frontend_list)

        return result_str

    async def control_device(self, target, action, brightness=None, color=None):
        """Orchestrates control actions on a device."""
        result_msg = f"Action '{action}' on '{target}' failed."
        dev = await self._resolve_device(target)
        if not dev:
            return result_msg

        success = False
        try:
            if action == "turn_on":
                await dev.turn_on()
                success = True
                result_msg = f"Turned ON '{target}'."
            elif action == "turn_off":
                await dev.turn_off()
                success = True
                result_msg = f"Turned OFF '{target}'."
            elif action == "set":
                success = True
                result_msg = f"Updated '{target}':"

            if success or action == "set":
                if brightness is not None and (dev.is_dimmable or dev.is_bulb):
                    await dev.set_brightness(int(brightness))
                    result_msg += f" Set brightness to {brightness}."
                if color is not None and dev.is_color:
                    hsv = self.name_to_hsv(color) if isinstance(color, str) else (color if isinstance(color, (tuple, list)) and len(color) == 3 else None)
                    if hsv:
                        await dev.set_hsv(int(hsv[0]), int(hsv[1]), int(hsv[2]))
                        result_msg += f" Set color to {color}."

            if success or brightness is not None or color is not None:
                await dev.update()

        except Exception as e:
            print(f"Error controlling {target}: {e}")
            return result_msg

        # Notify Frontend of State Change
        if self.on_update:
            self.on_update(self.get_devices_list())

        return result_msg

    def get_device_by_alias(self, alias):
        """Finds a device by its alias (case-insensitive)."""
        for ip, dev in self.devices.items():
            if dev.alias.lower() == alias.lower():
                return dev
        return None

    async def _resolve_device(self, target):
        """Resolves a target string (IP or Alias) to a device object, attempting discovery if missing."""
        # 1. Check IP in cache
        if target in self.devices:
            return self.devices[target]
        
        # 2. Check Alias in cache
        dev = self.get_device_by_alias(target)
        if dev:
            return dev
            
        # 3. Fallback: Discovery if it looks like an IP
        if target.count(".") == 3:
             try:
                dev = await Discover.discover_single(target)
                if dev:
                    self.devices[target] = dev
                    return dev
             except Exception:
                 pass

        return None

    def name_to_hsv(self, color_name):
        """Converts common color names to HSV (Hue, Saturation, Value).
           Hue: 0-360, Sat: 0-100, Val: 0-100
        """
        color_name = color_name.lower().strip()
        colors = {
            "red": (0, 100, 100),
            "orange": (30, 100, 100),
            "yellow": (60, 100, 100),
            "green": (120, 100, 100),
            "cyan": (180, 100, 100),
            "blue": (240, 100, 100),
            "purple": (300, 100, 100),
            "pink": (300, 50, 100),
            "white": (0, 0, 100),
            "warm": (30, 20, 100), # Warm White approx
            "cool": (200, 10, 100), # Cool White approx
            "daylight": (0, 0, 100),
        }
        return colors.get(color_name, None)

# Standalone test
if __name__ == "__main__":
    async def main():
        agent = KasaAgent()
        await agent.discover_devices()
        print("Devices:", agent.devices)
        
        # Example Test
        # await agent.turn_on("Bedroom Light")
        # await agent.set_color("Bedroom Light", "Red")
    
    asyncio.run(main())
