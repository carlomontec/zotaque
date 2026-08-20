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

    def test_motion_cues_filter_gravity_isolation(self):
        f = MotionCuesFilter(cutoff_hz=1.5, sample_rate_hz=50.0, sensitivity=1.0)
        
        # Feed static 1g on Z axis for 2 seconds (100 samples)
        for i in range(100):
            res = f.process_imu_sample(ax=0.0, ay=0.0, az=9.81, timestamp=i * 0.02)
        
        # When stationary, dynamic offset should converge close to 0
        self.assertAlmostEqual(res["dx"], 0.0, delta=0.05)
        self.assertAlmostEqual(res["dy"], 0.0, delta=0.05)
        self.assertAlmostEqual(res["intensity"], 0.0, delta=0.05)

    def test_motion_cues_filter_acceleration_response(self):
        f = MotionCuesFilter(cutoff_hz=1.5, sample_rate_hz=50.0, sensitivity=1.2)
        
        # Establish baseline
        for i in range(50):
            f.process_imu_sample(ax=0.0, ay=0.0, az=9.81, timestamp=i * 0.02)

        # Vehicle accelerates forward: sharp +2 m/s^2 linear force along Y axis for several frames
        res = None
        for i in range(50, 70):
            res = f.process_imu_sample(ax=0.0, ay=2.0, az=9.81, timestamp=i * 0.02)

        self.assertIsNotNone(res)
        self.assertGreater(res["dy"], 0.0)
        self.assertGreater(res["intensity"], 0.0)


if __name__ == "__main__":
    unittest.main()
