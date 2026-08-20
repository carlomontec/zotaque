mod filter;
mod ipc;
mod overlay;
mod sensor;

use std::sync::atomic::AtomicBool;
use std::sync::{Arc, Mutex};

use filter::FilterConfig;
use ipc::start_ipc_server;
use overlay::OverlayWindow;

fn main() {
    println!("=== ZOTAQUE NATIVE GAMESCOPE OVERLAY ===");

    let enabled_flag = Arc::new(AtomicBool::new(true)); // Enabled by default on startup
    let config = Arc::new(Mutex::new(FilterConfig::default()));

    // 1. Start Unix Socket IPC Server (/tmp/zotaque.sock)
    start_ipc_server(Arc::clone(&enabled_flag), Arc::clone(&config));

    // 2. Initialize 32-bit Transparent X11 Window in Gamescope
    match OverlayWindow::new() {
        Ok(overlay) => {
            println!("[Zotaque] Overlay window created successfully.");
            overlay.run_render_loop(enabled_flag, config);
        }
        Err(e) => {
            eprintln!("[Zotaque] Failed to create Gamescope overlay window: {}", e);
            std::process::exit(1);
        }
    }
}
