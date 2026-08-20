import os
import sys
import decky_plugin

# Add parent dir to sys.path to import zotaque modules
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(PLUGIN_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from zotaque.rgb.controller import ZotacRGBController
from zotaque.fan.curve import ThermalMonitor, FanCurveEngine

class Plugin:
    async def _main(self):
        decky_plugin.logger.info("Zotaque Decky Plugin Initialized")
        self.rgb = ZotacRGBController()

    async def _unload(self):
        decky_plugin.logger.info("Zotaque Decky Plugin Unloaded")

    async def set_rgb_mode(self, mode: str, hex_color: str = "00e5ff", brightness: int = 80, speed: int = 5):
        try:
            h = hex_color.lstrip("#")
            r, g, b = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
            if mode == "static":
                self.rgb.set_static_color(r, g, b, brightness=brightness)
            elif mode == "breathing":
                self.rgb.set_breathing(r, g, b, speed=speed, brightness=brightness)
            elif mode == "rainbow":
                self.rgb.set_rainbow_wave(speed=speed, brightness=brightness)
            elif mode == "off":
                self.rgb.turn_off()
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def get_apu_temperature(self):
        temp = ThermalMonitor.get_apu_temp()
        return {"temperature": temp}
