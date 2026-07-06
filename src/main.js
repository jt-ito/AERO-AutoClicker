const { invoke } = window.__TAURI__.core;
const { listen } = window.__TAURI__.event;

// Prevent right-click context menu to feel more like a native app
document.addEventListener("contextmenu", (e) => e.preventDefault());

let isRunning = false;
let currentHotkey = "CommandOrControl+Shift+S";

document.addEventListener("DOMContentLoaded", async () => {
  // Test page is now handled by test.html directly.

  const themeToggle = document.getElementById("theme-toggle");
  const testPageBtn = document.getElementById("test-page-btn");
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
  const enableTargetCheck = document.getElementById("enable-target-window");

  // Handle target window toggle
  const updateTargetWindowDisabledState = () => {
    const disabled = !enableTargetCheck.checked;
    winSelect.disabled = disabled;
    refreshBtn.disabled = disabled;
    coordX.disabled = disabled;
    coordY.disabled = disabled;
    pickBtn.disabled = disabled;
    bgModeCheck.disabled = disabled;
  };

  enableTargetCheck.addEventListener("change", updateTargetWindowDisabledState);
  updateTargetWindowDisabledState();

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

  testPageBtn.addEventListener("click", async () => {
    try {
      if (!window.__TAURI__ || !window.__TAURI__.webviewWindow) {
        alert("window.__TAURI__.webviewWindow is not available. Please ensure capabilities are configured.");
        return;
      }
      
      const { WebviewWindow } = window.__TAURI__.webviewWindow;
      
      const webview = new WebviewWindow('test-page', {
        url: 'test.html',
        title: 'Autoclicker Test Page',
        width: 800,
        height: 600,
        resizable: true
      });
      
      webview.once('tauri://error', (e) => {
        alert('error creating test page window: ' + JSON.stringify(e));
      });

      // Auto-select as target window
      setTimeout(async () => {
        await loadWindows();
        const opts = Array.from(winSelect.options);
        const testPageOpt = opts.find(o => o.textContent.includes('Autoclicker Test Page'));
        if (testPageOpt) {
          winSelect.value = testPageOpt.value;
          enableTargetCheck.checked = true;
          updateTargetWindowDisabledState();
        }
      }, 1000);
    } catch (e) {
      alert("Failed to open test page: " + e);
    }
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
    
    let hwnd = null;
    if (enableTargetCheck.checked) {
      hwnd = parseInt(winSelect.value);
      if (isNaN(hwnd)) {
        alert("Please select a target window.");
        return;
      }
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

  // hotkey utility
  const recordHotkey = (btn, display, onComplete) => {
    let isRecording = false;
    btn.addEventListener("click", () => {
      if (isRecording) {
        isRecording = false;
        btn.textContent = "Set";
        document.removeEventListener("keydown", hotkeyRecorder);
      } else {
        isRecording = true;
        btn.textContent = "Recording...";
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
      display.value = shortcutStr;
      
      isRecording = false;
      btn.textContent = "Set";
      document.removeEventListener("keydown", hotkeyRecorder);
      onComplete(shortcutStr);
    };
  };

  // setup hotkeys
  let clickerHotkeyStr = "CommandOrControl+Shift+S";
  let macroRecordHotkeyStr = "CommandOrControl+Shift+R";
  let macroPlayHotkeyStr = "CommandOrControl+Shift+P";

  // Prevent browser reload shortcuts (Ctrl+R, F5, Ctrl+Shift+R)
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && (e.key.toLowerCase() === 'r')) {
      e.preventDefault();
    }
    if (e.key === 'F5') {
      e.preventDefault();
    }
  });

  const registerAllHotkeys = async () => {
    try {
      await invoke("register_hotkeys", { 
        clicker: clickerHotkeyStr,
        macroRecord: macroRecordHotkeyStr,
        macroPlay: macroPlayHotkeyStr
      });
    } catch (e) {
      console.error("Failed to register hotkeys", e);
    }
  };

  // Note: the original recordHotkey and initial registerAllHotkeys has been moved to the settings block.


  // --- MACRO LOGIC ---
  const tabClicker = document.getElementById("tab-clicker");
  const tabMacro = document.getElementById("tab-macro");
  const viewClicker = document.getElementById("clicker-view");
  const viewMacro = document.getElementById("macro-view");

  tabClicker.addEventListener("click", () => {
    tabClicker.classList.add("active");
    tabMacro.classList.remove("active");
    viewClicker.style.display = "flex";
    viewMacro.style.display = "none";
  });

  tabMacro.addEventListener("click", () => {
    tabMacro.classList.add("active");
    tabClicker.classList.remove("active");
    viewMacro.style.display = "flex";
    viewClicker.style.display = "none";
  });

  const macroRecordHotkeyDisplay = document.getElementById("macro-record-hotkey");
  const macroRecordHotkeyBtn = document.getElementById("record-macro-hotkey-btn");
  
  const macroPlayHotkeyDisplay = document.getElementById("macro-play-hotkey");
  const macroPlayHotkeyBtn = document.getElementById("record-macro-play-hotkey-btn");
  
  recordHotkey(macroPlayHotkeyBtn, macroPlayHotkeyDisplay, (key) => {
    macroPlayHotkeyStr = key;
    registerAllHotkeys();
    saveSettings();
  });

  recordHotkey(macroRecordHotkeyBtn, macroRecordHotkeyDisplay, (key) => {
    macroRecordHotkeyStr = key;
    registerAllHotkeys();
    saveSettings();
  });

  recordHotkey(recordBtn, hotkeyDisplay, (key) => {
    clickerHotkeyStr = key;
    registerAllHotkeys();
    saveSettings();
  });

  // Settings Persistence
  const SETTINGS_KEY = "aero_settings";
  const saveSettings = () => {
    const s = {
      enableTarget: enableTargetCheck.checked,
      interval: intervalInput.value,
      doubleClick: doubleClickCheck.checked,
      coordX: coordX.value,
      coordY: coordY.value,
      bgMode: bgModeCheck.checked,
      clickerHotkey: clickerHotkeyStr,
      macroRecordHotkey: macroRecordHotkeyStr,
      macroPlayHotkey: macroPlayHotkeyStr
    };
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(s));
  };

  const loadSettings = () => {
    const saved = localStorage.getItem(SETTINGS_KEY);
    if (saved) {
      try {
        const s = JSON.parse(saved);
        if (s.enableTarget !== undefined) enableTargetCheck.checked = s.enableTarget;
        if (s.interval !== undefined) intervalInput.value = s.interval;
        if (s.doubleClick !== undefined) doubleClickCheck.checked = s.doubleClick;
        if (s.coordX !== undefined) coordX.value = s.coordX;
        if (s.coordY !== undefined) coordY.value = s.coordY;
        if (s.bgMode !== undefined) bgModeCheck.checked = s.bgMode;
        if (s.clickerHotkey) clickerHotkeyStr = s.clickerHotkey;
        if (s.macroRecordHotkey) macroRecordHotkeyStr = s.macroRecordHotkey;
        if (s.macroPlayHotkey) macroPlayHotkeyStr = s.macroPlayHotkey;
      } catch (e) {}
    }
    hotkeyDisplay.value = clickerHotkeyStr;
    macroRecordHotkeyDisplay.value = macroRecordHotkeyStr;
    macroPlayHotkeyDisplay.value = macroPlayHotkeyStr;
    updateTargetWindowDisabledState();
  };

  // Add event listeners to auto-save
  [enableTargetCheck, intervalInput, doubleClickCheck, coordX, coordY, bgModeCheck].forEach(el => {
    el.addEventListener('change', saveSettings);
    el.addEventListener('input', saveSettings);
  });

  loadSettings();
  registerAllHotkeys();

  // Macro state
  let moves = [];
  let isMacroRecording = false;
  let isMacroPlaying = false;
  const movesList = document.getElementById("moves-list");
  const clearMovesBtn = document.getElementById("clear-moves-btn");
  const playMacroBtn = document.getElementById("play-macro-btn");
  const stopMacroBtn = document.getElementById("stop-macro-btn");

  const renderMoves = () => {
    movesList.innerHTML = "";
    if (moves.length === 0) {
      movesList.innerHTML = `<li class="empty-state">No moves recorded. Press your record hotkey to start!</li>`;
      return;
    }

    moves.forEach((move, index) => {
      const li = document.createElement("li");
      li.className = "move-item";
      li.draggable = true;
      li.dataset.index = index;

      let icon = "";
      let text = "";
      if (move.type === "Delay") {
        icon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-clock"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`;
        text = `Wait ${move.ms} ms`;
      } else if (move.type === "Click") {
        icon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-mouse-pointer-click"><path d="M14 4.1 12 6"/><path d="m5.1 8-2.9-.8"/><path d="m6 12-1.9 2"/><path d="M7.2 2.2 8 5.1"/><path d="M9.037 9.69a.498.498 0 0 1 .653-.653l11 4.5a.5.5 0 0 1-.074.949l-4.349 1.041a1 1 0 0 0-.74.739l-1.04 4.35a.5.5 0 0 1-.95.074z"/></svg>`;
        text = `Left Click at (${move.x}, ${move.y})`;
      } else if (move.type === "RightClick") {
        icon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-mouse-pointer-click"><path d="M14 4.1 12 6"/><path d="m5.1 8-2.9-.8"/><path d="m6 12-1.9 2"/><path d="M7.2 2.2 8 5.1"/><path d="M9.037 9.69a.498.498 0 0 1 .653-.653l11 4.5a.5.5 0 0 1-.074.949l-4.349 1.041a1 1 0 0 0-.74.739l-1.04 4.35a.5.5 0 0 1-.95.074z"/></svg>`;
        text = `Right Click at (${move.x}, ${move.y})`;
      } else if (move.type === "KeyDown" || move.type === "KeyUp") {
        icon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-keyboard"><path d="M10 8h.01"/><path d="M12 12h.01"/><path d="M14 8h.01"/><path d="M16 12h.01"/><path d="M18 8h.01"/><path d="M6 8h.01"/><path d="M7 16h10"/><path d="M8 12h.01"/><rect width="20" height="16" x="2" y="4" rx="2"/></svg>`;
        let keyName = String.fromCharCode(move.key || 0);
        if (move.key === 32) keyName = "SPACE";
        text = `${move.type === "KeyDown" ? "Press" : "Release"} [${keyName}]`;
      }

      li.innerHTML = `
        <div class="move-info">
          <span class="move-icon">${icon}</span>
          <span>${text}</span>
        </div>
        <div class="move-actions">
          <button class="delete-move-btn" data-index="${index}">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-x"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
          </button>
        </div>
      `;

      // Drag and drop events
      li.addEventListener("dragstart", (e) => {
        e.dataTransfer.setData("text/plain", index);
        li.classList.add("dragging");
      });
      li.addEventListener("dragend", () => {
        li.classList.remove("dragging");
      });
      li.addEventListener("dragover", (e) => {
        e.preventDefault();
      });
      li.addEventListener("drop", (e) => {
        e.preventDefault();
        const fromIndex = parseInt(e.dataTransfer.getData("text/plain"));
        const toIndex = index;
        if (fromIndex !== toIndex) {
          const moveItem = moves.splice(fromIndex, 1)[0];
          moves.splice(toIndex, 0, moveItem);
          renderMoves();
        }
      });

      movesList.appendChild(li);
    });

    // Delete buttons
    document.querySelectorAll(".delete-move-btn").forEach(btn => {
      btn.addEventListener("click", (e) => {
        const idx = parseInt(e.currentTarget.dataset.index);
        moves.splice(idx, 1);
        renderMoves();
      });
    });
  };

  clearMovesBtn.addEventListener("click", () => {
    moves = [];
    renderMoves();
  });

  listen("macro-move-recorded", (e) => {
    moves.push(e.payload);
    renderMoves();
    // auto scroll to bottom
    movesList.parentElement.scrollTop = movesList.parentElement.scrollHeight;
  });

  const getVkCodesForHotkey = (hotkeyStr) => {
    const parts = hotkeyStr.split("+");
    const codes = new Set();
    parts.forEach(p => {
      p = p.toLowerCase();
      if (p === "commandorcontrol" || p === "control" || p === "ctrl") { codes.add(17); codes.add(162); codes.add(163); }
      else if (p === "shift") { codes.add(16); codes.add(160); codes.add(161); }
      else if (p === "alt") { codes.add(18); codes.add(164); codes.add(165); }
      else if (p === "meta" || p === "super" || p === "win") { codes.add(91); codes.add(92); }
      else if (p === "space") codes.add(32);
      else if (p.length === 1) codes.add(p.toUpperCase().charCodeAt(0));
    });
    return codes;
  };

  listen("toggle-macro-record", async () => {
    if (isMacroRecording) {
      await invoke("stop_macro_recording");
      isMacroRecording = false;
      document.body.style.border = "none";
      
      const hotkeyCodes = getVkCodesForHotkey(macroRecordHotkeyStr);
      
      // Strip from beginning: KeyUp of hotkey and leading Delays
      while (moves.length > 0) {
        const first = moves[0];
        if (first.type === "Delay") {
          moves.shift();
        } else if (first.type === "KeyUp" && hotkeyCodes.has(first.key)) {
          moves.shift();
        } else {
          break;
        }
      }
      
      // Strip from end: KeyDown/KeyUp of hotkey and trailing Delays
      while (moves.length > 0) {
        const last = moves[moves.length - 1];
        if (last.type === "Delay") {
          moves.pop();
        } else if ((last.type === "KeyDown" || last.type === "KeyUp") && hotkeyCodes.has(last.key)) {
          moves.pop();
        } else {
          break;
        }
      }
      
      renderMoves();
    } else {
      moves = [];
      renderMoves();
      let targetHwnd = null;
      if (enableTargetCheck.checked) {
        const hwnd = parseInt(winSelect.value);
        targetHwnd = isNaN(hwnd) ? null : hwnd;
      }
      await invoke("start_macro_recording", { hwnd: targetHwnd });
      isMacroRecording = true;
      // visual indicator
      document.body.style.border = "2px solid #ff3333";
      document.body.style.boxSizing = "border-box";
    }
  });

  const startMacroPlayback = async () => {
    if (isMacroPlaying || moves.length === 0) return;
    try {
      let targetHwnd = null;
      if (enableTargetCheck.checked) {
        const hwnd = parseInt(winSelect.value);
        targetHwnd = isNaN(hwnd) ? null : hwnd;
      }
      await invoke("start_macro_playback", { moves, hwnd: targetHwnd });
      isMacroPlaying = true;
      playMacroBtn.classList.remove("solid-blue");
      playMacroBtn.classList.add("translucent-blue");
      playMacroBtn.disabled = true;

      stopMacroBtn.classList.remove("translucent-red");
      stopMacroBtn.classList.add("solid-red");
      stopMacroBtn.disabled = false;
    } catch (e) {
      console.error(e);
    }
  };

  const stopMacroPlayback = async () => {
    if (!isMacroPlaying) return;
    try {
      await invoke("stop_macro_playback");
    } catch (e) {
      console.error(e);
    }
  };

  listen("toggle-macro-play", () => {
    if (isMacroPlaying) stopMacroPlayback();
    else startMacroPlayback();
  });

  listen("macro-playback-stopped", () => {
    isMacroPlaying = false;
    playMacroBtn.classList.remove("translucent-blue");
    playMacroBtn.classList.add("solid-blue");
    playMacroBtn.disabled = false;

    stopMacroBtn.classList.remove("solid-red");
    stopMacroBtn.classList.add("translucent-red");
    stopMacroBtn.disabled = true;
  });

  playMacroBtn.addEventListener("click", startMacroPlayback);
  stopMacroBtn.addEventListener("click", stopMacroPlayback);
});

