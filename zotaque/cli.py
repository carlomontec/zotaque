"""
Unified CLI for Zotaque (Zotac Zone Linux Toolkit).
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Ensure root directory is in sys.path when executed directly
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from zotaque.core.config import load_config, save_config
from zotaque.diagnostics.bazzite import run_full_diagnostic
from zotaque.dials.mapper import ZotacDialMapper
from zotaque.fan.curve import FanCurveEngine, ThermalMonitor
from zotaque.motion_cues.server import run_server as run_motion_server
from zotaque.rgb.controller import ZotacRGBController


def handle_diag(args):
    """Runs diagnostics and prints formatted summary."""
    diag = run_full_diagnostic()
    print("========================================")
    print("       ZOTAQUE DIAGNOSTIC REPORT        ")
    print("========================================")
    print(f"OS: {diag['os'].get('PRETTY_NAME', 'Linux')} (Kernel: {diag['os'].get('KERNEL', 'Unknown')})")
    print("\n[IIO Sensors]")
    if diag["iio_sensors"]:
        for s in diag["iio_sensors"]:
            print(f"  - {s['path']} ({s['name']}) -> Accel: {s['has_accelerometer']}, Gyro: {s['has_gyroscope']}")
    else:
        print("  No IIO devices found under /sys/bus/iio/devices/")

    print("\n[Hwmon & Thermals]")
    for h in diag["hwmon"]:
        print(f"  - {h['path']} ({h['name']}): {h['temp_sensors']} temp inputs, PWMs: {h['pwms']}")

    print("\n[Decky Loader Status]")
    print(f"  CEF Remote Debugging: {'Enabled' if diag['decky']['cef_remote_debugging_enabled'] else 'Disabled/Missing'}")
    print(f"  Decky Homebrew Dir:   {'Present' if diag['decky']['decky_installed'] else 'Not Found'}")
    print(f"  plugin_loader.service:{'Active' if diag['decky']['plugin_loader_active'] else 'Inactive'}")

    print("\n[USB Controllers]")
    for dev in diag["usb"]:
        if any(k in dev.lower() for k in ["zotac", "controller", "gamepad", "hid", "sensor"]):
            print(f"  - {dev}")


def handle_rgb(args):
    """Controls RGB Halo rings and LEDs."""
    controller = ZotacRGBController()
    if args.mode == "static":
        print(f"[RGB] Setting static color #{args.hex} (Brightness: {args.brightness}%)")
        h = args.hex.lstrip("#")
        r, g, b = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        controller.set_static_color(r, g, b, brightness=args.brightness)
    elif args.mode == "breathing":
        print(f"[RGB] Setting breathing color #{args.hex} (Speed: {args.speed})")
        h = args.hex.lstrip("#")
        r, g, b = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        controller.set_breathing(r, g, b, speed=args.speed, brightness=args.brightness)
    elif args.mode == "rainbow":
        print(f"[RGB] Setting rainbow wave (Speed: {args.speed}, Brightness: {args.brightness}%)")
        controller.set_rainbow_wave(speed=args.speed, brightness=args.brightness)
    elif args.mode == "off":
        print("[RGB] Turning off lighting")
        controller.turn_off()


def handle_dials(args):
    """Runs dial event listener."""
    print(f"[Dials] Starting dial monitor (Left: {args.left}, Right: {args.right})...")
    mapper = ZotacDialMapper(left_action=args.left, right_action=args.right)
    mapper.run_evdev_listener(device_path=args.device)


def handle_fan(args):
    """Runs fan thermal monitor / curve daemon."""
    engine = FanCurveEngine(hysteresis=args.hysteresis)
    print("[Fan] Starting fan curve engine. Polling interval: 2.0s...")
    import time
    while True:
        temp, pwm = engine.step()
        if temp is not None:
            print(f"[Fan] APU Temp: {temp:.1f}°C | Applied PWM: {pwm:.1f}%", end="\r")
        time.sleep(args.interval)


def handle_motion_cues(args):
    """Runs Apple-style vehicle motion cues server."""
    print(f"[Motion Cues] Starting daemon on {args.host}:{args.port}...")
    run_motion_server(host=args.host, port=args.port)


def main():
    parser = argparse.ArgumentParser(
        prog="zotaque",
        description="User-space Companion Suite & Drivers for ZOTAC GAMING ZONE"
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # Diag
    p_diag = subparsers.add_parser("diag", help="Run system and hardware diagnostic")
    p_diag.set_defaults(func=handle_diag)

    # RGB
    p_rgb = subparsers.add_parser("rgb", help="Control stick halo rings and accent RGB")
    p_rgb.add_argument("mode", choices=["static", "breathing", "rainbow", "off"], help="Lighting mode")
    p_rgb.add_argument("--hex", default="00e5ff", help="Hex color code (e.g. ff007f, default: 00e5ff)")
    p_rgb.add_argument("--brightness", type=int, default=80, help="Brightness (0-100)")
    p_rgb.add_argument("--speed", type=int, default=5, help="Animation speed (1-10)")
    p_rgb.set_defaults(func=handle_rgb)

    # Dials
    p_dials = subparsers.add_parser("dials", help="Start radial dial mapper daemon")
    p_dials.add_argument("--left", default="brightness", choices=["brightness", "volume", "scroll"], help="Action for left dial")
    p_dials.add_argument("--right", default="volume", choices=["volume", "brightness", "scroll"], help="Action for right dial")
    p_dials.add_argument("--device", default=None, help="Explicit evdev device path")
    p_dials.set_defaults(func=handle_dials)

    # Fan
    p_fan = subparsers.add_parser("fan", help="Run fan curve controller")
    p_fan.add_argument("--interval", type=float, default=2.0, help="Polling interval in seconds")
    p_fan.add_argument("--hysteresis", type=float, default=3.0, help="Hysteresis threshold in °C")
    p_fan.set_defaults(func=handle_fan)

    # Motion Cues
    p_motion = subparsers.add_parser("motion-cues", help="Run Vehicle Motion Cues overlay daemon")
    p_motion.add_argument("--host", default="0.0.0.0", help="Binding host")
    p_motion.add_argument("--port", type=int, default=8765, help="Port for WebSocket & HTTP overlay")
    p_motion.set_defaults(func=handle_motion_cues)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
