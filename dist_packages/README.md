# Clevo Keyboard Driver & GUI Packages (v1.0.0)

Pre-built packages and binaries supporting Linux Kernel 7.3+, GNOME, KDE Plasma, XFCE, and other desktop environments.

## 📦 Available Packages

| Distribution / Target | Package Location | Installation Command |
|---|---|---|
| **Ubuntu / Debian / Pop!_OS / Mint** | `dist_packages/deb/clevo-keyboard-1.0.0.deb` | `sudo apt install ./dist_packages/deb/clevo-keyboard-1.0.0.deb` |
| **Fedora / RHEL / CentOS** | `dist_packages/rpm/clevo-keyboard-1.0.0-1.noarch.rpm` | `sudo dnf install ./dist_packages/rpm/clevo-keyboard-1.0.0-1.noarch.rpm` |
| **openSUSE** | `dist_packages/rpm/clevo-keyboard-1.0.0-1.noarch.rpm` | `sudo zypper install ./dist_packages/rpm/clevo-keyboard-1.0.0-1.noarch.rpm` |
| **Arch Linux / Manjaro** | `dist_packages/arch/PKGBUILD` | `cd dist_packages/arch && makepkg -si` |
| **Any Linux Distro (Universal Binary)** | `dist_packages/standalone/clevo-keyboard-gui` | `./dist_packages/standalone/clevo-keyboard-gui` |

---

## 🎨 Features
- **15 Authentic Clevo Colors**: Blue, Red, Magenta, Green, Cyan, Yellow, White, Orange, Sky Blue, Lime, Pink, Aqua Mint, Amber Gold, Violet, Crimson.
- **Strict Hardware Safety**: Strictly adheres to OEM hardware modes (Mode 0 static lighting & brightness control). No experimental registers, firmware writes, or unsupported breathe modes.
- **Native Desktop Adaptive UI**: Built with pure Qt6 system styling. Automatically adapts to dark and light palettes across KDE Plasma (Breeze), GNOME (Adwaita/Yaru), and XFCE.
- **Monochrome Symbolic Tray Icon**: Follows FreeDesktop specifications, automatically adapting to dark and light panels.
- **Lightweight**: Zero idle background threads, instant launch, 0% CPU footprint.
- **Command Line Interface (CLI)**: Full support for scripting and keyboard shortcut keybindings (`--color`, `--brightness`, `--off`, `--on`, `--status`).
