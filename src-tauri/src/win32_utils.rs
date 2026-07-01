use std::ffi::OsString;
use std::os::windows::ffi::OsStringExt;
use windows::core::BOOL;
use windows::Win32::Foundation::{HWND, LPARAM, POINT, RECT};
use windows::Win32::UI::WindowsAndMessaging::{
    EnumWindows, GetClientRect, GetForegroundWindow, GetParent, GetWindowTextLengthW, GetWindowTextW,
    IsWindowVisible, WindowFromPoint,
};
use windows::Win32::Graphics::Gdi::{ClientToScreen, ScreenToClient};
use windows::Win32::UI::Input::KeyboardAndMouse::GetAsyncKeyState;

pub fn get_window_list() -> Vec<(isize, String)> {
    let mut windows: Vec<(isize, String)> = Vec::new();
    
    unsafe extern "system" fn enum_window_callback(hwnd: HWND, lparam: LPARAM) -> BOOL {
        if IsWindowVisible(hwnd).as_bool() {
            let length = GetWindowTextLengthW(hwnd);
            if length > 0 {
                let mut buffer = vec![0u16; (length + 1) as usize];
                GetWindowTextW(hwnd, &mut buffer);
                let text = OsString::from_wide(&buffer[..length as usize])
                    .into_string()
                    .unwrap_or_else(|_| String::new());
                if !text.is_empty() {
                    let vec_ptr = lparam.0 as *mut Vec<(isize, String)>;
                    (*vec_ptr).push((hwnd.0 as isize, text));
                }
            }
        }
        BOOL(1)
    }

    unsafe {
        let lparam = LPARAM(&mut windows as *mut _ as isize);
        let _ = EnumWindows(Some(enum_window_callback), lparam);
    }
    windows
}

pub fn client_center(hwnd: isize) -> (i32, i32) {
    let hwnd = HWND(hwnd as _);
    let mut rect = RECT::default();
    unsafe {
        let _ = GetClientRect(hwnd, &mut rect);
    }
    let x = (rect.right - rect.left) / 2;
    let y = (rect.bottom - rect.top) / 2;
    (x, y)
}

pub fn get_foreground_window() -> isize {
    unsafe { GetForegroundWindow().0 as isize }
}

#[allow(dead_code)]
pub fn window_from_point(x: i32, y: i32) -> isize {
    unsafe { WindowFromPoint(POINT { x, y }).0 as isize }
}

#[allow(dead_code)]
pub fn get_parent(hwnd: isize) -> isize {
    unsafe { GetParent(HWND(hwnd as _)).map(|h| h.0 as isize).unwrap_or(0) }
}

pub fn client_to_screen(hwnd: isize, x: i32, y: i32) -> (i32, i32) {
    let mut pt = POINT { x, y };
    unsafe {
        let _ = ClientToScreen(HWND(hwnd as _), &mut pt);
    }
    (pt.x, pt.y)
}

pub fn wait_for_left_click() {
    unsafe {
        // Clear state
        GetAsyncKeyState(0x01); // VK_LBUTTON = 0x01
        loop {
            let state = GetAsyncKeyState(0x01);
            if (state as u16) & 0x8000 != 0 {
                break;
            }
            std::thread::sleep(std::time::Duration::from_millis(10));
        }
    }
}

pub fn get_cursor_pos() -> (i32, i32) {
    let mut pt = POINT::default();
    unsafe {
        let _ = windows::Win32::UI::WindowsAndMessaging::GetCursorPos(&mut pt);
    }
    (pt.x, pt.y)
}

pub fn screen_to_client(hwnd: isize, x: i32, y: i32) -> (i32, i32) {
    let mut pt = POINT { x, y };
    unsafe {
        let _ = ScreenToClient(HWND(hwnd as _), &mut pt);
    }
    (pt.x, pt.y)
}
