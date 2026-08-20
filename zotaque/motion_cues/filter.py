"""
Motion Cues Signal Processing & Sensor Fusion.
Filters road vibration (LPF) and balances handheld tilt with dynamic vehicle inertia.
"""

import math
import time
from typing import Any, Dict, Optional


class MotionCuesFilter:
    """
    Sensor fusion engine isolating vehicle inertia while respecting handheld tilt.
    """

    def __init__(
        self,
        tilt_sensitivity: float = 1.0,
        dynamic_sensitivity: float = 1.2,
        smoothing: float = 0.85,
        max_shift_px: float = 50.0
    ):
        self.tilt_sensitivity = tilt_sensitivity
        self.dynamic_sensitivity = dynamic_sensitivity
        self.smoothing = smoothing
        self.max_shift_px = max_shift_px

        # Internal state
        self.filtered_ax = 0.0
        self.filtered_ay = 0.0
        self.filtered_az = 9.81

        self.gravity_ax = 0.0
        self.gravity_ay = 0.0
        self.gravity_az = 9.81

        self.output_dx = 0.0
        self.output_dy = 0.0
        self.last_time: Optional[float] = None

    def update_parameters(self, config: Dict[str, Any]) -> None:
        """Updates filter parameters live from GUI slider config."""
        if "tilt_sensitivity" in config:
            self.tilt_sensitivity = float(config["tilt_sensitivity"])
        if "dynamic_sensitivity" in config:
            self.dynamic_sensitivity = float(config["dynamic_sensitivity"])
        if "smoothing" in config:
            self.smoothing = max(0.1, min(0.98, float(config["smoothing"])))
        if "max_shift_px" in config:
            self.max_shift_px = float(config["max_shift_px"])

    def reset(self) -> None:
        """Resets filter memory."""
        self.filtered_ax = 0.0
        self.filtered_ay = 0.0
        self.filtered_az = 9.81
        self.gravity_ax = 0.0
        self.gravity_ay = 0.0
        self.gravity_az = 9.81
        self.output_dx = 0.0
        self.output_dy = 0.0
        self.last_time = None

    def process_imu_sample(
        self,
        ax: float,
        ay: float,
        az: float,
        timestamp: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Processes raw IMU read (in m/s^2).
        Returns normalized 2D motion shift coordinates [-1.0, 1.0] and telemetry.
        """
        now = timestamp or time.time()
        if self.last_time is None:
            self.filtered_ax = ax
            self.filtered_ay = ay
            self.filtered_az = az
            self.gravity_ax = ax
            self.gravity_ay = ay
            self.gravity_az = az
            self.last_time = now
            return {"dx": 0.0, "dy": 0.0, "intensity": 0.0, "ax": ax, "ay": ay, "az": az}

        # 1. Low-Pass Smoothing to eliminate road chatter / vibration
        alpha = 1.0 - self.smoothing
        self.filtered_ax += alpha * (ax - self.filtered_ax)
        self.filtered_ay += alpha * (ay - self.filtered_ay)
        self.filtered_az += alpha * (az - self.filtered_az)

        # 2. Slow baseline tracking for gravity/neutral seating position (~3.5 sec decay)
        dt = max(0.001, min(0.1, now - self.last_time))
        self.last_time = now
        alpha_grav = dt / (3.5 + dt)
        self.gravity_ax += alpha_grav * (self.filtered_ax - self.gravity_ax)
        self.gravity_ay += alpha_grav * (self.filtered_ay - self.gravity_ay)
        self.gravity_az += alpha_grav * (self.filtered_az - self.gravity_az)

        # 3. Dynamic Vehicle Inertia (Acceleration / Braking / Cornering)
        dyn_x = (self.filtered_ax - self.gravity_ax)
        dyn_y = (self.filtered_ay - self.gravity_ay)

        # 4. Instant Handheld Tilt component
        tilt_x = (self.filtered_ax / 9.81) * self.tilt_sensitivity
        tilt_y = (self.filtered_ay / 9.81) * self.tilt_sensitivity

        # 5. Combined Motion Cue vector
        # Centrifugal turn left/right (x-axis force) -> horizontal dot shift
        # Acceleration/braking (y-axis force) -> vertical dot shift
        raw_dx = -(dyn_x * self.dynamic_sensitivity / 4.0 + tilt_x * 0.4)
        raw_dy = (dyn_y * self.dynamic_sensitivity / 4.0 + tilt_y * 0.4)

        self.output_dx = max(-1.0, min(1.0, raw_dx))
        self.output_dy = max(-1.0, min(1.0, raw_dy))
        intensity = min(1.0, math.sqrt(self.output_dx**2 + self.output_dy**2))

        return {
            "dx": round(self.output_dx, 4),
            "dy": round(self.output_dy, 4),
            "intensity": round(intensity, 4),
            "ax": round(ax, 2),
            "ay": round(ay, 2),
            "az": round(az, 2)
        }
