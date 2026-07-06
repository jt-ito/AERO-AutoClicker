use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use std::thread;
use std::time::Duration;

use tauri::Emitter;
use windows::Win32::UI::Input::KeyboardAndMouse::{
    SendInput, INPUT, INPUT_0, INPUT_MOUSE, MOUSEINPUT, MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP,
    MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP,
    INPUT_KEYBOARD, KEYBDINPUT, KEYEVENTF_KEYUP, KEYBD_EVENT_FLAGS, VIRTUAL_KEY
};

use crate::macro_recorder::MacroMove;

pub struct MacroPlayer {
    pub playing: Arc<AtomicBool>,
}

impl MacroPlayer {
    pub fn new() -> Self {
        Self {
            playing: Arc::new(AtomicBool::new(false)),
        }
    }

    pub fn start(&self, app: tauri::AppHandle, moves: Vec<MacroMove>) {
        if self.playing.load(Ordering::SeqCst) {
            return;
        }
        self.playing.store(true, Ordering::SeqCst);
        let playing = Arc::clone(&self.playing);

        thread::spawn(move || {
            for m in moves {
                if !playing.load(Ordering::SeqCst) {
                    break;
                }

                match m.r#type.as_str() {
                    "Delay" => {
                        if let Some(ms) = m.ms {
                            // Sleep in small increments to allow for quick cancellation
                            let total_sleep = Duration::from_millis(ms);
                            let start = std::time::Instant::now();
                            while start.elapsed() < total_sleep {
                                if !playing.load(Ordering::SeqCst) {
                                    break;
                                }
                                thread::sleep(Duration::from_millis(5));
                            }
                        }
                    }
                    "Click" | "RightClick" => {
                        if let (Some(x), Some(y)) = (m.x, m.y) {
                            unsafe {
                                windows::Win32::UI::WindowsAndMessaging::SetCursorPos(x, y).ok();
                                
                                let (down_flag, up_flag) = if m.r#type == "Click" {
                                    (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP)
                                } else {
                                    (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP)
                                };

                                let inputs = [
                                    INPUT {
                                        r#type: INPUT_MOUSE,
                                        Anonymous: INPUT_0 {
                                            mi: MOUSEINPUT { dx: 0, dy: 0, mouseData: 0, dwFlags: down_flag, time: 0, dwExtraInfo: 0 }
                                        }
                                    },
                                    INPUT {
                                        r#type: INPUT_MOUSE,
                                        Anonymous: INPUT_0 {
                                            mi: MOUSEINPUT { dx: 0, dy: 0, mouseData: 0, dwFlags: up_flag, time: 0, dwExtraInfo: 0 }
                                        }
                                    }
                                ];
                                SendInput(&inputs, std::mem::size_of::<INPUT>() as i32);
                            }
                        }
                    }
                    "KeyDown" | "KeyUp" => {
                        if let Some(vk) = m.key {
                            unsafe {
                                let flags = if m.r#type == "KeyUp" { KEYEVENTF_KEYUP } else { KEYBD_EVENT_FLAGS(0) };
                                let input = INPUT {
                                    r#type: INPUT_KEYBOARD,
                                    Anonymous: INPUT_0 {
                                        ki: KEYBDINPUT {
                                            wVk: VIRTUAL_KEY(vk as u16),
                                            wScan: 0,
                                            dwFlags: flags,
                                            time: 0,
                                            dwExtraInfo: 0,
                                        }
                                    }
                                };
                                SendInput(&[input], std::mem::size_of::<INPUT>() as i32);
                            }
                        }
                    }
                    _ => {}
                }
            }

            playing.store(false, Ordering::SeqCst);
            let _ = app.emit("macro-playback-stopped", ());
        });
    }

    pub fn stop(&self) {
        self.playing.store(false, Ordering::SeqCst);
    }
}
