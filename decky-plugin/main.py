import asyncio
import os
import sys
import decky_plugin

# Add parent dir to sys.path to import zotaque modules
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(PLUGIN_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from zotaque.fan.curve import ThermalMonitor
from zotaque.motion_cues.filter import MotionCuesFilter
from zotaque.motion_cues.sensor import IIOIMUSensor
from zotaque.rgb.controller import ZotacRGBController


class Plugin:
    async def _main(self):
        decky_plugin.logger.info("Zotaque Decky Plugin Initializing...")
        self.rgb = ZotacRGBController()
        self.sensor = IIOIMUSensor()
        self.filter = MotionCuesFilter(tilt_sensitivity=1.2, dynamic_sensitivity=1.2)
        self.motion_task = asyncio.create_task(self._motion_loop())
        decky_plugin.logger.info("Zotaque Motion Cues background task started.")

    async def _unload(self):
        decky_plugin.logger.info("Zotaque Decky Plugin Unloading...")
        if hasattr(self, "motion_task") and self.motion_task:
            self.motion_task.cancel()

    async def _motion_loop(self):
        """Samples sensor at 50Hz and pushes events directly to Steam UI via Decky router."""
        while True:
            try:
                sample = self.sensor.read_sample()
                vec = self.filter.process_imu_sample(
                    sample["accel_x"],
                    sample["accel_y"],
                    sample["accel_z"],
                    timestamp=sample["timestamp"]
                )
                await decky_plugin.emit_event("zotaque_motion", vec)
                await asyncio.sleep(1.0 / 50.0)  # 50 Hz
            except asyncio.CancelledError:
                break
            except Exception as e:
                await asyncio.sleep(0.5)

    async def get_motion_sample(self):
        """Direct fallback query for current 2D motion vector."""
        sample = self.sensor.read_sample()
        return self.filter.process_imu_sample(
            sample["accel_x"],
            sample["accel_y"],
            sample["accel_z"],
            timestamp=sample["timestamp"]
        )

    async def update_motion_config(self, config: dict):
        """Updates tilt sensitivity or smoothing live."""
        if hasattr(self, "filter"):
            self.filter.update_parameters(config)
        return {"status": "ok"}

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
