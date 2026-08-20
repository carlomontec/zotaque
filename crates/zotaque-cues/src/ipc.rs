use serde::{Deserialize, Serialize};
use std::fs;
use std::io::{BufRead, BufReader, Write};
use std::os::unix::net::{UnixListener, UnixStream};
use std::path::Path;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;

use crate::filter::FilterConfig;

pub const SOCKET_PATH: &str = "/tmp/zotaque.sock";

#[derive(Deserialize, Debug)]
#[serde(tag = "cmd")]
pub enum IpcRequest {
    #[serde(rename = "enable")]
    Enable,
    #[serde(rename = "disable")]
    Disable,
    #[serde(rename = "toggle")]
    Toggle,
    #[serde(rename = "set_config")]
    SetConfig {
        tilt_sensitivity: Option<f32>,
        dynamic_sensitivity: Option<f32>,
        smoothing: Option<f32>,
        max_shift_px: Option<f32>,
        dot_radius: Option<f32>,
        dot_color_hex: Option<String>,
    },
    #[serde(rename = "get_status")]
    GetStatus,
}

#[derive(Serialize, Debug)]
pub struct IpcResponse {
    pub enabled: bool,
    pub status: String,
}

pub fn start_ipc_server(
    enabled_flag: Arc<AtomicBool>,
    config_mutex: Arc<Mutex<FilterConfig>>,
) {
    if Path::new(SOCKET_PATH).exists() {
        let _ = fs::remove_file(SOCKET_PATH);
    }

    let listener = match UnixListener::bind(SOCKET_PATH) {
        Ok(l) => l,
        Err(e) => {
            eprintln!("[IPC] Failed to bind Unix socket at {}: {}", SOCKET_PATH, e);
            return;
        }
    };

    // Make socket accessible to deck/user
    let _ = fs::set_permissions(SOCKET_PATH, std::os::unix::fs::PermissionsExt::from_mode(0o777));

    thread::spawn(move || {
        for stream in listener.incoming() {
            if let Ok(mut stream) = stream {
                handle_client(&mut stream, &enabled_flag, &config_mutex);
            }
        }
    });
}

fn parse_hex_color(hex: &str) -> (u8, u8, u8, u8) {
    let clean = hex.trim_start_matches('#');
    if clean.len() >= 6 {
        if let (Ok(r), Ok(g), Ok(b)) = (
            u8::from_str_radix(&clean[0..2], 16),
            u8::from_str_radix(&clean[2..4], 16),
            u8::from_str_radix(&clean[4..6], 16),
        ) {
            return (r, g, b, 230);
        }
    }
    (0, 229, 255, 230)
}

fn handle_client(
    stream: &mut UnixStream,
    enabled_flag: &Arc<AtomicBool>,
    config_mutex: &Arc<Mutex<FilterConfig>>,
) {
    let mut reader = BufReader::new(stream.try_clone().unwrap());
    let mut line = String::new();
    if reader.read_line(&mut line).is_ok() {
        if let Ok(req) = serde_json::from_str::<IpcRequest>(&line) {
            match req {
                IpcRequest::Enable => {
                    enabled_flag.store(true, Ordering::SeqCst);
                }
                IpcRequest::Disable => {
                    enabled_flag.store(false, Ordering::SeqCst);
                }
                IpcRequest::Toggle => {
                    let curr = enabled_flag.load(Ordering::SeqCst);
                    enabled_flag.store(!curr, Ordering::SeqCst);
                }
                IpcRequest::SetConfig {
                    tilt_sensitivity,
                    dynamic_sensitivity,
                    smoothing,
                    max_shift_px,
                    dot_radius,
                    dot_color_hex,
                } => {
                    if let Ok(mut cfg) = config_mutex.lock() {
                        if let Some(v) = tilt_sensitivity { cfg.tilt_sensitivity = v; }
                        if let Some(v) = dynamic_sensitivity { cfg.dynamic_sensitivity = v; }
                        if let Some(v) = smoothing { cfg.smoothing = v; }
                        if let Some(v) = max_shift_px { cfg.max_shift_px = v; }
                        if let Some(v) = dot_radius { cfg.dot_radius = v; }
                        if let Some(hex) = dot_color_hex { cfg.dot_color_rgba = parse_hex_color(&hex); }
                    }
                }
                IpcRequest::GetStatus => {}
            }
        }

        let resp = IpcResponse {
            enabled: enabled_flag.load(Ordering::SeqCst),
            status: "ok".to_string(),
        };
        if let Ok(json) = serde_json::to_string(&resp) {
            let _ = writeln!(stream, "{}", json);
        }
    }
}
