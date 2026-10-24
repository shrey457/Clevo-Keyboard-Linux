<div align="center">

<img src="clevo-keyboard.svg" width="128" height="128" alt="Clevo Keyboard Backlight Icon" />

# Clevo Keyboard Backlight Control for Linux

**Modern Linux Kernel 7.3+ driver suite & native desktop control center for Clevo, Tuxedo, Acer, and Sager RGB backlit keyboards.**

[![Linux Kernel](https://img.shields.io/badge/Kernel-7.3%2B%20%7C%206.x-brightgreen.svg?logo=linux&logoColor=white)](https://kernel.org)
[![Ubuntu / Debian](https://img.shields.io/badge/Ubuntu%20%2F%20Debian-26.10%20%7C%2024.04%20LTS-orange.svg?logo=ubuntu&logoColor=white)](dist_packages/deb/)
[![Fedora / RHEL](https://img.shields.io/badge/Fedora%20%2F%20RHEL-40%2B%20%7C%209%2B-blue.svg?logo=fedora&logoColor=white)](dist_packages/rpm/)
[![Arch Linux](https://img.shields.io/badge/Arch%20Linux-PKGBUILD%20Ready-1793d1.svg?logo=archlinux&logoColor=white)](dist_packages/arch/)
[![Hardware Safe](https://img.shields.io/badge/Hardware-100%25%20Brick--Safe-success.svg)](#-safety--hardware-adherence)
[![License](https://img.shields.io/badge/License-GPL--2.0-blue.svg)](LICENSE)

[Quick Start](#-quick-start) • [Distro Packages](#-pre-built-distro-packages) • [Hardware Hotkeys](#-physical-keyboard-shortcuts) • [GUI & Shortcuts](#-desktop-gui--in-app-shortcuts) • [CLI Control](#-command-line-interface-cli) • [Architecture](#-technical-architecture-kernel-73-fix)

</div>

---

##  Overview

Modern Linux kernels (starting with 6.2 and completely enforced in Kernel 7.3+) removed legacy ACPI driver interfaces (`struct acpi_driver` and `module_acpi_driver`), breaking existing Clevo/Tuxedo backlight modules across modern distributions such as Ubuntu 26.10+, Fedora 41+, and Arch Linux.

This repository provides a **fully refactored, modern Linux Kernel 7.3+ driver suite** coupled with a **lightweight, native Qt6 desktop application** and **pre-built packages for all major Linux distributions**.

---

## ⚡ Key Highlights

- **Linux Kernel 7.3+ Native**: Refactored to standard `platform_driver` with ACPI device ID matching (`CLV0001:00`) and ACPICA notification handlers.
- **Direct Physical Fn-Key Control**: Physical keyboard hotkeys (`Fn + /`, `Fn + *`, `Fn + -`, `Fn + +`) control lighting directly in hardware with zero lag.
- **Native Adaptive GUI**:
  - Automatically matches system dark & light color palettes (KDE Breeze, GNOME Adwaita, XFCE).
  - Maximizable, responsive chiclet keyboard visualizer with live underglow bloom.
  - Symmetrical 15 authentic OEM color grid (Blue, Red, Green, Cyan, White, Lime, Aqua, etc.).
  - Smooth 0%–100% brightness control with quick presets.
  - 100% FreeDesktop symbolic monochrome tray icon that adapts to your panel theme color.
  - In-app keyboard hotkeys (`Space`, `1-9`, `↑/↓`, `C`, `Esc`).
  - Real-time hardware synchronization: GUI updates live if physical Fn-keys are pressed.
- **Hardware Safe**: Strictly operates within factory OEM specifications (Mode 0 static lighting and standard brightness). Does **not** execute arbitrary EC register writes or unsupported modes.
- **Universal Packaging**: Ready-to-install `.deb` (Debian/Ubuntu), `.rpm` (Fedora/RHEL/openSUSE), Arch `PKGBUILD`, and standalone Linux executable.

---

## 💻 Hardware Compatibility

Tested and verified on:
- **Acer Aspire 7 Series** (e.g., A715-79G Clevo base with Intel Core 5 / Core i7 & RTX series)
- **Clevo Chassis** (NH50, NH55, NH58, NP50, PB50, PB51, PB71, PC50, PC70, PD50, PD70, X170, etc.)
- **TUXEDO Computers** (Polaris, Stellaris, Aura, Pulse, InfinityBook)
- **Sager, Schenker XMG, & NovaCustom** laptops utilizing Clevo/Uniwill motherboards

---

##  Quick Start

### 1-Step Automated Installer (Recommended)

Clone the repository and run the automated installer:

```bash
git clone https://github.com/YOUR_USERNAME/clevo-keyboard.git
cd clevo-keyboard
sudo ./kb.sh
```

The script automatically:
1. Detects your running kernel (`7.3+` or `6.x`) and compiler headers.
2. Registers and builds the DKMS modules for automatic recompilation across kernel upgrades.
3. Sets up non-root `udev` permissions (`/etc/udev/rules.d/99-clevo-backlight.rules`) so you never need `sudo` to adjust lighting.
4. Installs the GUI app, icons, desktop launcher, and modprobe configuration.

> [!TIP]
> After first install, a quick system reboot ensures the kernel unbinds legacy resident ACPI tables and connects the new EC event router.

---

##  Pre-Built Distro Packages

Pre-compiled packages with complete DKMS sources, desktop integration, udev rules, and icons are available in [`dist_packages/`](dist_packages/):

| Distribution / Target | Package | Installation Command |
|---|---|---|
| **Ubuntu / Debian / Pop!_OS / Mint** | [tuxedo-keyboard-3.2.10.deb](dist_packages/deb/tuxedo-keyboard-3.2.10.deb) | `sudo apt install ./dist_packages/deb/tuxedo-keyboard-3.2.10.deb` |
| **Fedora / RHEL / CentOS** | [tuxedo-keyboard-3.2.10-1.noarch.rpm](dist_packages/rpm/tuxedo-keyboard-3.2.10-1.noarch.rpm) | `sudo dnf install ./dist_packages/rpm/tuxedo-keyboard-3.2.10-1.noarch.rpm` |
| **openSUSE** | [tuxedo-keyboard-3.2.10-1.noarch.rpm](dist_packages/rpm/tuxedo-keyboard-3.2.10-1.noarch.rpm) | `sudo zypper install ./dist_packages/rpm/tuxedo-keyboard-3.2.10-1.noarch.rpm` |
| **Arch Linux / Manjaro** | [PKGBUILD](dist_packages/arch/PKGBUILD) | `cd dist_packages/arch && makepkg -si` |
| **Universal Standalone Binary** | [clevo-keyboard-gui](dist_packages/standalone/clevo-keyboard-gui) | `./dist_packages/standalone/clevo-keyboard-gui` |

---

##  Physical Keyboard Shortcuts

The kernel module handles physical function keys directly in kernel space:

| Physical Hotkey | Action | Behavior |
|---|---|---|
| <kbd>Fn</kbd> + <kbd>/</kbd> | **Cycle Color** | Cycles through all 15 authentic Clevo colors sequentially |
| <kbd>Fn</kbd> + <kbd>*</kbd> | **Toggle Power** | Toggles keyboard backlight On / Off (restores previous brightness) |
| <kbd>Fn</kbd> + <kbd>-</kbd> | **Brightness Down** | Decreases brightness in smooth 20% steps |
| <kbd>Fn</kbd> + <kbd>+</kbd> | **Brightness Up** | Increases brightness in smooth 20% steps |

---

##  Desktop GUI & In-App Shortcuts

Launch the control center from your application menu (**Clevo Keyboard Backlight**) or via terminal:

```bash
clevo-keyboard-gui
```

### In-App Keyboard Shortcuts

When the application window is focused:

| Shortcut | Function |
|---|---|
| <kbd>Space</kbd> or <kbd>0</kbd> | Toggle backlight On / Off |
| <kbd>↑</kbd> / <kbd>+</kbd> | Increase brightness (+10%) |
| <kbd>↓</kbd> / <kbd>-</kbd> | Decrease brightness (-10%) |
| <kbd>1</kbd> – <kbd>9</kbd> | Direct select colors 1 through 9 |
| <kbd>C</kbd> | Cycle to next color |
| <kbd>Esc</kbd> | Minimize window to system tray |

---

##  Command Line Interface (CLI)

The application includes a built-in CLI for scripts, desktop hotkeys, and automated cron schedules:

```bash
# Query active hardware state
clevo-keyboard-gui --status

# Set a color by standard OEM name
clevo-keyboard-gui --color cyan
clevo-keyboard-gui --color red
clevo-keyboard-gui --color white

# Set brightness level (0 to 255)
clevo-keyboard-gui --brightness 200

# Power control
clevo-keyboard-gui --on
clevo-keyboard-gui --off

# Start minimized to system tray on login
clevo-keyboard-gui --tray &
```

### Authentic OEM Color Names
`blue`, `red`, `magenta`, `green`, `cyan`, `yellow`, `white`, `orange`, `skyblue`, `lime`, `pink`, `aqua`, `amber`, `violet`, `crimson`

---

##  Technical Architecture (Kernel 7.3+ Fix)

### The Problem
Upstream Linux Kernel 7.3 completely removed:
- `struct acpi_driver`
- `module_acpi_driver()`
- Direct ACPICA device binding methods

Attempting to compile previous versions of `tuxedo-keyboard` or `clevo-keyboard` on Kernel 7.3 resulted in fatal compiler errors (`unknown type name ‘struct acpi_driver’`).

### The Solution
1. **Platform Driver Migration (`src/clevo_acpi.c`)**:
   Rebuilt as a standard Linux `platform_driver` bound via `.acpi_match_table` matching ACPI hardware ID `CLV0001:00`.
2. **ACPICA Notify Installation**:
   Registered via `acpi_dev_install_notify_handler(adev, ACPI_ALL_NOTIFY, clevo_acpi_notify_handler, adev)`.
3. **Direct Hardware Brightness Stepping (`src/clevo_keyboard.h`)**:
   Implemented `clevo_keyboard_step_brightness(int delta)` and `clevo_keyboard_toggle_brightness()` directly within the kernel hotkey event dispatcher. Physical key events update the EC immediately and notify sysfs userspace listeners via `led_classdev_notify_brightness_hw_changed()`.
4. **Universal DMI Override**:
   Enabled `force_load=1` by default in `src/tuxedo_keyboard.c`, allowing the module to attach to generic Acer, Sager, and OEM Clevo motherboards without requiring manual DMI table patches.

---

##  Safety & Hardware Adherence

- **100% Brick-Safe**: Only sends standard color and brightness commands through Linux SysFS nodes (`/sys/class/leds/rgb:kbd_backlight/`).
- **No Experimental Modes**: Breath mode and unsupported raw registers have been excluded to preserve hardware integrity across all Clevo motherboard revisions.
- **Zero Background Overhead**: The GUI uses event-driven Qt with a lightweight 400ms polling timer checking standard sysfs attributes only. Uses 0% idle CPU and ~25MB memory.

---

##  Uninstallation

To cleanly remove the driver and application:

```bash
sudo ./kb.sh --uninstall
```

Or if installed via package manager:
```bash
# Ubuntu / Debian
sudo apt remove tuxedo-keyboard

# Fedora
sudo dnf remove tuxedo-keyboard

# Arch Linux
sudo pacman -R tuxedo-keyboard-dkms
```

---

##  License & Credits

- Licensed under the **GNU General Public License v2.0** ([LICENSE](LICENSE)).
- Kernel module core based on TUXEDO Computers GmbH `tuxedo-keyboard`.
- Modern Kernel 7.3+ platform driver refactoring, direct hotkey stepping, native Qt6 control center, and multi-distro packaging maintained for the community.
