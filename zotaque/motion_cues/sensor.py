"""
Linux IIO Subsystem Reader for Zotac Zone 6-Axis IMU (Accelerometer + Gyroscope).
Reads /sys/bus/iio/devices/iio:device*.
"""

import glob
import os
import time
from pathlib import Path
from typing import Dict, Optional, Tuple


class IIOIMUSensor:
    """Reads raw Accelerometer & Gyroscope data from Linux IIO devices."""

    def __init__(self, device_path: Optional[str] = None):
        self.device_path = self._find_iio_device(device_path)
        self.accel_scale = self._read_scale("in_accel_scale", default=0.000598)  # standard m/s^2 conversion
        self.gyro_scale = self._read_scale("in_anglvel_scale", default=0.001064) # rad/s conversion

    def _find_iio_device(self, override: Optional[str] = None) -> Optional[Path]:
        if override and Path(override).exists():
            return Path(override)

        # Search /sys/bus/iio/devices/
        devices = sorted(glob.glob("/sys/bus/iio/devices/iio:device*"))
        for d in devices:
            p = Path(d)
            # Check if this device exposes accel or gyro
            if (p / "in_accel_x_raw").exists() or (p / "in_accel_z_raw").exists():
                return p
        return Path(devices[0]) if devices else None

    def _read_scale(self, filename: str, default: float) -> float:
        if self.device_path:
            scale_file = self.device_path / filename
            if scale_file.exists():
                try:
                    return float(scale_file.read_text().strip())
                except Exception:
                    pass
        return default

    def _read_raw_node(self, filename: str) -> Optional[int]:
        if not self.device_path:
            return None
        node = self.device_path / filename
        if node.exists():
            try:
                return int(node.read_text().strip())
            except Exception:
                pass
        return None

    def read_accel(self) -> Tuple[float, float, float]:
        """
        Returns (accel_x, accel_y, accel_z) in m/s^2.
        """
        raw_x = self._read_raw_node("in_accel_x_raw") or 0
        raw_y = self._read_raw_node("in_accel_y_raw") or 0
        raw_z = self._read_raw_node("in_accel_z_raw") or 0
        return (
            raw_x * self.accel_scale,
            raw_y * self.accel_scale,
            raw_z * self.accel_scale
        )

    def read_gyro(self) -> Tuple[float, float, float]:
        """
        Returns (gyro_x, gyro_y, gyro_z) in rad/s.
        """
        raw_x = self._read_raw_node("in_anglvel_x_raw") or 0
        raw_y = self._read_raw_node("in_anglvel_y_raw") or 0
        raw_z = self._read_raw_node("in_anglvel_z_raw") or 0
        return (
            raw_x * self.gyro_scale,
            raw_y * self.gyro_scale,
            raw_z * self.gyro_scale
        )

    def read_sample(self) -> Dict[str, float]:
        """Returns unified timestamped IMU sample."""
        ax, ay, az = self.read_accel()
        gx, gy, gz = self.read_gyro()
        return {
            "timestamp": time.time(),
            "accel_x": ax,
            "accel_y": ay,
            "accel_z": az,
            "gyro_x": gx,
            "gyro_y": gy,
            "gyro_z": gz,
        }
