use std::fs;
use std::path::{Path, PathBuf};

pub struct IMUSensor {
    device_path: Option<PathBuf>,
    accel_scale: f32,
}

impl IMUSensor {
    pub fn new() -> Self {
        let mut dev_path = None;
        for i in 0..8 {
            let p = PathBuf::from(format!("/sys/bus/iio/devices/iio:device{}", i));
            if p.join("in_accel_x_raw").exists() {
                dev_path = Some(p);
                break;
            }
        }

        let mut scale = 0.000598f32;
        if let Some(ref p) = dev_path {
            if let Ok(s) = fs::read_to_string(p.join("in_accel_scale")) {
                if let Ok(v) = s.trim().parse::<f32>() {
                    scale = v;
                }
            }
        }

        Self {
            device_path: dev_path,
            accel_scale: scale,
        }
    }

    fn read_raw_node(&self, name: &str) -> i32 {
        if let Some(ref p) = self.device_path {
            if let Ok(content) = fs::read_to_string(p.join(name)) {
                if let Ok(val) = content.trim().parse::<i32>() {
                    return val;
                }
            }
        }
        0
    }

    /// Reads raw accelerometer and maps native portrait motherboard axes
    /// into standard landscape gaming screen coordinates.
    pub fn read_accel_landscape(&self) -> (f32, f32, f32) {
        let raw_x = self.read_raw_node("in_accel_x_raw") as f32;
        let raw_y = self.read_raw_node("in_accel_y_raw") as f32;
        let raw_z = self.read_raw_node("in_accel_z_raw") as f32;

        // Native portrait to Landscape gaming orientation mapping:
        // UP on chip = Right of device
        let land_x = raw_y * self.accel_scale;
        let land_y = -raw_x * self.accel_scale;
        let land_z = raw_z * self.accel_scale;

        (land_x, land_y, land_z)
    }
}
