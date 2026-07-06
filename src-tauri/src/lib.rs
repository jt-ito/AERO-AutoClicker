mod win32_utils;
mod click_worker;
mod macro_recorder;
mod macro_player;

use tauri::{State, Emitter};
use serde::Serialize;
use click_worker::ClickWorker;
use macro_recorder::{MacroRecorder, MacroMove};
use macro_player::MacroPlayer;

#[derive(Serialize)]
struct WindowInfo {
    hwnd: isize,
    title: String,
}

struct AppState {
    worker: ClickWorker,
    macro_recorder: MacroRecorder,
    macro_player: MacroPlayer,
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
    hwnd: Option<isize>,
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
    unsafe {
        let _ = windows::Win32::UI::WindowsAndMessaging::SetForegroundWindow(
            windows::Win32::Foundation::HWND(hwnd as _)
        );
    }
    
    win32_utils::wait_for_left_click();
    
    let (sx, sy) = win32_utils::get_cursor_pos();
    let (cx, cy) = win32_utils::screen_to_client(hwnd, sx, sy);
    
    Ok((std::cmp::max(0, cx), std::cmp::max(0, cy)))
}

#[tauri::command]
fn register_hotkeys(app: tauri::AppHandle, clicker: String, macro_record: String, macro_play: String) -> Result<(), String> {
    use tauri_plugin_global_shortcut::{GlobalShortcutExt, Shortcut, ShortcutState};
    use std::str::FromStr;
    
    let manager = app.global_shortcut();
    let _ = manager.unregister_all();
    
    if let Ok(shortcut) = Shortcut::from_str(&clicker) {
        let _ = manager.on_shortcut(shortcut, move |app, _shortcut, event| {
            if event.state() == ShortcutState::Released { return; }
            let _ = app.emit("toggle-clicker", ());
        });
    }

    if let Ok(shortcut) = Shortcut::from_str(&macro_record) {
        let _ = manager.on_shortcut(shortcut, move |app, _shortcut, event| {
            if event.state() == ShortcutState::Released { return; }
            let _ = app.emit("toggle-macro-record", ());
        });
    }

    if let Ok(shortcut) = Shortcut::from_str(&macro_play) {
        let _ = manager.on_shortcut(shortcut, move |app, _shortcut, event| {
            if event.state() == ShortcutState::Released { return; }
            let _ = app.emit("toggle-macro-play", ());
        });
    }
    
    Ok(())
}

#[tauri::command]
fn start_macro_recording(app: tauri::AppHandle, state: State<'_, AppState>, hwnd: Option<isize>) -> Result<(), String> {
    if let Some(h) = hwnd {
        unsafe {
            let _ = windows::Win32::UI::WindowsAndMessaging::SetForegroundWindow(
                windows::Win32::Foundation::HWND(h as _)
            );
        }
    }
    state.macro_recorder.start(app);
    Ok(())
}

#[tauri::command]
fn stop_macro_recording(state: State<'_, AppState>) -> Result<(), String> {
    state.macro_recorder.stop();
    Ok(())
}

#[tauri::command]
fn start_macro_playback(app: tauri::AppHandle, state: State<'_, AppState>, moves: Vec<MacroMove>, hwnd: Option<isize>) -> Result<(), String> {
    if let Some(h) = hwnd {
        unsafe {
            let _ = windows::Win32::UI::WindowsAndMessaging::SetForegroundWindow(
                windows::Win32::Foundation::HWND(h as _)
            );
        }
    }
    state.macro_player.start(app, moves);
    Ok(())
}

#[tauri::command]
fn stop_macro_playback(state: State<'_, AppState>) -> Result<(), String> {
    state.macro_player.stop();
    Ok(())
}

#[tauri::command]
fn open_test_page(app: tauri::AppHandle) -> Result<(), String> {
    use tauri::Manager;
    
    println!("open_test_page called");
    if let Some(w) = app.get_webview_window("test-page") {
        println!("test-page already exists, focusing");
        let _ = w.set_focus();
        return Ok(());
    }

    let builder = tauri::WebviewWindowBuilder::new(
        &app,
        "test-page",
        tauri::WebviewUrl::App("test.html".into())
    )
    .title("Autoclicker Test Page")
    .inner_size(800.0, 600.0)
    .resizable(true);

    println!("building webview...");
    match builder.build() {
        Ok(webview) => {
            println!("webview built successfully");
            let app_clone = app.clone();
            webview.on_window_event(move |event| {
                if let tauri::WindowEvent::Destroyed = event {
                    println!("test-page window destroyed");
                    let state = app_clone.state::<AppState>();
                    state.worker.stop();
                    let _ = app_clone.emit("clicker-stopped", ());
                }
            });
        }
        Err(e) => {
            println!("ERROR building webview: {:?}", e);
            return Err(e.to_string());
        }
    }

    println!("open_test_page returning");
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(AppState {
            worker: ClickWorker::new(),
            macro_recorder: MacroRecorder::new(),
            macro_player: MacroPlayer::new(),
        })
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            get_windows,
            start_clicking,
            stop_clicking,
            pick_coordinates,
            register_hotkeys,
            start_macro_recording,
            stop_macro_recording,
            start_macro_playback,
            stop_macro_playback,
            open_test_page,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
