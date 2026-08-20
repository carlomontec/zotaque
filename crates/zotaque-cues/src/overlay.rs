use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

use tiny_skia::{Color, Paint, PathBuilder, Pixmap, Transform};
use x11rb::connection::Connection;
use x11rb::protocol::shape::{self, ConnectionExt as ShapeConnectionExt};
use x11rb::protocol::xproto::{
    self, AtomEnum, ClipOrdering, ColormapAlloc, ConnectionExt, CreateWindowAux, EventMask, Gcontext,
    ImageFormat, PropMode, VisualClass, Visualid, Window, WindowClass,
};
use x11rb::rust_connection::RustConnection;
use x11rb::wrapper::ConnectionExt as WrapperConnectionExt;

use crate::filter::{FilterConfig, MotionCuesFilter};
use crate::sensor::IMUSensor;

pub struct OverlayWindow {
    conn: RustConnection,
    screen_num: usize,
    window: Window,
    gc: Gcontext,
    width: u16,
    height: u16,
    depth: u8,
    visual_id: Visualid,
}

impl OverlayWindow {
    pub fn new() -> Result<Self, Box<dyn std::error::Error>> {
        let (conn, screen_num) = x11rb::connect(None)?;
        let screen = &conn.setup().roots[screen_num];

        let width = screen.width_in_pixels;
        let height = screen.height_in_pixels;

        // Find 32-bit ARGB TrueColor visual for per-pixel transparency
        let mut visual_id = screen.root_visual;
        let mut depth = screen.root_depth;

        for d in &screen.allowed_depths {
            if d.depth == 32 {
                for v in &d.visuals {
                    if v.class == VisualClass::TRUE_COLOR {
                        visual_id = v.visual_id;
                        depth = 32;
                        break;
                    }
                }
            }
        }

        let colormap = conn.generate_id()?;
        conn.create_colormap(ColormapAlloc::NONE, colormap, screen.root, visual_id)?;

        let window = conn.generate_id()?;
        let aux = CreateWindowAux::new()
            .override_redirect(1) // Frameless, bypass window manager decorations
            .colormap(colormap)
            .border_pixel(0)
            .background_pixel(0)
            .event_mask(EventMask::STRUCTURE_NOTIFY | EventMask::EXPOSURE);

        conn.create_window(
            depth,
            window,
            screen.root,
            0,
            0,
            width,
            height,
            0,
            WindowClass::INPUT_OUTPUT,
            visual_id,
            &aux,
        )?;

        // Gamescope-native overlay atoms (same as MangoApp)
        // GAMESCOPE_EXTERNAL_OVERLAY = 1 → composite on top of all games
        // GAMESCOPE_NO_FOCUS = 1 → never steal gamepad/keyboard focus
        let gs_overlay = conn.intern_atom(false, b"GAMESCOPE_EXTERNAL_OVERLAY")?.reply()?.atom;
        let gs_no_focus = conn.intern_atom(false, b"GAMESCOPE_NO_FOCUS")?.reply()?.atom;

        conn.change_property32(
            PropMode::REPLACE,
            window,
            gs_overlay,
            AtomEnum::CARDINAL,
            &[1],
        )?;

        conn.change_property32(
            PropMode::REPLACE,
            window,
            gs_no_focus,
            AtomEnum::CARDINAL,
            &[1],
        )?;

        // Set 100% Click-Through Input Mask via XShape extension
        // Games receive 100% of touches, buttons, and clicks!
        let _ = conn.shape_rectangles(
            shape::SO::SET,
            shape::SK::INPUT,
            ClipOrdering::UNSORTED,
            window,
            0,
            0,
            &[],
        );

        let gc = conn.generate_id()?;
        conn.create_gc(gc, window, &xproto::CreateGCAux::new())?;

        conn.map_window(window)?;
        conn.flush()?;

        Ok(Self {
            conn,
            screen_num,
            window,
            gc,
            width,
            height,
            depth,
            visual_id,
        })
    }

