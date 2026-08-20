# Zotaque 🎮⚡

**Zotaque** is a pure user-space Linux companion suite and hardware toolkit specifically built for the **ZOTAC GAMING ZONE** running **Bazzite Linux** (or SteamOS / Atomic Fedora Silverblue).

---

## 🌟 Why User-Space First on Bazzite?

On atomic/immutable Linux operating systems like Bazzite (`rpm-ostree` / `bootc`), kernel updates regularly break out-of-tree compiled kernel drivers (`.ko` modules). 

**Zotaque solves this by operating directly in user-space:**
- **RGB Halo Rings & Accent LEDs**: Directly controlled over USB HID (`hidapi` / `/dev/hidraw*`).
- **Thumbstick Radial Dials**: Parsed from HID / `evdev` step deltas and dispatched to PipeWire (volume), `/sys/class/backlight` (brightness), or `uinput` virtual events.
- **Vehicle Motion Cues (Apple-style Motion Cues)**: Reads raw 6-axis IMU sensors via `/sys/bus/iio/devices/iio:device*`, applies real-time Butterworth low-pass filtering and tilt/gravity isolation, and streams floating boundary dots over a WebSocket overlay.
- **Fan Curve Engine**: Hysteresis-aware thermal controller reading `k10temp` / `amdgpu` and writing directly to PWM sysfs nodes.

---

## 🚀 Quick Start on Bazzite via SSH

### 1. Connect to your Zotac Zone
```bash
# On your Zotac Zone terminal (or via SSH deck@<IP>)
cd ~
git clone <your-repo-url> zotaque
cd zotaque
pip install -e .
```

### 2. Run Diagnostics
Check your hardware nodes, IIO sensors, USB descriptors, and Decky status:
```bash
zotaque diag
```

### 3. Control RGB Halo Rings
```bash
# Set dynamic rainbow wave
zotaque rgb rainbow --brightness 80 --speed 5

# Set static teal/cyan
zotaque rgb static --hex 00e5ff --brightness 90

# Set breathing pulse
zotaque rgb breathing --hex ff007f --speed 4

# Turn off lights
zotaque rgb off
```

### 4. Enable Radial Dial Mapper
Maps the left dial to display brightness and right dial to system volume:
```bash
zotaque dials --left brightness --right volume
```

### 5. Launch Vehicle Motion Cues (Anti-Motion Sickness in Cars)
Starts the real-time sensor fusion daemon and serves a transparent kinetic dots overlay on port 8765:
```bash
zotaque motion-cues --port 8765
```
Open `http://localhost:8765` in any browser / Steam web overlay to see the animated floating dots that sync with vehicle movement and turns.

---

## ⚙️ Enable Automatic Background Daemons (Systemd)

To make your settings persist across reboots on Bazzite:
```bash
./systemd/install-services.sh
```
Or enable services individually:
```bash
systemctl --user enable --now zotaque-rgb.service
systemctl --user enable --now zotaque-dials.service
systemctl --user enable --now zotaque-motion-cues.service
```

---

## 🧩 Decky Loader Plugin Integration

The repository includes a ready-to-build Decky plugin under `decky-plugin/` for controlling RGB, fan profiles, and motion cues directly from the Steam Quick Access Menu (QAM) in Gaming Mode.

---

## 🧪 Testing

Run test suite:
```bash
python3 -m unittest discover tests/
```
