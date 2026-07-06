use std::sync::{Arc, Mutex, OnceLock};
use std::sync::atomic::{AtomicBool, Ordering};
use std::thread;
use std::time::Instant;
use serde::{Serialize, Deserialize};
use tauri::Emitter;

use windows::Win32::Foundation::{LPARAM, LRESULT, WPARAM, HINSTANCE};
use windows::Win32::UI::WindowsAndMessaging::{
    CallNextHookEx, SetWindowsHookExW, UnhookWindowsHookEx,
    HHOOK, MSG, WH_MOUSE_LL, WM_LBUTTONDOWN, WM_RBUTTONDOWN,
    MSLLHOOKSTRUCT,
};
use windows::Win32::System::LibraryLoader::GetModuleHandleW;
use windows::Win32::UI::Input::KeyboardAndMouse::GetAsyncKeyState;

#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct MacroMove {
    pub r#type: String,
    pub ms: Option<u64>,
    pub x: Option<i32>,
    pub y: Option<i32>,
    pub key: Option<u32>,
}

static RECORDER_STATE: OnceLock<Mutex<RecorderState>> = OnceLock::new();

struct RecorderState {
    app: Option<tauri::AppHandle>,
    last_action_time: Option<Instant>,
    mouse_hook: Option<isize>,
    thread_id: Option<u32>,
}

pub struct MacroRecorder {
    pub recording: Arc<AtomicBool>,
}

impl MacroRecorder {
    pub fn new() -> Self {
        let _ = RECORDER_STATE.get_or_init(|| Mutex::new(RecorderState {
            app: None,
            last_action_time: None,
            mouse_hook: None,
            thread_id: None,
        }));
        Self {
            recording: Arc::new(AtomicBool::new(false)),
        }
    }

    pub fn start(&self, app: tauri::AppHandle) {
        if self.recording.load(Ordering::SeqCst) {
            return;
        }
        self.recording.store(true, Ordering::SeqCst);

        let mut state = RECORDER_STATE.get().unwrap().lock().unwrap();
        state.app = Some(app.clone());
        state.last_action_time = Some(Instant::now());
        
        let (tx, rx) = std::sync::mpsc::channel();
        
        // MOUSE HOOK THREAD
        thread::spawn(move || {
            let thread_id = unsafe { windows::Win32::System::Threading::GetCurrentThreadId() };
            tx.send(thread_id).unwrap();
            
            let mouse_hook = unsafe {
                let module = GetModuleHandleW(None).unwrap_or_default();
                let hinst = HINSTANCE(module.0);
                SetWindowsHookExW(
                    WH_MOUSE_LL,
                    Some(mouse_hook_callback),
                    Some(hinst),
                    0
                ).unwrap()
            };

            {
                let mut state = RECORDER_STATE.get().unwrap().lock().unwrap();
                state.mouse_hook = Some(mouse_hook.0 as isize);
            }
            
            let mut msg = MSG::default();
            unsafe {
                while windows::Win32::UI::WindowsAndMessaging::GetMessageW(&mut msg, None, 0, 0).into() {
                    let _ = windows::Win32::UI::WindowsAndMessaging::TranslateMessage(&msg);
                    let _ = windows::Win32::UI::WindowsAndMessaging::DispatchMessageW(&msg);
                }
                
                let _ = UnhookWindowsHookEx(mouse_hook);
            }
        });
        
        state.thread_id = Some(rx.recv().unwrap());
        
        // KEYBOARD POLLING THREAD
        let recording_for_kbd = Arc::clone(&self.recording);
        let app_for_kbd = app.clone();
        thread::spawn(move || {
            let mut last_state = [false; 256];
            while recording_for_kbd.load(Ordering::SeqCst) {
                for vk in 8..=254 { // skip mouse buttons
                    let state_val = unsafe { GetAsyncKeyState(vk) };
                    let is_down = (state_val as u16 & 0x8000) != 0;
                    
                    if is_down != last_state[vk as usize] {
                        last_state[vk as usize] = is_down;
                        
                        if let Some(state_mutex) = RECORDER_STATE.get() {
                            if let Ok(mut state) = state_mutex.lock() {
                                if let Some(last_time) = state.last_action_time {
                                    let now = Instant::now();
                                    let elapsed = now.duration_since(last_time).as_millis() as u64;
                                    
                                    if elapsed > 10 {
                                        let delay_move = MacroMove {
                                            r#type: "Delay".to_string(),
                                            ms: Some(elapsed),
                                            x: None,
                                            y: None,
                                            key: None,
                                        };
                                        let _ = app_for_kbd.emit("macro-move-recorded", delay_move);
                                    }
                                    
                                    let event_type = if is_down { "KeyDown" } else { "KeyUp" };
                                    let key_move = MacroMove {
                                        r#type: event_type.to_string(),
                                        ms: None,
                                        x: None,
                                        y: None,
                                        key: Some(vk as u32),
                                    };
                                    let _ = app_for_kbd.emit("macro-move-recorded", key_move);
                                    
                                    state.last_action_time = Some(now);
                                }
                            }
                        }
                    }
                }
                thread::sleep(std::time::Duration::from_millis(10));
            }
        });
    }