    pub fn run_render_loop(
        self,
        enabled_flag: Arc<AtomicBool>,
        config_mutex: Arc<Mutex<FilterConfig>>,
    ) {
        let sensor = IMUSensor::new();
        let init_cfg = config_mutex.lock().unwrap().clone();
        let mut filter = MotionCuesFilter::new(init_cfg);

        let w = self.width as u32;
        let h = self.height as u32;

        let mut pixmap = Pixmap::new(w, h).unwrap();
        let mut smooth_offset_x = 0.0f32;
        let mut smooth_offset_y = 0.0f32;
        let mut last_offset_x = f32::NAN;
        let mut last_offset_y = f32::NAN;
        let mut was_enabled = true;

        // 30 FPS is plenty smooth for motion cues and cuts X11 bandwidth by 4x
        let target_frame_time = Duration::from_millis(33); // ~30 FPS

        println!("[Overlay] Native 30Hz Gamescope Overlay loop running ({}x{})", w, h);

        loop {
            let start = Instant::now();
            let enabled = enabled_flag.load(Ordering::SeqCst);

            if enabled {
                if let Ok(cfg) = config_mutex.try_lock() {
                    filter.config = cfg.clone();
                }

                // 1. Read IMU sensor & filter
                let (ax, ay, az) = sensor.read_accel_landscape();
                let (dx, dy, intensity) = filter.process(ax, ay, az);

                // 2. Smooth visual offset
                let target_x = dx * filter.config.max_shift_px;
                let target_y = dy * filter.config.max_shift_px;
                smooth_offset_x += (target_x - smooth_offset_x) * 0.15;
                smooth_offset_y += (target_y - smooth_offset_y) * 0.15;

                // 3. Skip blit entirely if motion is negligible (saves ~95% of idle CPU)
                let delta = (smooth_offset_x - last_offset_x).abs() + (smooth_offset_y - last_offset_y).abs();
                if delta < 0.15 && !was_enabled.eq(&false) {
                    let elapsed = start.elapsed();
                    if elapsed < target_frame_time {
                        thread::sleep(target_frame_time - elapsed);
                    }
                    was_enabled = true;
                    continue;
                }
                last_offset_x = smooth_offset_x;
                last_offset_y = smooth_offset_y;
                was_enabled = true;

                // 4. Clear transparent buffer
                pixmap.fill(Color::TRANSPARENT);

                // 5. Draw anti-aliased kinetic dots
                let margin = 28.0f32;
                let count = filter.config.dot_count_edge;
                let radius = filter.config.dot_radius;
                let (r, g, b, a_base) = filter.config.dot_color_rgba;
                let alpha = (a_base as f32 / 255.0) * (0.4 + intensity * 0.55);

                let mut paint = Paint::default();
                paint.set_color_rgba8(r, g, b, (alpha * 255.0) as u8);
                paint.anti_alias = true;

                let w_f = w as f32;
                let h_f = h as f32;
                let mut dot_positions = Vec::with_capacity(count * 4);

                for i in 0..count {
                    let x = margin + ((w_f - margin * 2.0) / (count - 1) as f32) * i as f32;
                    dot_positions.push((x, margin));
                    dot_positions.push((x, h_f - margin));
                }
                for j in 1..(count - 1) {
                    let y = margin + ((h_f - margin * 2.0) / (count - 1) as f32) * j as f32;
                    dot_positions.push((margin, y));
                    dot_positions.push((w_f - margin, y));
                }

                for (bx, by) in dot_positions {
                    let px = bx + smooth_offset_x;
                    let py = by + smooth_offset_y;
                    let mut pb = PathBuilder::new();
                    pb.push_circle(px, py, radius);
                    if let Some(path) = pb.finish() {
                        pixmap.fill_path(
                            &path,
                            &paint,
                            tiny_skia::FillRule::Winding,
                            Transform::identity(),
                            None,
                        );
                    }
                }

                // 6. Blit only when something actually changed
                let _ = self.conn.put_image(
                    ImageFormat::Z_PIXMAP,
                    self.window,
                    self.gc,
                    self.width,
                    self.height,
                    0,
                    0,
                    0,
                    self.depth,
                    pixmap.data(),
                );
                let _ = self.conn.flush();
            } else {
                // When toggled off: clear once, then sleep heavily
                if was_enabled {
                    pixmap.fill(Color::TRANSPARENT);
                    let _ = self.conn.put_image(
                        ImageFormat::Z_PIXMAP,
                        self.window,
                        self.gc,
                        self.width,
                        self.height,
                        0,
                        0,
                        0,
                        self.depth,
                        pixmap.data(),
                    );
                    let _ = self.conn.flush();
                    last_offset_x = f32::NAN;
                    last_offset_y = f32::NAN;
                    was_enabled = false;
                }
                thread::sleep(Duration::from_millis(100));
                continue;
            }

            let elapsed = start.elapsed();
            if elapsed < target_frame_time {
                thread::sleep(target_frame_time - elapsed);
            }
        }
    }
}
