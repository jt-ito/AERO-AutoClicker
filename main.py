import sys
import time
import threading
from functools import partial

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QSpinBox,
    QCheckBox,
    QSlider,
    QFrame,
    QMessageBox,
)
from PySide6.QtCore import Qt, QTimer, QSettings, QPoint
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import QObject, QEvent
from PySide6.QtWidgets import QGraphicsDropShadowEffect

import ctypes
from ctypes import wintypes
import os

try:
    import win32gui
    import win32con
    import win32api
except Exception as e:
    win32gui = None
    win32con = None
    win32api = None


def list_windows():
    """Return list of (hwnd, title) for visible top-level windows."""
    res = []
    if win32gui is None:
        return res

    def enum_proc(hwnd, lparam):
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
            title = win32gui.GetWindowText(hwnd)
            res.append((hwnd, title))
        return True

    win32gui.EnumWindows(enum_proc, None)
    return res


def client_center(hwnd):
    rc = win32gui.GetClientRect(hwnd)
    x = (rc[2] - rc[0]) // 2
    y = (rc[3] - rc[1]) // 2
    return x, y


class ClickWorker(threading.Thread):
    def __init__(self, hwnd, interval_ms=100, double=False, stop_event=None):
        super().__init__()
        self.hwnd = hwnd
        # allow sub-second intervals; interval_ms is in milliseconds
        self.interval = max(0.001, float(interval_ms) / 1000.0)
        self.double = double
        self._stop = stop_event or threading.Event()
        self.offset = None
        self.use_system_mouse = True
        # if True, prefer PostMessage and only use system mouse as fallback
        self.background_mode = False
        # callback to notify main thread when fallback to system mouse occurs
        self.fallback_callback = None
        # whether we've already switched to system mouse due to fallback
        self._using_system_mouse = False
        # Optional fixed screen position (sx, sy) to use for system mouse clicks
        self._fixed_screen = None

    def set_offset(self, x, y):
        self.offset = (int(x), int(y))

    def set_use_system_mouse(self, enabled: bool):
        self.use_system_mouse = bool(enabled)

    def set_background_mode(self, enabled: bool, fallback_callback=None):
        self.background_mode = bool(enabled)
        self.fallback_callback = fallback_callback

    def set_fixed_screen(self, sx, sy):
        try:
            self._fixed_screen = (int(sx), int(sy))
        except Exception:
            self._fixed_screen = None

    def stop(self):
        self._stop.set()

    def post_click(self):
        if not self.hwnd:
            return
        # compute client coordinates and pack into lParam
        if self.offset:
            cx, cy = self.offset
        else:
            cx, cy = client_center(self.hwnd)

        # If background_mode is enabled and we have win32gui, try PostMessage first
        if self.background_mode and win32gui is not None and not self._using_system_mouse:
            try:
                lParam = (int(cy) << 16) | (int(cx) & 0xFFFF)
                # send a mouse-move first so the target control updates hover state,
                # then send down/up (and dblclick if requested)
                try:
                    win32gui.PostMessage(self.hwnd, win32con.WM_MOUSEMOVE, 0, lParam)
                except Exception:
                    pass
                win32gui.PostMessage(self.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
                win32gui.PostMessage(self.hwnd, win32con.WM_LBUTTONUP, 0, lParam)
                if self.double:
                    win32gui.PostMessage(self.hwnd, win32con.WM_LBUTTONDBLCLK, win32con.MK_LBUTTON, lParam)
                return
            except Exception:
                # if PostMessage failed, fall back to system mouse if allowed and target is foreground
                try:
                    fg = win32gui.GetForegroundWindow()
                except Exception:
                    fg = None
                if self.use_system_mouse and fg == self.hwnd:
                    # mark we've fallen back and notify
                    self._using_system_mouse = True
                    try:
                        if self.fallback_callback:
                            self.fallback_callback()
                    except Exception:
                        pass
                    # continue into system-mouse section
                else:
                    return

        if self.use_system_mouse and win32api is not None:
            # convert to screen coordinates
            try:
                # compute current screen coords from client coords each click so clicks remain
                # accurate if the target window moved or changed position
                sx, sy = win32gui.ClientToScreen(self.hwnd, (cx, cy))
            except Exception:
                # fallback to any fixed screen pos if set, else use client coords
                if getattr(self, '_fixed_screen', None) is not None:
                    sx, sy = self._fixed_screen
                else:
                    sx, sy = cx, cy
            try:
                prev = win32gui.GetCursorPos()
            except Exception:
                prev = None
            # Before moving the system cursor and clicking, ensure the target window
            # is still the foreground window and the window at the click point
            # belongs to the same top-level hwnd. If not, skip the click to avoid
            # interacting with other applications.
            try:
                fg = win32gui.GetForegroundWindow()
            except Exception:
                fg = None
            try:
                pt_hwnd = win32gui.WindowFromPoint((int(sx), int(sy)))
            except Exception:
                pt_hwnd = None
            top = pt_hwnd
            if top:
                try:
                    while True:
                        p = win32gui.GetParent(top)
                        if not p:
                            break
                        top = p
                except Exception:
                    pass
            if fg != self.hwnd or (top and top != self.hwnd):
                return
            try:
                win32api.SetCursorPos((int(sx), int(sy)))
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                if self.double:
                    time.sleep(0.02)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            except Exception:
                # fallback to PostMessage
                lParam = (int(cy) << 16) | (int(cx) & 0xFFFF)
                win32gui.PostMessage(self.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
                win32gui.PostMessage(self.hwnd, win32con.WM_LBUTTONUP, 0, lParam)
            finally:
                # Restore previous cursor position only if the user didn't move the mouse
                try:
                    if prev:
                        try:
                            cur = win32gui.GetCursorPos()
                            # if cursor is still at the click location (sx,sy) within small tolerance, restore
                            if abs(cur[0] - int(sx)) <= 1 and abs(cur[1] - int(sy)) <= 1:
                                win32api.SetCursorPos(prev)
                            else:
                                # user moved the mouse during clicking; do not override
                                pass
                        except Exception:
                            # if we cannot determine current pos, attempt to restore
                            try:
                                win32api.SetCursorPos(prev)
                            except Exception:
                                pass
                except Exception:
                    pass
        else:
            lParam = (int(cy) << 16) | (int(cx) & 0xFFFF)
            win32gui.PostMessage(self.hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lParam)
            win32gui.PostMessage(self.hwnd, win32con.WM_LBUTTONUP, 0, lParam)

    def run(self):
        # use a high-resolution timer for accurate short intervals
        next_time = time.perf_counter()
        while not self._stop.is_set():
            now = time.perf_counter()
            if now >= next_time:
                try:
                    self.post_click()
                    if self.double:
                        # small gap between double clicks
                        time.sleep(0.02)
                        self.post_click()
                except Exception:
                    pass
                next_time = now + self.interval
            else:
                remaining = next_time - now
                # sleep most of the remaining time, then busy-wait for precision
                if remaining > 0.005:
                    time.sleep(remaining - 0.002)
                else:
                    # busy-wait for very short remaining time
                    while time.perf_counter() < next_time:
                        pass


class HotkeyThread(threading.Thread):
    """Register a global hotkey (Ctrl+Shift+S) and set an Event when pressed.
    Uses ctypes to call RegisterHotKey and GetMessage loop in a background thread.
    """
    def __init__(self, event, mods=None, vk=ord("S")):
        super().__init__()
        self.event = event
        # avoid evaluating win32con constants at import time if pywin32 not available
        if mods is None:
            self.mods = (win32con.MOD_CONTROL | win32con.MOD_SHIFT) if win32con is not None else 0
        else:
            self.mods = mods
        self.vk = vk
        self._running = True
        self._id = 1
        self._tid = None

        import ctypes
        from ctypes import wintypes
        self._user32 = ctypes.windll.user32
        self._kernel32 = ctypes.windll.kernel32


    
    def run(self):
        # store this thread id for shutdown posting
        try:
            self._tid = self._kernel32.GetCurrentThreadId()
        except Exception:
            self._tid = None
        # Register hotkey for the current thread (no HWND)
        if not self._user32.RegisterHotKey(None, self._id, int(self.mods), int(self.vk)):
            return

        msg = wintypes.MSG()
        while self._running:
            # GetMessage blocks until a message arrives
            res = self._user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if res == 0:
                break
            if msg.message == win32con.WM_HOTKEY:
                # signal main thread
                try:
                    self.event.set()
                except Exception:
                    pass
            # Dispatch other messages normally
            self._user32.TranslateMessage(ctypes.byref(msg))
            self._user32.DispatchMessageW(ctypes.byref(msg))

        # Unregister on exit
        try:
            self._user32.UnregisterHotKey(None, self._id)
        except Exception:
            pass

    def shutdown(self):
        self._running = False
        try:
            tid = self._tid or self._kernel32.GetCurrentThreadId()
            # Post a quit message to unblock GetMessage running in hotkey thread
            if tid:
                self._user32.PostThreadMessageW(tid, win32con.WM_QUIT, 0, 0)
        except Exception:
            pass


class HoverShadowFilter(QObject):
    """Top-level event filter that applies a QGraphicsDropShadowEffect on enter and
    removes it on leave. Use `btn.installEventFilter(HoverShadowFilter())`."""
    def __init__(self, parent=None, radius=16, color=(31, 111, 235, 120)):
        super().__init__(parent)
        self._radius = radius
        self._color = color

    def eventFilter(self, obj, event):
        try:
            if event.type() == QEvent.Enter:
                effect = QGraphicsDropShadowEffect(obj)
                effect.setBlurRadius(self._radius)
                effect.setOffset(0, 8)
                r, g, b, a = self._color
                from PySide6.QtGui import QColor
                effect.setColor(QColor(r, g, b, a))
                obj.setGraphicsEffect(effect)
                return False
            elif event.type() == QEvent.Leave:
                try:
                    obj.setGraphicsEffect(None)
                except Exception:
                    pass
                return False
        except Exception:
            pass
        return super().eventFilter(obj, event)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AERO AutoClicker")
        self.setMinimumSize(420, 260)
        # Use a frameless window with a custom modern title bar
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        # load icon (works both in normal run and when bundled by PyInstaller)
        try:
            base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            self.base_path = base_path
            icon_path = os.path.join(base_path, 'assets', 'cursor_icon.svg')
            if os.path.exists(icon_path):
                self.app_icon = QIcon(icon_path)
                self.setWindowIcon(self.app_icon)
            else:
                self.app_icon = None
        except Exception:
            self.app_icon = None

        self.worker = None
        self.worker_stop = None
        self.click_x = None
        self.click_y = None
        self.hotkey_event = threading.Event()
        self.hotkey_thread = None

        self.dark_qss = """
        QFrame#content { background: #121212; color: #e0e0e0; border-bottom-left-radius: 8px; border-bottom-right-radius: 8px; border-top-left-radius: 0px; border-top-right-radius: 0px; }
        QComboBox, QSpinBox, QSlider { background: #1e1e1e; }
        QPushButton { background: #1f6feb; color: white; padding: 6px; border-radius: 6px; border: 1px solid rgba(0,0,0,0.15); }
        QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #58a6ff, stop:1 #2f84ff); border: 1px solid rgba(255,255,255,0.12); }
        QPushButton:pressed { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #155ab8, stop:1 #0f3f85); border: 1px solid rgba(0,0,0,0.25); }
        QPushButton:disabled { background: #374151; color: #9aa4b2; }
        QPushButton#stopBtn { background: #c53030; border: 1px solid rgba(0,0,0,0.2); }
        QPushButton#stopBtn:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff6b6b, stop:1 #e04b4b); border: 1px solid rgba(255,255,255,0.12); }
        QPushButton#stopBtn:pressed { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8b1414, stop:1 #5e0b0b); border: 1px solid rgba(0,0,0,0.3); }
        QCheckBox { padding: 4px; }
        /* outline-only white box for checkboxes */
        QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #ffffff; background: transparent; }
        QCheckBox::indicator:checked { background: #1f6feb; }
        QLabel#small { color: #a0a0a0; }
        /* title bar */
        QFrame#titleBar { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0f1724, stop:1 #111827); border-top-left-radius: 8px; border-top-right-radius: 8px; border-bottom-left-radius: 0px; border-bottom-right-radius: 0px; }
        QLabel#titleLbl { font-weight: 600; color: #e6eefc; }
        QPushButton#titleBtn { background: transparent; color: #cbd5e1; border: none; padding: 4px; border-radius: 4px; }
        QPushButton#titleBtn:hover { background: rgba(255,255,255,0.05); }
        QPushButton#closeBtn { background: transparent; color: #fca5a5; border: none; padding: 4px; border-radius: 4px; }
        QPushButton#closeBtn:hover { background: rgba(255,0,0,0.08); }
        """

        self.light_qss = """
        QFrame#content { background: #f6f7fb; color: #111827; border-bottom-left-radius: 8px; border-bottom-right-radius: 8px; border-top-left-radius: 0px; border-top-right-radius: 0px; }
        QPushButton { background: #2563eb; color: white; padding: 6px; border-radius: 6px; border: 1px solid rgba(0,0,0,0.08); }
        QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4a7ff8, stop:1 #2b6ef0); border: 1px solid rgba(255,255,255,0.08); }
        QPushButton:pressed { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #164fb0, stop:1 #0f3b86); border: 1px solid rgba(0,0,0,0.18); }
        QPushButton:disabled { background: #cbd5e1; color: #94a3b8; }
        QPushButton#stopBtn { background: #b91c1c; border: 1px solid rgba(0,0,0,0.12); }
        QPushButton#stopBtn:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff6b6b, stop:1 #d73f3f); border: 1px solid rgba(255,255,255,0.08); }
        QPushButton#stopBtn:pressed { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #7a1212, stop:1 #4f0a0a); border: 1px solid rgba(0,0,0,0.22); }
        QCheckBox { padding: 4px; }
        /* outline-only box for light theme (black border) */
        QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #000000; background: transparent; }
        QCheckBox::indicator:checked { background: #2563eb; }
        QLabel#small { color: #374151; }
        QFrame#titleBar { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ffffff, stop:1 #eef2ff); border-top-left-radius: 8px; border-top-right-radius: 8px; border-bottom-left-radius: 0px; border-bottom-right-radius: 0px; }
        QLabel#titleLbl { font-weight: 600; color: #0f1724; }
        QPushButton#titleBtn { background: transparent; color: #0f1724; border: none; padding: 4px; border-radius: 4px; }
        QPushButton#titleBtn:hover { background: rgba(0,0,0,0.06); }
        QPushButton#closeBtn { background: transparent; color: #b91c1c; border: none; padding: 4px; border-radius: 4px; }
        QPushButton#closeBtn:hover { background: rgba(185,28,28,0.08); }
        """

        self.init_ui()
        self.apply_dark_theme()

    def init_ui(self):
        rootLayout = QVBoxLayout()
        rootLayout.setContentsMargins(6, 6, 6, 6)
        rootLayout.setSpacing(0)

        # --- custom title bar ---
        titleBar = QFrame()
        titleBar.setObjectName('titleBar')
        titleBarLayout = QHBoxLayout()
        titleBarLayout.setContentsMargins(8, 6, 8, 6)
        titleBarLayout.setSpacing(8)

        iconLbl = QLabel()
        if self.app_icon:
            try:
                pm_path = os.path.join(getattr(self, 'base_path', os.path.dirname(os.path.abspath(__file__))), 'assets', 'cursor_icon.svg')
                pm = QPixmap(pm_path)
                iconLbl.setPixmap(pm.scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            except Exception:
                pass
        iconLbl.setFixedSize(20, 20)
        titleBarLayout.addWidget(iconLbl)

        titleLbl = QLabel('AERO AutoClicker')
        titleLbl.setObjectName('titleLbl')
        titleBarLayout.addWidget(titleLbl)
        titleBarLayout.addStretch()

        self.minBtn = QPushButton('—')
        self.minBtn.setFixedSize(32, 22)
        self.minBtn.setObjectName('titleBtn')
        self.minBtn.clicked.connect(self.showMinimized)
        titleBarLayout.addWidget(self.minBtn)

        self.maxBtn = QPushButton('❐')
        self.maxBtn.setFixedSize(32, 22)
        self.maxBtn.setObjectName('titleBtn')
        self.maxBtn.clicked.connect(self._toggle_max_restore)
        titleBarLayout.addWidget(self.maxBtn)

        self.closeBtn = QPushButton('✕')
        self.closeBtn.setFixedSize(32, 22)
        self.closeBtn.setObjectName('closeBtn')
        self.closeBtn.clicked.connect(self.close)
        titleBarLayout.addWidget(self.closeBtn)

        titleBar.setLayout(titleBarLayout)
        rootLayout.addWidget(titleBar)

        # track titlebar for dragging
        self._title_bar = titleBar
        self._drag_pos = None
        self._is_maximized = False

        # content area for controls (keeps children on an opaque background)
        contentLayout = QVBoxLayout()
        contentLayout.setContentsMargins(12, 12, 12, 12)
        contentLayout.setSpacing(8)

        # Window selector
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("Target window:"))
        self.winCombo = QComboBox()
        h1.addWidget(self.winCombo)
        self.refreshBtn = QPushButton("Refresh")
        self.refreshBtn.clicked.connect(self.refresh_windows)
        h1.addWidget(self.refreshBtn)
        contentLayout.addLayout(h1)

        # Rate controls
        h2 = QHBoxLayout()
        h2.addWidget(QLabel("Interval (ms):"))
        self.intervalSpin = QSpinBox()
        self.intervalSpin.setRange(1, 100000)
        self.intervalSpin.setValue(100)
        h2.addWidget(self.intervalSpin)
        h2.addStretch()
        self.doubleChk = QCheckBox("Double-click")
        h2.addWidget(self.doubleChk)
        contentLayout.addLayout(h2)

        # Coordinate controls
        hcoord = QHBoxLayout()
        hcoord.addWidget(QLabel("X:"))
        self.xSpin = QSpinBox()
        self.xSpin.setRange(0, 10000)
        self.xSpin.setValue(0)
        hcoord.addWidget(self.xSpin)
        hcoord.addWidget(QLabel("Y:"))
        self.ySpin = QSpinBox()
        self.ySpin.setRange(0, 10000)
        self.ySpin.setValue(0)
        hcoord.addWidget(self.ySpin)
        self.pickBtn = QPushButton("Pick Coordinates")
        self.pickBtn.clicked.connect(self.pick_coordinates)
        hcoord.addWidget(self.pickBtn)
        contentLayout.addLayout(hcoord)

        # Hotkey config (single read-only combo display + record button)
        hhot = QHBoxLayout()
        hhot.addWidget(QLabel("Hotkey:"))
        from PySide6.QtWidgets import QLineEdit
        self.keyEdit = QLineEdit()
        self.keyEdit.setFixedWidth(180)
        # default to Ctrl+Shift+S
        self.keyEdit.setText("Ctrl+Shift+S")
        self.keyEdit.setReadOnly(True)
        self.recordBtn = QPushButton("Record")
        self.recordBtn.setCheckable(True)
        self.recordBtn.clicked.connect(self._on_record_toggle)
        hhot.addWidget(self.recordBtn)
        hhot.addWidget(self.keyEdit)
        self.applyHotkeyBtn = QPushButton("Apply Hotkey")
        self.applyHotkeyBtn.clicked.connect(self.apply_hotkey)
        hhot.addWidget(self.applyHotkeyBtn)
        self.clearHotkeyBtn = QPushButton("Clear")
        self.clearHotkeyBtn.clicked.connect(self.clear_hotkey)
        hhot.addWidget(self.clearHotkeyBtn)
        # Background mode toggle: prefer PostMessage when enabled
        self.bgModeChk = QCheckBox("Background Mode (PostMessage)")
        self.bgModeChk.setChecked(True)
        hhot.addWidget(self.bgModeChk)
        # status label to show active delivery mode
        self.modeLbl = QLabel("Mode: PostMessage")
        self.modeLbl.setObjectName('small')
        hhot.addWidget(self.modeLbl)
        contentLayout.addLayout(hhot)

        # Start/Stop
        h3 = QHBoxLayout()
        self.startBtn = QPushButton("Start")
        self.startBtn.clicked.connect(self.start_clicking)
        h3.addWidget(self.startBtn)
        self.stopBtn = QPushButton("Stop")
        self.stopBtn.setObjectName("stopBtn")
        self.stopBtn.clicked.connect(self.stop_clicking)
        h3.addWidget(self.stopBtn)
        contentLayout.addLayout(h3)

        # Install hover shadow filter on primary buttons to enhance hover visibility
        try:
            hover_filter = HoverShadowFilter(self)
            for btn in (self.startBtn, self.stopBtn, self.applyHotkeyBtn, getattr(self, 'clearHotkeyBtn', None), self.recordBtn, self.refreshBtn):
                if btn is not None:
                    btn.installEventFilter(hover_filter)
        except Exception:
            pass

        # Theme toggle and info
        row = QHBoxLayout()
        self.themeBtn = QPushButton("Light Mode")
        self.themeBtn.clicked.connect(self.toggle_theme)
        row.addWidget(self.themeBtn)
        row.addStretch()
        info = QLabel("Click target will be the center of the chosen window.")
        info.setObjectName("small")
        row.addWidget(info)
        contentLayout.addLayout(row)

        # create content frame and add to root layout
        contentFrame = QFrame()
        contentFrame.setObjectName('content')
        contentFrame.setLayout(contentLayout)
        rootLayout.addWidget(contentFrame)

        self.setLayout(rootLayout)

        # timer to refresh selection if window list empty
        QTimer.singleShot(10, self.refresh_windows)
        # Poll hotkey event periodically
        self._hotkey_timer = QTimer(self)
        self._hotkey_timer.timeout.connect(self._poll_hotkey)
        self._hotkey_timer.start(100)

        # Load saved settings
        self.settings = QSettings("AERO", "AERO AutoClicker")
        self._load_settings()

        # Start hotkey thread with initial UI-configured hotkey
        if win32gui is not None:
            mods, vk = self._read_hotkey_ui()
            try:
                self.hotkey_thread = HotkeyThread(self.hotkey_event, mods=mods, vk=vk)
                self.hotkey_thread.start()
            except Exception:
                self.hotkey_thread = None

    def refresh_windows(self):
        self.winCombo.clear()
        wins = list_windows()
        for hwnd, title in wins:
            self.winCombo.addItem(f"{title} [{hwnd}]", hwnd)
        # try to restore last selected target by title substring
        try:
            last = self.settings.value("target_title", "")
            if last:
                for i in range(self.winCombo.count()):
                    if last in self.winCombo.itemText(i):
                        self.winCombo.setCurrentIndex(i)
                        break
        except Exception:
            pass

    def get_selected_hwnd(self):
        idx = self.winCombo.currentIndex()
        if idx < 0:
            return None
        return self.winCombo.itemData(idx)

    def start_clicking(self):
        if win32gui is None:
            QMessageBox.critical(self, "Missing dependency", "This app requires Windows and pywin32.")
            return

        hwnd = self.get_selected_hwnd()
        if not hwnd:
            QMessageBox.warning(self, "No target", "Please select a target window.")
            return

        interval = self.intervalSpin.value()
        double = self.doubleChk.isChecked()

        if self.worker and self.worker.is_alive():
            QMessageBox.information(self, "Already running", "Clicker is already running.")
            return

        self.worker_stop = threading.Event()
        self.worker = ClickWorker(hwnd, interval_ms=interval, double=double, stop_event=self.worker_stop)
        # set whether to use system mouse
        try:
            use_sys = True
            self.worker.set_use_system_mouse(use_sys)
        except Exception:
            pass
        # set background mode (PostMessage preference) and provide fallback callback
        try:
            bg = bool(self.bgModeChk.isChecked())
            self.worker.set_background_mode(bg, fallback_callback=self._on_worker_fallback)
        except Exception:
            pass
        # compute and store fixed screen position so system-mouse clicks stay at the chosen point
        try:
            # determine client coords used by worker (offset if provided, otherwise center)
            if self.xSpin.value() != 0 or self.ySpin.value() != 0:
                cx, cy = int(self.xSpin.value()), int(self.ySpin.value())
            else:
                cx, cy = client_center(hwnd)
            try:
                sx, sy = win32gui.ClientToScreen(hwnd, (cx, cy))
            except Exception:
                sx, sy = cx, cy
            self.worker.set_fixed_screen(sx, sy)
        except Exception:
            pass
        # set offset if specified
        try:
            x = int(self.xSpin.value())
            y = int(self.ySpin.value())
            if x != 0 or y != 0:
                self.worker.set_offset(x, y)
        except Exception:
            pass
        self.worker.daemon = True
        self.worker.start()

    def stop_clicking(self):
        if self.worker_stop:
            self.worker_stop.set()
            self.worker = None
            self.worker_stop = None

    def _poll_hotkey(self):
        if self.hotkey_event.is_set():
            self.hotkey_event.clear()
            # toggle
            if self.worker and self.worker_stop:
                self.stop_clicking()
            else:
                self.start_clicking()

    def _read_hotkey_ui(self):
        # return (mods, vk) for current UI selection
        mods = 0
        keytxt = self.keyEdit.text().strip()
        vk = 0
        if keytxt:
            # parse tokens like "Ctrl+Shift+S" or "F5"
            parts = [p.strip() for p in keytxt.split('+') if p.strip()]
            last = parts[-1] if parts else ''
            # modifiers
            for p in parts[:-1]:
                up = p.upper()
                if up in ('CTRL', 'CONTROL'):
                    mods |= (win32con.MOD_CONTROL if win32con is not None else 0)
                elif up in ('ALT',):
                    mods |= (win32con.MOD_ALT if win32con is not None else 0)
                elif up in ('SHIFT',):
                    mods |= (win32con.MOD_SHIFT if win32con is not None else 0)

            kt = last.upper()
            if kt:
                # function keys
                if kt.startswith('F') and kt[1:].isdigit():
                    try:
                        n = int(kt[1:])
                        vk = getattr(win32con, f'VK_F{n}')
                    except Exception:
                        vk = ord(kt[0]) if len(kt) == 1 else ord(kt[0])
                else:
                    if len(kt) == 1:
                        vk = ord(kt)
                    else:
                        special = {'ESC': win32con.VK_ESCAPE if win32con is not None else 0,
                                   'TAB': win32con.VK_TAB if win32con is not None else 0,
                                   'ENTER': win32con.VK_RETURN if win32con is not None else 0,
                                   'SPACE': win32con.VK_SPACE if win32con is not None else 0}
                        vk = special.get(kt, ord(kt[0]))
        return mods, vk

    def apply_hotkey(self):
        if win32gui is None:
            QMessageBox.warning(self, "Hotkey", "pywin32 not available; cannot register hotkey.")
            return
        mods, vk = self._read_hotkey_ui()
        # shutdown existing
        if self.hotkey_thread:
            try:
                self.hotkey_thread.shutdown()
                self.hotkey_thread.join(timeout=0.5)
            except Exception:
                pass
            self.hotkey_thread = None
        try:
            self.hotkey_thread = HotkeyThread(self.hotkey_event, mods=mods, vk=vk)
            self.hotkey_thread.start()
            QMessageBox.information(self, "Hotkey", "Hotkey applied.")
        except Exception as e:
            QMessageBox.warning(self, "Hotkey", f"Failed to register hotkey: {e}")

    def clear_hotkey(self):
        # Unregister any existing hotkey and clear the display
        if getattr(self, 'hotkey_thread', None):
            try:
                self.hotkey_thread.shutdown()
                self.hotkey_thread.join(timeout=0.5)
            except Exception:
                pass
            self.hotkey_thread = None
        try:
            self.keyEdit.setText("")
        except Exception:
            pass
        try:
            self._save_settings()
        except Exception:
            pass

    def _on_record_toggle(self, checked: bool):
        # Start/stop recording the next key press
        if checked:
            self.recording_hotkey = True
            self.recordBtn.setText("Recording...")
            # force focus so key events arrive here
            self.keyEdit.setFocus()
        else:
            self.recording_hotkey = False
            self.recordBtn.setText("Record")

    def _on_worker_fallback(self):
        # called from worker thread context; schedule UI update via QTimer.singleShot
        try:
            def notify():
                try:
                    self.modeLbl.setText("Mode: System Mouse (fallback)")
                    QMessageBox.information(self, "Fallback", "PostMessage did not work for the chosen window. Falling back to system mouse for reliable clicks.")
                except Exception:
                    pass
            QTimer.singleShot(0, notify)
        except Exception:
            pass

    def keyPressEvent(self, event):
        # If we're recording, capture modifiers + key
        if getattr(self, 'recording_hotkey', False):
            mods = event.modifiers()
            parts = []
            if mods & Qt.ControlModifier:
                parts.append('Ctrl')
            if mods & Qt.AltModifier:
                parts.append('Alt')
            if mods & Qt.ShiftModifier:
                parts.append('Shift')

            keytxt = ''
            txt = event.text()
            # Some modifier combos produce non-printable control characters
            # (e.g. Ctrl+Shift+S may yield a control code). Prefer the
            # printable text when available; otherwise fall back to key()
            if txt and txt.strip() and txt.isprintable():
                keytxt = txt.upper()
            else:
                k = event.key()
                # function keys
                if Qt.Key_F1 <= k <= Qt.Key_F35:
                    keytxt = f'F{(k - Qt.Key_F1) + 1}'
                # letters A-Z
                elif Qt.Key_A <= k <= Qt.Key_Z:
                    keytxt = chr(ord('A') + (k - Qt.Key_A))
                # digits 0-9
                elif Qt.Key_0 <= k <= Qt.Key_9:
                    keytxt = chr(ord('0') + (k - Qt.Key_0))
                else:
                    # map some common non-text keys
                    key_map = {
                        Qt.Key_Escape: 'Esc',
                        Qt.Key_Tab: 'Tab',
                        Qt.Key_Return: 'Enter',
                        Qt.Key_Enter: 'Enter',
                        Qt.Key_Space: 'Space',
                    }
                    keytxt = key_map.get(k, '')

            if keytxt:
                combo = '+'.join(parts + [keytxt]) if parts else keytxt
                self.keyEdit.setText(combo)
                # stop recording
                self.recording_hotkey = False
                self.recordBtn.setChecked(False)
                self.recordBtn.setText("Record")
                try:
                    # automatically apply the hotkey the user just recorded
                    self.apply_hotkey()
                except Exception:
                    pass
            # accept the event so it doesn't propagate
            event.accept()
            return

        # otherwise default behavior
        super().keyPressEvent(event)

    def _load_settings(self):
        try:
            interval = int(self.settings.value("interval", 100))
        except Exception:
            interval = 100
        try:
            self.intervalSpin.setValue(interval)
        except Exception:
            pass

        try:
            self.doubleChk.setChecked(self.settings.value("double", "false") in (True, "true", "1", 1))
        except Exception:
            pass

        try:
            x = int(self.settings.value("click_x", 0))
            y = int(self.settings.value("click_y", 0))
            self.xSpin.setValue(x)
            self.ySpin.setValue(y)
        except Exception:
            pass

        try:
            theme = self.settings.value("theme", "dark")
            if theme == "light":
                self.apply_light_theme()
            else:
                self.apply_dark_theme()
        except Exception:
            pass

        try:
            # hotkey (stored as single combo string) — default to Ctrl+Shift+S
            key = self.settings.value("hot_key", "Ctrl+Shift+S")
            if key:
                self.keyEdit.setText(str(key))
        except Exception:
            pass

        try:
            # background mode
            bg = self.settings.value("background_mode", "true") in (True, "true", "1", 1)
            self.bgModeChk.setChecked(bg)
            self.modeLbl.setText("Mode: PostMessage" if bg else "Mode: System Mouse")
        except Exception:
            pass

    def _save_settings(self):
        try:
            self.settings.setValue("interval", int(self.intervalSpin.value()))
            self.settings.setValue("double", bool(self.doubleChk.isChecked()))
            self.settings.setValue("click_x", int(self.xSpin.value()))
            self.settings.setValue("click_y", int(self.ySpin.value()))
            self.settings.setValue("theme", "light" if self.themeBtn.text() == "Dark Mode" else "dark")
            # save hotkey UI (single combo string)
            self.settings.setValue("hot_key", str(self.keyEdit.text()))
            # save background mode
            try:
                self.settings.setValue("background_mode", bool(self.bgModeChk.isChecked()))
            except Exception:
                pass
            # save selected target title substring if possible
            try:
                sel = self.winCombo.currentText()
                if sel:
                    # save until the last ' [' which precedes the hwnd
                    self.settings.setValue("target_title", sel)
            except Exception:
                pass
        except Exception:
            pass

    def pick_coordinates(self):
        hwnd = self.get_selected_hwnd()
        if not hwnd:
            QMessageBox.warning(self, "No target", "Please select a target window first.")
            return

        # Hide our window so user can click target
        self.hide()
        try:
            # try to bring target to foreground
            try:
                win32gui.SetForegroundWindow(hwnd)
            except Exception:
                pass

            QMessageBox.information(None, "Pick", "After you dismiss this, click the desired point in the target window. The next left-click will be recorded.")

            # wait for left button down
            while True:
                state = win32api.GetAsyncKeyState(win32con.VK_LBUTTON)
                if state & 0x8000:
                    # get cursor pos
                    x, y = win32gui.GetCursorPos()
                    # translate to client coords
                    try:
                        cx, cy = win32gui.ScreenToClient(hwnd, (x, y))
                    except Exception:
                        cx, cy = x, y
                    self.xSpin.setValue(max(0, int(cx)))
                    self.ySpin.setValue(max(0, int(cy)))
                    break
                time.sleep(0.01)
        finally:
            self.show()

    def _toggle_max_restore(self):
        if self._is_maximized:
            self.showNormal()
            self._is_maximized = False
        else:
            self.showMaximized()
            self._is_maximized = True

    def mousePressEvent(self, event):
        # allow dragging by clicking the custom title bar
        if event.button() == Qt.LeftButton:
            pos = event.position().toPoint()
            gpos = event.globalPosition().toPoint()
            if self._title_bar and pos.y() <= self._title_bar.height():
                self._drag_pos = gpos - self.frameGeometry().topLeft()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if getattr(self, '_drag_pos', None) is not None and event.buttons() & Qt.LeftButton:
            try:
                gpos = event.globalPosition().toPoint()
                self.move(gpos - self._drag_pos)
            except Exception:
                pass
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def closeEvent(self, event):
        # cleanup hotkey
        # save settings
        try:
            self._save_settings()
        except Exception:
            pass
        if self.hotkey_thread:
            self.hotkey_thread.shutdown()
            self.hotkey_thread.join(timeout=1.0)
        event.accept()

    def apply_dark_theme(self):
        self.setStyleSheet(self.dark_qss)
        self.themeBtn.setText("Light Mode")

    def apply_light_theme(self):
        self.setStyleSheet(self.light_qss)
        self.themeBtn.setText("Dark Mode")

    def toggle_theme(self):
        if self.themeBtn.text() == "Light Mode":
            self.apply_light_theme()
        else:
            self.apply_dark_theme()


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
