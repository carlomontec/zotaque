"""
Zotac Zone Radial Dial Event Mapper.
Monitors thumbstick dial rotations and dispatches system volume, display brightness,
or virtual uinput keystrokes without kernel modules.
"""

import glob
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Dict, Optional

try:
    import evdev
    from evdev import UInput, ecodes as e
except ImportError:
    evdev = None


class SystemActions:
    """Dispatches common handheld actions on Bazzite / Linux."""

    @staticmethod
    def adjust_volume(delta_percent: int) -> None:
        """Adjusts volume using PipeWire / WirePlumber (wpctl) or amixer."""
        sign = "+" if delta_percent > 0 else "-"
        abs_val = abs(delta_percent) / 100.0
        try:
            subprocess.run(
                ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{abs_val:.2f}{sign}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False
            )
        except FileNotFoundError:
            try:
                subprocess.run(
                    ["amixer", "-D", "pulse", "sset", "Master", f"{abs(delta_percent)}%{sign}"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False
                )
            except Exception:
                pass

    @staticmethod
    def adjust_brightness(delta_percent: int) -> None:
        """Adjusts screen brightness using brightnessctl or /sys/class/backlight."""
        sign = "+" if delta_percent > 0 else "-"
        abs_val = abs(delta_percent)
        try:
            subprocess.run(
                ["brightnessctl", "set", f"{abs_val}%{sign}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False
            )
            return
        except FileNotFoundError:
            pass

        # Fallback: direct sysfs write
        backlights = glob.glob("/sys/class/backlight/*")
        if backlights:
            bl_path = Path(backlights[0])
            try:
                max_b = int((bl_path / "max_brightness").read_text().strip())
                curr_b = int((bl_path / "brightness").read_text().strip())
                step = int(max_b * (delta_percent / 100.0))
                new_b = max(0, min(max_b, curr_b + step))
                (bl_path / "brightness").write_text(str(new_b))
            except Exception:
                pass


class ZotacDialMapper:
    """Listens to radial dial HID/evdev reports and applies actions."""

    def __init__(
        self,
        left_action: str = "brightness",
        right_action: str = "volume",
        step_multiplier: int = 2
    ):
        self.left_action = left_action
        self.right_action = right_action
        self.step_multiplier = step_multiplier
        self.uinput_device: Optional[UInput] = None
        self._init_uinput()

    def _init_uinput(self) -> None:
        """Initializes virtual uinput device for keystrokes / scroll wheels."""
        if evdev is None:
            return
        try:
            cap = {
                e.EV_KEY: [e.KEY_VOLUMEUP, e.KEY_VOLUMEDOWN, e.KEY_BRIGHTNESSUP, e.KEY_BRIGHTNESSDOWN],
                e.EV_REL: [e.REL_WHEEL, e.REL_HWHEEL]
            }
            self.uinput_device = UInput(cap, name="Zotaque Virtual Dial Controller")
        except Exception as ex:
            print(f"[Dials] uinput initialization skipped/failed: {ex}", file=sys.stderr)

    def dispatch_action(self, action_name: str, direction: int) -> None:
        """
        Executes the configured action.
        direction: +1 (Clockwise), -1 (Counter-Clockwise)
        """
        delta = direction * self.step_multiplier
        if action_name == "volume":
            SystemActions.adjust_volume(delta * 2)
        elif action_name == "brightness":
            SystemActions.adjust_brightness(delta * 2)
        elif action_name == "scroll" and self.uinput_device:
            self.uinput_device.write(e.EV_REL, e.REL_WHEEL, direction)
            self.uinput_device.syn()

    def handle_dial_event(self, dial_id: str, delta: int) -> None:
        """
        Called when a dial rotation tick occurs.
        dial_id: 'left' or 'right'
        delta: +1 or -1
        """
        if dial_id == "left":
            self.dispatch_action(self.left_action, delta)
        elif dial_id == "right":
            self.dispatch_action(self.right_action, delta)

    def run_evdev_listener(self, device_path: Optional[str] = None) -> None:
        """Main loop listening for evdev input events."""
        if evdev is None:
            raise RuntimeError("evdev is required for Linux input monitoring")

        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        target_device = None

        if device_path:
            target_device = evdev.InputDevice(device_path)
        else:
            for dev in devices:
                if any(k in dev.name.lower() for k in ["zotac", "zone", "gamepad", "controller"]):
                    target_device = dev
                    break

        if not target_device and devices:
            # Fallback to first matching controller input device
            target_device = devices[0]

        if not target_device:
            print("[Dials] No input device found.", file=sys.stderr)
            return

        print(f"[Dials] Listening on {target_device.path} ({target_device.name})")
        for event in target_device.read_loop():
            # Intercept relative wheel or vendor-specific dial rotation codes
            if event.type == e.EV_REL:
                if event.code == e.REL_WHEEL:
                    self.handle_dial_event("right", 1 if event.value > 0 else -1)
                elif event.code == e.REL_HWHEEL:
                    self.handle_dial_event("left", 1 if event.value > 0 else -1)
