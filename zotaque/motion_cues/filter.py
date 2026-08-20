"""
Motion Cues Signal Processing & Sensor Fusion.
Filters road vibration (LPF) and removes gravity/tilt to extract clean 2D vehicle motion vectors.
"""

import math
import time
from typing import Dict, Optional, Tuple


class MotionCuesFilter:
    """
    Sensor fusion engine isolating vehicle inertia from handheld tilt and road noise.
    """

    def __init__(
        self,
        cutoff_hz: float = 1.5,
        sample_rate_hz: float = 50.0,
        sensitivity: float = 1.2
    ):
        self.cutoff_hz = cutoff_hz
        self.sample_rate_hz = sample_rate_hz
        self.sensitivity = sensitivity

        # Exponential Moving Average smoothing factors
        # alpha = dt / (RC + dt) = 2*pi*fc*dt / (2*pi*fc*dt + 1)
        dt = 1.0 / sample_rate_hz
        rc_vibration = 1.0 / (2.0 * math.pi * cutoff_hz)
        self.alpha_lpf = dt / (rc_vibration + dt)

        # Slow EMA for gravity / static tilt estimation (~3.0 sec time constant)
        rc_gravity = 3.0
        self.alpha_gravity = dt / (rc_gravity + dt)

        # State vectors
        self.gravity_x = 0.0
        self.gravity_y = 0.0
        self.gravity_z = 9.81

        self.filtered_accel_x = 0.0
        self.filtered_accel_y = 0.0
        self.filtered_accel_z = 0.0

        self.output_dx = 0.0
        self.output_dy = 0.0
        self.last_timestamp: Optional[float] = None

    def reset(self):
        """Resets filter states."""
        self.gravity_x = 0.0
        self.gravity_y = 0.0
        self.gravity_z = 9.81
        self.filtered_accel_x = 0.0
        self.filtered_accel_y = 0.0
        self.filtered_accel_z = 0.0
        self.output_dx = 0.0
        self.output_dy = 0.0
        self.last_timestamp = None

    def process_imu_sample(
        self,
        ax: float,
        ay: float,
        az: float,
        timestamp: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Processes a raw accelerometer read in m/s^2.
        Returns:
            {
                "dx": float (-1.0 to 1.0 normalized visual horizontal shift),
                "dy": float (-1.0 to 1.0 normalized visual vertical shift),
                "intensity": float (0.0 to 1.0 magnitude),
                "raw_linear_x": float,
                "raw_linear_y": float
            }
        """
        if self.last_timestamp is None:
            self.gravity_x = ax
            self.gravity_y = ay
            self.gravity_z = az
            self.last_timestamp = timestamp or time.time()
            return {"dx": 0.0, "dy": 0.0, "intensity": 0.0, "raw_linear_x": 0.0, "raw_linear_y": 0.0}

        # 1. Update slow gravity / tilt tracking
        self.gravity_x += self.alpha_gravity * (ax - self.gravity_x)
        self.gravity_y += self.alpha_gravity * (ay - self.gravity_y)
        self.gravity_z += self.alpha_gravity * (az - self.gravity_z)

        # 2. Subtract gravity to get dynamic linear vehicle acceleration
        lin_x = ax - self.gravity_x
        lin_y = ay - self.gravity_y
        lin_z = az - self.gravity_z

        # 3. Apply Low-Pass Filter to remove high frequency vibration (potholes, engine RPM)
        self.filtered_accel_x += self.alpha_lpf * (lin_x - self.filtered_accel_x)
        self.filtered_accel_y += self.alpha_lpf * (lin_y - self.filtered_accel_y)
        self.filtered_accel_z += self.alpha_lpf * (lin_z - self.filtered_accel_z)

        # 4. Map vehicle physics to Apple-style visual cues
        # Centrifugal turn left/right maps to lateral shift
        # Forward acceleration/braking maps to vertical shift
        # Clamped to [-1.0, 1.0]
        raw_dx = -(self.filtered_accel_x * self.sensitivity) / 4.0
        raw_dy = (self.filtered_accel_y * self.sensitivity) / 4.0

        self.output_dx = max(-1.0, min(1.0, raw_dx))
        self.output_dy = max(-1.0, min(1.0, raw_dy))
        intensity = min(1.0, math.sqrt(self.output_dx**2 + self.output_dy**2))

        return {
            "dx": round(self.output_dx, 4),
            "dy": round(self.output_dy, 4),
            "intensity": round(intensity, 4),
            "raw_linear_x": round(self.filtered_accel_x, 3),
            "raw_linear_y": round(self.filtered_accel_y, 3)
        }