    pub fn stop(&self) {
        if !self.recording.load(Ordering::SeqCst) {
            return;
        }
        self.recording.store(false, Ordering::SeqCst);
        
        let mut state = RECORDER_STATE.get().unwrap().lock().unwrap();
        if let Some(tid) = state.thread_id {
            unsafe {
                let _ = windows::Win32::UI::WindowsAndMessaging::PostThreadMessageW(tid, windows::Win32::UI::WindowsAndMessaging::WM_QUIT, WPARAM(0), LPARAM(0));
            }
        }
        state.app = None;
        state.mouse_hook = None;
        state.thread_id = None;
    }
}

unsafe extern "system" fn mouse_hook_callback(ncode: i32, wparam: WPARAM, lparam: LPARAM) -> LRESULT {
    if ncode >= 0 {
        let wp = wparam.0 as u32;
        if wp == WM_LBUTTONDOWN || wp == WM_RBUTTONDOWN {
            let hook_struct = *(lparam.0 as *const MSLLHOOKSTRUCT);
            
            if let Some(state_mutex) = RECORDER_STATE.get() {
                if let Ok(mut state) = state_mutex.try_lock() {
                    if let (Some(app), Some(last_time)) = (state.app.as_ref(), state.last_action_time) {
                        let now = Instant::now();
                        let elapsed = now.duration_since(last_time).as_millis() as u64;
                        
                        if elapsed > 10 {
                            let delay_move = MacroMove {
                                r#type: "Delay".to_string(),
                                ms: Some(elapsed),
                                x: None,
                                y: None,
                                key: None,
                            };
                            let _ = app.emit("macro-move-recorded", delay_move);
                        }
                        
                        let click_type = if wp == WM_LBUTTONDOWN { "Click" } else { "RightClick" };
                        let click_move = MacroMove {
                            r#type: click_type.to_string(),
                            ms: None,
                            x: Some(hook_struct.pt.x),
                            y: Some(hook_struct.pt.y),
                            key: None,
                        };
                        let _ = app.emit("macro-move-recorded", click_move);
                        
                        state.last_action_time = Some(now);
                    }
                }
            }
        }
    }
    
    let hook = {
        let state_mutex = RECORDER_STATE.get().unwrap();
        if let Ok(state) = state_mutex.try_lock() {
            state.mouse_hook.map(|h| HHOOK(h as _))
        } else {
            None
        }
    };
    
    if let Some(h) = hook {
        CallNextHookEx(Some(h), ncode, wparam, lparam)
    } else {
        LRESULT(0)
    }
}
