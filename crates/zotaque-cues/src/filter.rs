use std::time::Instant;

#[derive(Clone, Debug)]
pub struct FilterConfig {
    pub tilt_sensitivity: f32,
    pub dynamic_sensitivity: f32,
    pub smoothing: f32,
    pub max_shift_px: f32,
    pub dot_radius: f32,
    pub dot_color_rgba: (u8, u8, u8, u8),
    pub dot_count_edge: usize,
}

impl Default for FilterConfig {
    fn default() -> Self {
        Self {
            tilt_sensitivity: 1.0,
            dynamic_sensitivity: 1.2,
            smoothing: 0.85,
            max_shift_px: 50.0,
            dot_radius: 7.0,
            dot_color_rgba: (0, 229, 255, 220), // Neon Cyan
            dot_count_edge: 8,
        }
    }
}

pub struct MotionCuesFilter {
    pub config: FilterConfig,
    filtered_ax: f32,
    filtered_ay: f32,
    filtered_az: f32,
    gravity_ax: f32,
    gravity_ay: f32,
    gravity_az: f32,
    last_time: Option<Instant>,
}

impl MotionCuesFilter {
    pub fn new(config: FilterConfig) -> Self {
        Self {
            config,
            filtered_ax: 0.0,
            filtered_ay: 0.0,
            filtered_az: 9.81,
            gravity_ax: 0.0,
            gravity_ay: 0.0,
            gravity_az: 9.81,
            last_time: None,
        }
    }

    pub fn process(&mut self, ax: f32, ay: f32, az: f32) -> (f32, f32, f32) {
        let now = Instant::now();
        let dt = match self.last_time {
            Some(t) => (now - t).as_secs_f32().clamp(0.001, 0.1),
            None => {
                self.filtered_ax = ax;
                self.filtered_ay = ay;
                self.filtered_az = az;
                self.gravity_ax = ax;
                self.gravity_ay = ay;
                self.gravity_az = az;
                self.last_time = Some(now);
                return (0.0, 0.0, 0.0);
            }
        };
        self.last_time = Some(now);

        // 1. Low-Pass Smoothing (Anti-Vibration)
        let alpha = (1.0 - self.config.smoothing).clamp(0.02, 0.95);
        self.filtered_ax += alpha * (ax - self.filtered_ax);
        self.filtered_ay += alpha * (ay - self.filtered_ay);
        self.filtered_az += alpha * (az - self.filtered_az);

        // 2. Slow baseline decay for neutral posture / gravity tracking
        let alpha_grav = dt / (3.5 + dt);
        self.gravity_ax += alpha_grav * (self.filtered_ax - self.gravity_ax);
        self.gravity_ay += alpha_grav * (self.filtered_ay - self.gravity_ay);
        self.gravity_az += alpha_grav * (self.filtered_az - self.gravity_az);

        // 3. Dynamic linear vehicle forces
        let dyn_x = self.filtered_ax - self.gravity_ax;
        let dyn_y = self.filtered_ay - self.gravity_ay;

        // 4. Handheld Tilt component
        let tilt_x = (self.filtered_ax / 9.81) * self.config.tilt_sensitivity;
        let tilt_y = (self.filtered_ay / 9.81) * self.config.tilt_sensitivity;

        // 5. Output 2D motion shift vector [-1.0, 1.0]
        let raw_dx = -(dyn_x * self.config.dynamic_sensitivity / 4.0 + tilt_x * 0.4);
        let raw_dy = dyn_y * self.config.dynamic_sensitivity / 4.0 + tilt_y * 0.4;

        let dx = raw_dx.clamp(-1.0, 1.0);
        let dy = raw_dy.clamp(-1.0, 1.0);
        let intensity = (dx * dx + dy * dy).sqrt().min(1.0);

        (dx, dy, intensity)
    }
}
