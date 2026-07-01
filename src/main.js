const { invoke } = window.__TAURI__.core;
const { listen } = window.__TAURI__.event;

// Prevent right-click context menu to feel more like a native app
document.addEventListener("contextmenu", (e) => e.preventDefault());

let isRunning = false;
let currentHotkey = "CommandOrControl+Shift+S";

document.addEventListener("DOMContentLoaded", async () => {
  const themeToggle = document.getElementById("theme-toggle");
  const winSelect = document.getElementById("window-select");
  const refreshBtn = document.getElementById("refresh-btn");
  const startBtn = document.getElementById("start-btn");
  const stopBtn = document.getElementById("stop-btn");
  const intervalInput = document.getElementById("interval");
  const doubleClickCheck = document.getElementById("double-click");
  const coordX = document.getElementById("coord-x");
  const coordY = document.getElementById("coord-y");
  const pickBtn = document.getElementById("pick-btn");
  const hotkeyDisplay = document.getElementById("hotkey-display");
  const recordBtn = document.getElementById("record-btn");
  const bgModeCheck = document.getElementById("background-mode");

  // Theme Handling
  const THEME_KEY = "aero_theme";
  let isDark = localStorage.getItem(THEME_KEY) !== "light";
  
  const updateTheme = () => {
    if (isDark) {
      document.body.classList.add("dark-mode");
      themeToggle.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-sun"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/></svg>`;
    } else {
      document.body.classList.remove("dark-mode");
      themeToggle.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-moon"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>`;
    }
  };
  
  updateTheme();

  themeToggle.addEventListener("click", () => {
    isDark = !isDark;
    localStorage.setItem(THEME_KEY, isDark ? "dark" : "light");
    updateTheme();
  });

  // Windows List
  const loadWindows = async () => {
    try {
      const wins = await invoke("get_windows");
      // preserve selection
      const currentVal = winSelect.value;
      winSelect.innerHTML = `<option value="" disabled selected>Select a window...</option>`;
      wins.forEach(w => {
        const opt = document.createElement("option");
        opt.value = w.hwnd;
        opt.textContent = `${w.title} [${w.hwnd}]`;
        winSelect.appendChild(opt);
      });
      if (currentVal && wins.find(w => w.hwnd == currentVal)) {
        winSelect.value = currentVal;
      }
    } catch (e) {
      console.error(e);
    }
  };
  
  refreshBtn.addEventListener("click", loadWindows);
  loadWindows();

  const updateButtons = () => {
    if (isRunning) {
      startBtn.classList.remove("solid-blue");
      startBtn.classList.add("translucent-blue");
      startBtn.disabled = true;

      stopBtn.classList.remove("translucent-red");
      stopBtn.classList.add("solid-red");
      stopBtn.disabled = false;
    } else {
      startBtn.classList.remove("translucent-blue");
      startBtn.classList.add("solid-blue");
      startBtn.disabled = false;

      stopBtn.classList.remove("solid-red");
      stopBtn.classList.add("translucent-red");
      stopBtn.disabled = true;
    }
  };

  const startClicking = async () => {
    if (isRunning) return;
    const hwnd = parseInt(winSelect.value);
    if (isNaN(hwnd)) {
      alert("Please select a target window.");
      return;
    }

    const interval = parseInt(intervalInput.value);
    const double = doubleClickCheck.checked;
    const bgMode = bgModeCheck.checked;
    const x = parseInt(coordX.value) || 0;
    const y = parseInt(coordY.value) || 0;

    try {
      await invoke("start_clicking", {
        hwnd,
        intervalMs: interval,
        double,
        x: x === 0 ? null : x,
        y: y === 0 ? null : y,
        backgroundMode: bgMode
      });
      isRunning = true;
      updateButtons();
    } catch (e) {
      console.error(e);
      alert(e);
    }
  };

  const stopClicking = async () => {
    if (!isRunning) return;
    try {
      await invoke("stop_clicking");
      isRunning = false;
      updateButtons();
    } catch (e) {
      console.error(e);
    }
  };

  startBtn.addEventListener("click", startClicking);
  stopBtn.addEventListener("click", stopClicking);

  // Global hotkey toggling
  const toggleClicking = () => {
    if (isRunning) {
      stopClicking();
    } else {
      startClicking();
    }
  };

  listen("toggle-clicker", () => {
    toggleClicking();
  });

  listen("clicker-stopped", () => {
    if (isRunning) {
      isRunning = false;
      updateButtons();
    }
  });

  const setupHotkey = async (key) => {
    try {
      await invoke("register_hotkey", { hotkey: key });
      currentHotkey = key;
    } catch (e) {
      console.error("Hotkey error", e);
    }
  };

  const registerHotkey = async (keyCombination) => {
    try {
      await setupHotkey(keyCombination);
      hotkeyDisplay.value = currentHotkey;
    } catch (e) {
      console.error("Failed to register hotkey", e);
    }
  };

  // init hotkey
  registerHotkey(currentHotkey);

  // pick coords
  pickBtn.addEventListener("click", async () => {
    const hwnd = parseInt(winSelect.value);
    if (isNaN(hwnd)) {
      alert("Please select a target window first.");
      return;
    }
    try {
      const [cx, cy] = await invoke("pick_coordinates", { hwnd });
      coordX.value = cx;
      coordY.value = cy;
    } catch (e) {
      console.error(e);
    }
  });

  // record hotkey
  let isRecording = false;
  recordBtn.addEventListener("click", () => {
    if (isRecording) {
      isRecording = false;
      recordBtn.textContent = "Record";
      document.removeEventListener("keydown", hotkeyRecorder);
    } else {
      isRecording = true;
      recordBtn.textContent = "Recording...";
      document.addEventListener("keydown", hotkeyRecorder);
    }
  });

  const hotkeyRecorder = async (e) => {
    e.preventDefault();
    const parts = [];
    if (e.ctrlKey || e.metaKey) parts.push("CommandOrControl");
    if (e.altKey) parts.push("Alt");
    if (e.shiftKey) parts.push("Shift");
    
    // Ignore if only modifiers are pressed
    if (["Control", "Shift", "Alt", "Meta"].includes(e.key)) return;

    let key = e.key.toUpperCase();
    if (key === " ") key = "Space";
    parts.push(key);

    const shortcutStr = parts.join("+");
    hotkeyDisplay.value = shortcutStr;
    
    isRecording = false;
    recordBtn.textContent = "Record";
    document.removeEventListener("keydown", hotkeyRecorder);
    await registerHotkey(shortcutStr);
  };
});
