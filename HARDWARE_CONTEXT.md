# Zotac Zone Linux Architecture & Hardware Specification (Zotaque)

## Overview & Target Platform
- **Target Device**: ZOTAC GAMING ZONE Handheld Console (AMD Ryzen 7 8840U, 120Hz AMOLED VRR, Dual Trackpads, Two-Stage Triggers, Radial Knobs, 6-Axis IMU)
- **Target OS**: Bazzite Linux (Fedora Silverblue / rpm-ostree / bootc atomic base running Gamescope session)
- **Core Philosophy**: **User-space first**. By relying on user-space USB HID (`hidapi`, `/dev/hidraw*`), IIO (`/sys/bus/iio/devices/`), and standard `hwmon` / `sysfs` instead of compiling out-of-tree kernel modules (`.ko`), the entire suite remains 100% resilient across Bazzite atomic OS updates and kernel version bumps.

---

## Hardware Subsystems & Interfaces

### 1. RGB Lighting & Halo Rings
- **Interface**: USB HID (`/dev/hidraw*` via `hidapi` / `libusb`)
- **Location**: Thumbstick halo rings and rear/accent light bars
- **Packet Structure**: Direct HID feature/output reports for static color, pulse/breathing, dynamic rainbow wave, and brightness.
- **Advantage**: No kernel driver required; runs entirely in user-space daemon or Decky plugin backend.

### 2. Radial Dials / Knobs
- **Interface**: USB HID report stream
- **Operation**: Microcontroller sends step deltas (CW / CCW rotation increments per click) rather than absolute potentiometer values.
- **Mapping**: Handled via `python-evdev` / `uinput` or direct D-Bus calls:
  - **Left Dial**: Display brightness (`/sys/class/backlight/` or Gamescope D-Bus)
  - **Right Dial**: Audio volume (PipeWire / WirePlumber D-Bus / ALSA)
  - **Custom Mode**: Mouse scroll wheel, emulator speed, or custom key combinations.

### 3. Fan Curves & Embedded Controller (EC)
- **Interface**: Linux `hwmon` (`k10temp` / `amdgpu` thermal inputs) and Embedded Controller registers.
- **Modes**:
  - Direct EC memory / sysfs reading (`pwm1`, `fan1_input`)
  - Configurable hysteresis curve daemon matching target APU temperatures to quiet/balanced/performance RPM profiles.

### 4. Vehicle Motion Cues (Apple-style Motion Cues Clone)
- **Interface**: Linux IIO subsystem (`/sys/bus/iio/devices/iio:device0/` or `iio:device1/`)
- **Nodes**:
  - `in_accel_x_raw`, `in_accel_y_raw`, `in_accel_z_raw`
  - `in_anglvel_x_raw`, `in_anglvel_y_raw`, `in_anglvel_z_raw`
  - `in_accel_scale`, `in_anglvel_scale`
- **Signal Processing**:
  - **Gravity Vector Compensation**: Separates static gravitational tilt (1g) from dynamic vehicle acceleration.
  - **Low-Pass Filter (LPF)**: Butterworth / EMA filter (\(f_c \approx 1\text{--}2\,\text{Hz}\)) to strip road chatter, potholes, and vehicle engine vibrations.
- **Visual Presentation**:
  - Transparent overlay rendering floating kinetic dots along the 4 screen borders reacting to vehicle inertia (forward accel, braking, left/right centrifugal turns).

### 5. Diagnostics & Decky Loader
- CEF remote debugging validation (`~/.steam/steam/.cef-enable-remote-debugging`)
- Plugin loader service health check (`plugin_loader.service`)
- Standalone headless systemd user service fallback.
