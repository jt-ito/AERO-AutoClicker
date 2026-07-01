<div align="center">
  <img src="src-tauri/icons/128x128.png" alt="AERO Logo" width="128">
  
  # AERO AutoClicker
  
  **A blazing fast, modern, and reliable autoclicker built with Rust & Tauri.**
  
  [![Release](https://img.shields.io/github/v/release/jt-ito/AERO-AutoClicker?style=for-the-badge)](https://github.com/jt-ito/AERO-AutoClicker/releases)
  [![Platform](https://img.shields.io/badge/Platform-Windows-blue?style=for-the-badge)]()
  
</div>

## ✨ Features

- 🎨 **Modern Interface**: A beautiful glassmorphic UI with full support for Dark and Light modes.
- 🎯 **Target Specific Windows**: Don't just click blindly! Select an exact target window to interact with.
- ⌨️ **Global Hotkeys**: Start and stop clicking instantly with a fully customizable global hotkey (works everywhere).
- 👻 **Background Mode**: Send clicks via `PostMessage` without hijacking your physical mouse, allowing you to use your PC while it clicks in the background!
- 📍 **Precision Coordinate Picker**: Interactively pick the exact X/Y coordinates on your screen or within a window.
- 🚀 **Blazing Fast**: Written in pure Rust. Capable of insanely high click speeds while featuring built-in CPU yielding to prevent system freezes.
- 🖱️ **Double Clicks**: Native double-click toggle support.

## 🚀 Getting Started

### Installation

1. Head over to the [Releases page](https://github.com/jt-ito/AERO-AutoClicker/releases).
2. Download the latest `aero-clicker.exe` file.
3. Run it and enjoy! No installation required.

### Development

If you want to build AERO from source, you'll need [Node.js](https://nodejs.org/) and [Rust](https://rustup.rs/) installed.

```bash
# Clone the repository
git clone https://github.com/jt-ito/AERO-AutoClicker.git
cd AERO-AutoClicker

# Install dependencies
npm install

# Run in development mode
npm run tauri dev

# Build for production
npm run tauri build
```

## 💡 How to use

1. **Select Window**: Use the dropdown to pick the specific application window you want to click on.
2. **Set Interval**: Choose your clicking speed (in milliseconds).
3. **Pick Coordinates**: Click the "Pick Coords" button, then click on the target window to set exact X/Y coordinates. Leave as `0, 0` for the center of the window.
4. **Customize Hotkey**: Click "Record" and press your desired key combination to toggle the clicker.
5. **Start**: Press your hotkey or click the "Start" button!

---
*Built with ❤️ using [Tauri](https://tauri.app/)*
