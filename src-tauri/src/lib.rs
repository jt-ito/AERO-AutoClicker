mod win32_utils;
mod click_worker;

use tauri::{State, Emitter};
use serde::Serialize;
use click_worker::ClickWorker;

#[derive(Serialize)]
struct WindowInfo {
    hwnd: isize,
    title: String,
}

struct AppState {
    worker: ClickWorker,
}

#[tauri::command]
fn get_windows() -> Vec<WindowInfo> {
    win32_utils::get_window_list()
        .into_iter()
        .map(|(hwnd, title)| WindowInfo { hwnd, title })
        .collect()
}

#[tauri::command]
fn start_clicking(
    app: tauri::AppHandle,
    state: State<'_, AppState>,
    hwnd: isize,
    interval_ms: u64,
    double: bool,
    x: Option<i32>,
    y: Option<i32>,
    background_mode: bool,
) -> Result<(), String> {
    state.worker.start(app, hwnd, interval_ms, double, x, y, background_mode);
    Ok(())
}

#[tauri::command]
fn stop_clicking(state: State<'_, AppState>) -> Result<(), String> {
    state.worker.stop();
    Ok(())
}

#[tauri::command]
async fn pick_coordinates(hwnd: isize) -> Result<(i32, i32), String> {
    // We bring the target to the foreground so the user can easily click it.
    unsafe {
        let _ = windows::Win32::UI::WindowsAndMessaging::SetForegroundWindow(
            windows::Win32::Foundation::HWND(hwnd as _)
        );
    }
    
    // Wait for the left click
    win32_utils::wait_for_left_click();
    
    let (sx, sy) = win32_utils::get_cursor_pos();
    let (cx, cy) = win32_utils::screen_to_client(hwnd, sx, sy);
    
    // Return relative coordinates, >= 0
    Ok((std::cmp::max(0, cx), std::cmp::max(0, cy)))
}

#[tauri::command]
fn register_hotkey(app: tauri::AppHandle, hotkey: String) -> Result<(), String> {
    use tauri_plugin_global_shortcut::{GlobalShortcutExt, Shortcut, ShortcutState};
    use std::str::FromStr;
    
    let manager = app.global_shortcut();
    let _ = manager.unregister_all();
    
    let shortcut = Shortcut::from_str(&hotkey).map_err(|e| e.to_string())?;
    
    manager.on_shortcut(shortcut, move |app, _shortcut, event| {
        if event.state() == ShortcutState::Released {
            return;
        }
        let _ = app.emit("toggle-clicker", ());
    }).map_err(|e| e.to_string())?;
    
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(AppState {
            worker: ClickWorker::new(),
        })
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            get_windows,
            start_clicking,
            stop_clicking,
            pick_coordinates,
            register_hotkey
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
