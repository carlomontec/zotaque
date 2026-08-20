import json
import os
from pathlib import Path
from typing import Any, Dict

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "zotaque"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "rgb": {
        "enabled": True,
        "mode": "rainbow",  # static, breathing, rainbow, off
        "brightness": 80,   # 0 - 100
        "speed": 5,         # 1 - 10
        "color_primary": [255, 0, 128],   # [R, G, B]
        "color_secondary": [0, 200, 255]
    },
    "dials": {
        "enabled": True,
        "left_dial_mode": "brightness",  # brightness, volume, scroll, custom
        "right_dial_mode": "volume",     # volume, brightness, scroll, custom
        "step_multiplier": 2
    },
    "fan": {
        "enabled": False,  # manual curve vs automatic EC
        "polling_interval_sec": 2.0,
        "hysteresis_celsius": 3.0,
        "curve": [
            {"temp": 45, "pwm_percent": 20},
            {"temp": 60, "pwm_percent": 45},
            {"temp": 75, "pwm_percent": 75},
            {"temp": 85, "pwm_percent": 100}
        ]
    },
    "motion_cues": {
        "enabled": True,
        "port": 8765,
        "filter_cutoff_hz": 1.5,
        "gravity_compensation": True,
        "sensitivity": 1.2,
        "dot_count": 16,
        "dot_color": "#00e5ff",
        "dot_opacity": 0.85
    }
}

def load_config() -> Dict[str, Any]:
    """Loads configuration from JSON file or returns default."""
    if not CONFIG_FILE.exists():
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            # Merge with default keys to ensure compatibility
            merged = DEFAULT_CONFIG.copy()
            for k, v in data.items():
                if isinstance(v, dict) and k in merged:
                    merged[k].update(v)
                else:
                    merged[k] = v
            return merged
    except Exception:
        return DEFAULT_CONFIG.copy()

def save_config(config: Dict[str, Any]) -> None:
    """Saves configuration to JSON file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
