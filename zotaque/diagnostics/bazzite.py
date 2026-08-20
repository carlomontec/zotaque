"""
Zotac Zone & Bazzite Diagnostic Tool.
Probes hardware nodes, USB descriptors, IIO sensors, and Decky Loader state.
"""

import glob
import os
import subprocess
from pathlib import Path
from typing import Any, Dict


def check_os_info() -> Dict[str, str]:
    info = {}
    os_release = Path("/etc/os-release")
    if os_release.exists():
        for line in os_release.read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                info[k.strip()] = v.strip().strip('"')
    try:
        uname = subprocess.check_output(["uname", "-r"], text=True).strip()
        info["KERNEL"] = uname
    except Exception:
        pass
    return info


def check_usb_devices() -> list:
    devices = []
    try:
        out = subprocess.check_output(["lsusb"], text=True)
        for line in out.strip().splitlines():
            devices.append(line)
    except Exception:
        pass
    return devices


def check_iio_sensors() -> list:
    sensors = []
    for d in sorted(glob.glob("/sys/bus/iio/devices/iio:device*")):
        p = Path(d)
        name = (p / "name").read_text().strip() if (p / "name").exists() else "unknown"
        has_accel = (p / "in_accel_x_raw").exists()
        has_gyro = (p / "in_anglvel_x_raw").exists()
        sensors.append({
            "path": d,
            "name": name,
            "has_accelerometer": has_accel,
            "has_gyroscope": has_gyro
        })
    return sensors


def check_hwmon() -> list:
    nodes = []
    for h in sorted(glob.glob("/sys/class/hwmon/hwmon*")):
        p = Path(h)
        name = (p / "name").read_text().strip() if (p / "name").exists() else "unknown"
        pwms = [str(x.name) for x in p.glob("pwm*")]
        temps = [str(x.name) for x in p.glob("temp*_input")]
        nodes.append({
            "path": h,
            "name": name,
            "pwms": pwms,
            "temp_sensors": len(temps)
        })
    return nodes


def check_decky_status() -> Dict[str, Any]:
    home = Path.home()
    cef_debug = home / ".steam/steam/.cef-enable-remote-debugging"
    decky_dir = Path("/home/deck/homebrew")
    
    service_active = False
    try:
        res = subprocess.run(
            ["systemctl", "is-active", "plugin_loader.service"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        service_active = (res.stdout.strip() == "active")
    except Exception:
        pass

    return {
        "cef_remote_debugging_enabled": cef_debug.exists(),
        "decky_installed": decky_dir.exists(),
        "plugin_loader_active": service_active
    }


def run_full_diagnostic() -> Dict[str, Any]:
    return {
        "os": check_os_info(),
        "usb": check_usb_devices(),
        "iio_sensors": check_iio_sensors(),
        "hwmon": check_hwmon(),
        "decky": check_decky_status()
    }
