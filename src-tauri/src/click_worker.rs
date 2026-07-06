use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::thread;
use std::time::{Duration, Instant};

use windows::Win32::Foundation::{HWND, LPARAM, WPARAM};
use windows::Win32::UI::WindowsAndMessaging::{
    PostMessageW, WM_LBUTTONDOWN, WM_LBUTTONUP, WM_LBUTTONDBLCLK, WM_MOUSEMOVE, IsWindow,
};
use windows::Win32::System::SystemServices::MK_LBUTTON;
use windows::Win32::UI::Input::KeyboardAndMouse::{
    SendInput, INPUT, INPUT_0, INPUT_MOUSE, MOUSEINPUT, MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP,
};

use crate::win32_utils::{client_to_screen, get_foreground_window};
use tauri::Emitter;

pub struct ClickWorker {
    pub running: Arc<AtomicBool>,
}

impl ClickWorker {
    pub fn new() -> Self {
        Self {
            running: Arc::new(AtomicBool::new(false)),
        }
    }

    pub fn start(&self, app: tauri::AppHandle, hwnd: Option<isize>, interval_ms: u64, double: bool, x: Option<i32>, y: Option<i32>, background_mode: bool) {
        if self.running.load(Ordering::SeqCst) {
            return;
        }
        self.running.store(true, Ordering::SeqCst);
        let running = Arc::clone(&self.running);

        thread::spawn(move || {
            let interval = Duration::from_millis(interval_ms);
            let mut next_time = Instant::now();

            let target_info = if let Some(h) = hwnd {
                let hwnd_val = HWND(h as _);
                let (cx, cy) = match (x, y) {
                    (Some(cx), Some(cy)) => (cx, cy),
                    _ => crate::win32_utils::client_center(h),
                };
                let (sx, sy) = client_to_screen(h, cx, cy);
                let lparam = LPARAM(((cy as u32) << 16 | (cx as u32 & 0xFFFF)) as isize);
                Some((hwnd_val, sx, sy, lparam, h))
            } else {
                None
            };

            let mut using_system_mouse = target_info.is_none();

            while running.load(Ordering::SeqCst) {
                if let Some((hwnd_val, _, _, _, _)) = target_info {
                    if !unsafe { IsWindow(Some(hwnd_val)) }.as_bool() {
                        running.store(false, Ordering::SeqCst);
                        let _ = app.emit("clicker-stopped", ());
                        break;
                    }
                }

                let now = Instant::now();
                if now >= next_time {
                    if let Some((hwnd_val, sx, sy, lparam, h)) = target_info {
                        if background_mode && !using_system_mouse {
                            // Try PostMessage
                            unsafe {
                                let _ = PostMessageW(Some(hwnd_val), WM_MOUSEMOVE, WPARAM(0), lparam);
                                let res1 = PostMessageW(Some(hwnd_val), WM_LBUTTONDOWN, WPARAM(MK_LBUTTON.0 as _), lparam);
                                let res2 = PostMessageW(Some(hwnd_val), WM_LBUTTONUP, WPARAM(0), lparam);
                                
                                if res1.is_err() || res2.is_err() {
                                    // Fallback if it fails
                                    if get_foreground_window() == h {
                                        using_system_mouse = true;
                                    }
                                } else if double {
                                    let _ = PostMessageW(Some(hwnd_val), WM_LBUTTONDBLCLK, WPARAM(MK_LBUTTON.0 as _), lparam);
                                }
                            }
                        } 
                        
                        if !background_mode || using_system_mouse {
                            // System mouse (SendInput)
                            unsafe {
                                windows::Win32::UI::WindowsAndMessaging::SetCursorPos(sx, sy).ok();
                                
                                let inputs = [
                                    INPUT {
                                        r#type: INPUT_MOUSE,
                                        Anonymous: INPUT_0 {
                                            mi: MOUSEINPUT { dx: 0, dy: 0, mouseData: 0, dwFlags: MOUSEEVENTF_LEFTDOWN, time: 0, dwExtraInfo: 0 }
                                        }
                                    },
                                    INPUT {
                                        r#type: INPUT_MOUSE,
                                        Anonymous: INPUT_0 {
                                            mi: MOUSEINPUT { dx: 0, dy: 0, mouseData: 0, dwFlags: MOUSEEVENTF_LEFTUP, time: 0, dwExtraInfo: 0 }
                                        }
                                    }
                                ];
                                SendInput(&inputs, std::mem::size_of::<INPUT>() as i32);

                                if double {
                                    thread::sleep(Duration::from_millis(20));
                                    SendInput(&inputs, std::mem::size_of::<INPUT>() as i32);
                                }
                            }
                        }
                    } else {
                        // NO TARGET WINDOW, Just click at current position
                        unsafe {
                            let inputs = [
                                INPUT {
                                    r#type: INPUT_MOUSE,
                                    Anonymous: INPUT_0 {
                                        mi: MOUSEINPUT { dx: 0, dy: 0, mouseData: 0, dwFlags: MOUSEEVENTF_LEFTDOWN, time: 0, dwExtraInfo: 0 }
                                    }
                                },
                                INPUT {
                                    r#type: INPUT_MOUSE,
                                    Anonymous: INPUT_0 {
                                        mi: MOUSEINPUT { dx: 0, dy: 0, mouseData: 0, dwFlags: MOUSEEVENTF_LEFTUP, time: 0, dwExtraInfo: 0 }
                                    }
                                }
                            ];
                            SendInput(&inputs, std::mem::size_of::<INPUT>() as i32);

                            if double {
                                thread::sleep(Duration::from_millis(20));
                                SendInput(&inputs, std::mem::size_of::<INPUT>() as i32);
                            }
                        }
                    }

                    // Ensure a minimum interval of 1ms to prevent system freeze
                    let actual_interval = std::cmp::max(Duration::from_millis(1), interval);
                    next_time = now + actual_interval;
                } else {
                    let remaining = next_time - now;
                    if remaining > Duration::from_millis(2) {
                        thread::sleep(remaining - Duration::from_millis(1));
                    } else {
                        std::hint::spin_loop();
                    }
                }
            }
        });
    }

    pub fn stop(&self) {
        self.running.store(false, Ordering::SeqCst);
    }
}
