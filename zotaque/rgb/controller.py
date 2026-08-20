"""
Zotac Zone RGB Lighting Controller (Pure User-Space HID).
Communicates directly with the RGB Halo rings and rear accent lights via /dev/hidraw* / hidapi.
"""

import sys
import time
from typing import List, Optional, Tuple

try:
    import hid
except ImportError:
    hid = None

# Known Zotac Zone Controller USB IDs (composite controller + RGB MCU)
ZOTAC_VIDS = [0x1ee9, 0x197d, 0x0483, 0x1a40]
# Specific Known PIDs for Zotac Handheld MCU
ZOTAC_PIDS = [0x1590, 0x8840, 0x5750, 0x0001, 0x0002]

class ZotacRGBController:
    """Manages RGB Halo Rings and Accent LEDs on the Zotac Zone."""

    def __init__(self, vendor_id: Optional[int] = None, product_id: Optional[int] = None):
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.device = None

    def find_devices(self) -> List[dict]:
        """Scans for potential Zotac Zone HID controller devices."""
        if hid is None:
            raise RuntimeError("hidapi library is required. Install with: pip install hidapi")
        
        all_devices = hid.enumerate()
        matching = []
        for d in all_devices:
            vid = d.get('vendor_id')
            pid = d.get('product_id')
            if (self.vendor_id and vid == self.vendor_id) or (vid in ZOTAC_VIDS):
                matching.append(d)
        return matching or all_devices

    def connect(self) -> bool:
        """Connects to the Zotac Zone RGB HID interface."""
        if hid is None:
            return False

        try:
            if self.vendor_id and self.product_id:
                self.device = hid.device()
                self.device.open(self.vendor_id, self.product_id)
                return True

            # Auto-discover
            devices = self.find_devices()
            for d in devices:
                try:
                    dev = hid.device()
                    dev.open_path(d['path'])
                    self.device = dev
                    self.vendor_id = d.get('vendor_id')
                    self.product_id = d.get('product_id')
                    return True
                except Exception:
                    continue
        except Exception as e:
            print(f"[RGB] Connection error: {e}", file=sys.stderr)
        
        return False

    def close(self):
        """Closes the HID connection."""
        if self.device:
            try:
                self.device.close()
            except Exception:
                pass
            self.device = None

    def _send_report(self, report: bytes) -> bool:
        """Sends a raw HID report to the device."""
        if not self.device:
            if not self.connect():
                return False
        try:
            self.device.write(report)
            return True
        except Exception as e:
            print(f"[RGB] Error writing HID report: {e}", file=sys.stderr)
            return False

    def set_static_color(self, r: int, g: int, b: int, brightness: int = 100) -> bool:
        """Sets a static color for both stick halo rings and accent LEDs."""
        # Scale RGB with brightness (0-100)
        scale = max(0, min(100, brightness)) / 100.0
        r_val = int(r * scale)
        g_val = int(g * scale)
        b_val = int(b * scale)

        # Standard Zotac Zone RGB packet structure:
        # [Report ID: 0x00, Command: 0x5A, Mode: 0x01 (Static), R, G, B, Zone_Mask: 0xFF, Padding...]
        packet = bytearray(64)
        packet[0] = 0x00
        packet[1] = 0x5A  # RGB Command Header
        packet[2] = 0x01  # Mode: Static
        packet[3] = r_val & 0xFF
        packet[4] = g_val & 0xFF
        packet[5] = b_val & 0xFF
        packet[6] = 0xFF  # Apply to all zones (left halo, right halo, rear bar)
        return self._send_report(bytes(packet))

    def set_breathing(self, r: int, g: int, b: int, speed: int = 5, brightness: int = 100) -> bool:
        """Sets breathing/pulsing effect."""
        scale = max(0, min(100, brightness)) / 100.0
        r_val = int(r * scale)
        g_val = int(g * scale)
        b_val = int(b * scale)

        packet = bytearray(64)
        packet[0] = 0x00
        packet[1] = 0x5A
        packet[2] = 0x02  # Mode: Breathing
        packet[3] = r_val & 0xFF
        packet[4] = g_val & 0xFF
        packet[5] = b_val & 0xFF
        packet[6] = max(1, min(10, speed))  # Speed factor
        packet[7] = 0xFF  # All zones
        return self._send_report(bytes(packet))

    def set_rainbow_wave(self, speed: int = 5, brightness: int = 100) -> bool:
        """Sets animated rainbow wave mode."""
        packet = bytearray(64)
        packet[0] = 0x00
        packet[1] = 0x5A
        packet[2] = 0x03  # Mode: Rainbow
        packet[3] = max(0, min(100, brightness))
        packet[4] = max(1, min(10, speed))
        packet[5] = 0xFF  # All zones
        return self._send_report(bytes(packet))

    def turn_off(self) -> bool:
        """Turns off all RGB lighting."""
        packet = bytearray(64)
        packet[0] = 0x00
        packet[1] = 0x5A
        packet[2] = 0x00  # Mode: Off
        return self._send_report(bytes(packet))
