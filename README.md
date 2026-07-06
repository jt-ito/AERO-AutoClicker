<div align="center">
  <img src="src-tauri/icons/128x128.png" alt="AERO Logo" width="128">
  
  # AERO AutoClicker
  
  **A blazing fast, modern, and reliable autoclicker built with Rust & Tauri.**
  
  [![Release](https://img.shields.io/github/v/release/jt-ito/AERO-AutoClicker?style=for-the-badge)](https://github.com/jt-ito/AERO-AutoClicker/releases)
  [![Platform](https://img.shields.io/badge/Platform-Windows-blue?style=for-the-badge)]()
  
</div>

---

AERO is a next-generation automation toolkit designed for speed, reliability, and ease of use. By combining a lightweight **Rust** backend with a beautiful, modern **Tauri + Vanilla JS/CSS** frontend, AERO delivers uncompromising performance with a premium user experience.

Whether you need a simple rapid-fire autoclicker or a complex, multi-input macro sequence, AERO handles it all natively on Windows without breaking a sweat.

## ✨ Features

### 🖱️ Advanced AutoClicking
- **Precision Speed**: Achieve impossibly high Clicks-Per-Second (CPS) with sub-millisecond Rust timing.
- **Background Mode**: Target specific background windows to click silently without hijacking your active mouse cursor.
- **Custom Coordinates**: Specify exact X and Y screen coordinates, or use the built-in screen picker.
- **Double Clicks**: Native double-click simulation support.

### ⌨️ Bulletproof Macro Engine
- **Hardware-Level Polling**: The macro recorder utilizes a dedicated `GetAsyncKeyState` hardware polling thread, guaranteeing your inputs are recorded perfectly, even in environments with strict anti-cheat software or group policies that block traditional Win32 hooks.
- **Full Input Capture**: Captures left clicks, right clicks, and **all** keyboard keystrokes natively.
- **Smart Hotkey Stripping**: Intelligently parses your custom stop-recording hotkey and cleanly strips it out of the final macro sequence so it never accidentally plays back.
- **Drag-and-Drop Editor**: Easily re-order, tweak, or delete specific actions from your recorded macro sequence directly within the UI.

### 🎨 Premium User Experience
- **Modern Glassmorphism UI**: Beautifully crafted interface with smooth micro-animations.
- **Persistent State**: AERO remembers all of your custom hotkeys, delays, coordinates, and theme preferences across sessions automatically.
- **Light & Dark Mode**: Toggle instantly between sleek dark mode or vibrant light mode.
- **Built-in 3D Test Environment**: Test your macros and CPS speeds safely inside AERO's built-in pure CSS 3D "Minecraft-style" testing arena—complete with autoclicker detection alerts!

## 🚀 Getting Started

### Installation
Grab the latest release installer from the [Releases](https://github.com/jt-ito/AERO-AutoClicker/releases) page.
- `AERO_1.2.0_x64-setup.exe` (Recommended NSIS Installer)
- `AERO_1.2.0_x64_en-US.msi` (Windows Installer)
- `aero-clicker.exe` (Portable Binary)

### Usage Guide
1. **Set your Hotkeys**: Click any of the "Set" buttons next to a hotkey display and press your desired shortcut (e.g., `Ctrl+Shift+S`).
2. **AutoClicker**: Enter your desired interval in milliseconds, pick a target screen coordinate (optional), and press your hotkey to start spamming!
3. **Macros**: Switch to the Macro tab. Press your Record hotkey to start capturing inputs. Play a game, type a sentence, or navigate a UI. Press the hotkey again to stop. Press your Playback hotkey to watch AERO repeat your actions flawlessly.

## 🛠️ Development & Building

AERO is built on the [Tauri](https://tauri.app/) framework. To build it from source:

### Prerequisites
- [Node.js](https://nodejs.org/) (v16+)
- [Rust](https://www.rust-lang.org/tools/install)
- Windows Build Tools (C++ Build Tools)

### Build Instructions
```bash
# 1. Clone the repository
git clone https://github.com/jt-ito/AERO-AutoClicker.git
cd AERO-AutoClicker

# 2. Install dependencies
npm install

# 3. Run the development server (Hot-reloading)
npm run tauri dev

# 4. Build the final release executables
npm run tauri build
```
*The compiled `.exe` and installers will be located in `src-tauri/target/release/`.*

## 🤝 Contributing
Contributions, issues, and feature requests are always welcome! Feel free to check the [issues page](https://github.com/jt-ito/AERO-AutoClicker/issues) if you want to contribute.

## 📝 License
This project is open-source and available under the standard MIT License.
