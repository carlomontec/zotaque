"""
Zotac Zone Fan Curve Engine & Thermal Monitor.
Interpolates custom fan curves with hysteresis against APU / CPU hwmon temperatures.
"""

import glob
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class ThermalMonitor:
    """Discovers and reads temperature sensors from Linux hwmon."""

    @staticmethod
    def get_apu_temp() -> Optional[float]:
        """Scans /sys/class/hwmon for AMD k10temp / amdgpu or cpu thermal sensors."""
        hwmon_paths = glob.glob("/sys/class/hwmon/hwmon*")
        for hwmon in hwmon_paths:
            p = Path(hwmon)
            name_file = p / "name"
            if name_file.exists():
                name = name_file.read_text().strip().lower()
                if "k10temp" in name or "amdgpu" in name or "coretemp" in name:
                    # Look for temp1_input, temp2_input (Tctl/Tdie)
                    for temp_node in sorted(p.glob("temp*_input")):
                        try:
                            raw_val = int(temp_node.read_text().strip())
                            return raw_val / 1000.0  # millidegrees to Celsius
                        except Exception:
                            continue

        # Fallback to thermal_zone
        thermal_zones = glob.glob("/sys/class/thermal/thermal_zone*/temp")
        if thermal_zones:
            try:
                raw_val = int(Path(thermal_zones[0]).read_text().strip())
                return raw_val / 1000.0
            except Exception:
                pass

        return None


class FanCurveEngine:
    """Calculates PWM output based on current temperature, curve points, and hysteresis."""

    def __init__(
        self,
        curve_points: Optional[List[Dict[str, float]]] = None,
        hysteresis: float = 3.0,
        pwm_sysfs_path: Optional[str] = None
    ):
        # Default curve: (Temp C -> PWM %)
        self.curve = curve_points or [
            {"temp": 45.0, "pwm_percent": 20.0},
            {"temp": 55.0, "pwm_percent": 35.0},
            {"temp": 68.0, "pwm_percent": 55.0},
            {"temp": 78.0, "pwm_percent": 80.0},
            {"temp": 85.0, "pwm_percent": 100.0},
        ]
        # Sort by temperature
        self.curve.sort(key=lambda x: x["temp"])
        self.hysteresis = hysteresis
        self.last_applied_pwm: Optional[float] = None
        self.last_temp: Optional[float] = None
        self.pwm_path = self._discover_pwm_path(pwm_sysfs_path)

    def _discover_pwm_path(self, override: Optional[str] = None) -> Optional[Path]:
        if override and Path(override).exists():
            return Path(override)

        # Common EC / platform driver PWM paths
        candidates = glob.glob("/sys/class/hwmon/hwmon*/pwm1") + \
                     glob.glob("/sys/devices/platform/zotac*/hwmon/hwmon*/pwm1")
        return Path(candidates[0]) if candidates else None

    def calculate_pwm(self, temp_c: float) -> float:
        """Calculates interpolated PWM percentage for a given temperature."""
        if temp_c <= self.curve[0]["temp"]:
            return self.curve[0]["pwm_percent"]
        if temp_c >= self.curve[-1]["temp"]:
            return self.curve[-1]["pwm_percent"]

        for i in range(len(self.curve) - 1):
            p1 = self.curve[i]
            p2 = self.curve[i + 1]
            if p1["temp"] <= temp_c <= p2["temp"]:
                ratio = (temp_c - p1["temp"]) / (p2["temp"] - p1["temp"])
                pwm = p1["pwm_percent"] + ratio * (p2["pwm_percent"] - p1["pwm_percent"])
                return max(0.0, min(100.0, pwm))

        return 50.0

    def apply_pwm(self, pwm_percent: float) -> bool:
        """Writes PWM value (0-255) to the discovered sysfs node."""
        if not self.pwm_path or not self.pwm_path.exists():
            return False
        try:
            raw_pwm = int(255 * (max(0.0, min(100.0, pwm_percent)) / 100.0))
            self.pwm_path.write_text(str(raw_pwm))
            self.last_applied_pwm = pwm_percent
            return True
        except Exception as e:
            return False

    def step(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Executes a single thermal check and adjusts fan speed if hysteresis allows.
        Returns: (current_temp, target_pwm)
        """
        temp = ThermalMonitor.get_apu_temp()
        if temp is None:
            return None, None

        target_pwm = self.calculate_pwm(temp)

        # Apply hysteresis: only update if temperature changed beyond threshold or target PWM shifted
        if self.last_temp is None or abs(temp - self.last_temp) >= self.hysteresis:
            self.apply_pwm(target_pwm)
            self.last_temp = temp

        return temp, target_pwm
