"""
Unit tests for Zotaque modules: filter algorithms, fan curves, and configuration.
"""

import math
import unittest
from zotaque.core.config import DEFAULT_CONFIG, load_config
from zotaque.fan.curve import FanCurveEngine
from zotaque.motion_cues.filter import MotionCuesFilter


class TestZotaque(unittest.TestCase):

    def test_config_defaults(self):
        cfg = load_config()
        self.assertIn("rgb", cfg)
        self.assertIn("dials", cfg)
        self.assertIn("motion_cues", cfg)

    def test_fan_curve_interpolation(self):
        engine = FanCurveEngine(curve_points=[
            {"temp": 40.0, "pwm_percent": 20.0},
            {"temp": 80.0, "pwm_percent": 100.0}
        ])
        # Below min
        self.assertEqual(engine.calculate_pwm(30.0), 20.0)
        # Above max
        self.assertEqual(engine.calculate_pwm(90.0), 100.0)
        # Midpoint (60 C -> 60%)
        self.assertAlmostEqual(engine.calculate_pwm(60.0), 60.0)

    def test_motion_cues_tilt_sensitivity(self):
        f = MotionCuesFilter(tilt_sensitivity=1.5, dynamic_sensitivity=1.0)
        
        # Tilt device sideways: raw ax = 4.0 m/s^2
        res = None
        for i in range(10):
            res = f.process_imu_sample(ax=4.0, ay=0.0, az=8.9, timestamp=i * 0.02)
        
        self.assertIsNotNone(res)
        # Sideways tilt should deflect DX
        self.assertNotEqual(res["dx"], 0.0)

    def test_motion_cues_dynamic_acceleration(self):
        f = MotionCuesFilter(tilt_sensitivity=0.5, dynamic_sensitivity=1.5)
        
        # Settle baseline
        for i in range(50):
            f.process_imu_sample(ax=0.0, ay=0.0, az=9.81, timestamp=i * 0.02)

        # Vehicle accelerates forward: sudden +3 m/s^2 linear force along Y axis
        res = None
        for i in range(50, 65):
            res = f.process_imu_sample(ax=0.0, ay=3.0, az=9.81, timestamp=i * 0.02)

        self.assertIsNotNone(res)
        self.assertGreater(res["dy"], 0.0)
        self.assertGreater(res["intensity"], 0.0)


if __name__ == "__main__":
    unittest.main()
