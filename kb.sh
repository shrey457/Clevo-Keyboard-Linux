#!/usr/bin/env bash
# ==============================================================================
# Clevo Keyboard Backlight Installer & Driver Manager
# Compatible with Linux Kernel 7.3+ (Ubuntu 26.10, Fedora, Arch, openSUSE)
# ==============================================================================

set -e

if [ "$EUID" -ne 0 ]; then
  echo "[-] This script requires root privileges. Please run with: sudo $0 $@"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_NAME="$(sed -n 's/^PACKAGE_NAME=["'\'']\?\([^"'\''\n]*\)["'\'']\?/\1/p' "$SCRIPT_DIR/dkms.conf" 2>/dev/null || echo "clevo-keyboard")"
PACKAGE_VER="$(sed -n 's/^PACKAGE_VERSION=["'\'']\?\([^"'\''\n]*\)["'\'']\?/\1/p' "$SCRIPT_DIR/dkms.conf" 2>/dev/null || echo "1.0.0")"
DKMS_DEST="/usr/src/${PACKAGE_NAME}-${PACKAGE_VER}"

# ── Uninstall Option ────────────────────────────────────────────────────────
if [ "$1" == "--uninstall" ] || [ "$1" == "-u" ]; then
  echo "[*] Uninstalling Clevo / Tuxedo keyboard drivers..."
  
  # Unload kernel modules in proper dependency order
  modprobe -r clevo_acpi clevo_wmi tuxedo_io uniwill_wmi 2>/dev/null || true
  modprobe -r tuxedo_keyboard 2>/dev/null || true
  
  # Remove DKMS module (both current and legacy)
  dkms remove -m "$PACKAGE_NAME" -v "$PACKAGE_VER" --all 2>/dev/null || true
  dkms remove -m tuxedo-keyboard -v 3.2.10 --all 2>/dev/null || true
  rm -rf "$DKMS_DEST" /usr/src/tuxedo-keyboard-3.2.10
  
  # Remove system configurations
  rm -f /etc/modules-load.d/tuxedo.conf
  rm -f /etc/modprobe.d/tuxedo_keyboard.conf
  rm -f /etc/udev/rules.d/99-clevo-backlight.rules
  
  # Remove GUI files
  rm -f /usr/local/bin/clevo-keyboard-gui
  rm -f /usr/share/applications/clevo-keyboard-gui.desktop
  rm -f /usr/share/icons/hicolor/scalable/apps/clevo-keyboard.svg
  rm -f /usr/share/icons/hicolor/scalable/status/clevo-keyboard-tray-symbolic.svg
  gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor 2>/dev/null || true
  
  udevadm control --reload-rules 2>/dev/null || true
  echo "[+] Uninstallation complete."
  exit 0
fi

# ── Dependency Installation ────────────────────────────────────────────────
install_packages() {
  echo "[*] Detecting Linux distribution and installing dependencies..."
  if [ -f /etc/arch-release ]; then
    echo "    Detected: Arch Linux / Manjaro"
    pacman -Sy --noconfirm git dkms base-devel linux-headers python-pyqt6
  elif [ -f /etc/debian_version ]; then
    echo "    Detected: Debian / Ubuntu / Kubuntu"
    apt update && apt install -y git dkms build-essential linux-headers-$(uname -r) python3 python3-pyqt6
  elif [ -f /etc/redhat-release ]; then
    echo "    Detected: Fedora / RHEL / CentOS"
    dnf -y install git dkms kernel-headers kernel-devel gcc make python3 python3-pyqt6
  elif [ -f /etc/os-release ] && grep -qi "suse" /etc/os-release; then
    echo "    Detected: openSUSE"
    zypper in -y git dkms kernel-headers kernel-devel gcc make python3-qt6
  else
    echo "[!] Unrecognized distribution. Ensuring basic tools..."
  fi
}

echo "=================================================================="
echo "  Clevo Keyboard Backlight & Kernel 7.3+ Driver Installer"
echo "=================================================================="

# 1. Install required packages
install_packages

# 2. Prepare Source Directory
if [ ! -f "$SCRIPT_DIR/Makefile" ] || [ ! -d "$SCRIPT_DIR/src" ]; then
  echo "[-] Error: Installer must be run from within the clevo-keyboard directory."
  exit 1
fi

echo "[*] Cleaning any stale build artifacts..."
make -C "$SCRIPT_DIR" clean >/dev/null 2>&1 || true

# 3. Clean any existing DKMS registrations
echo "[*] Registering driver with DKMS for kernel auto-updates..."
dkms remove -m "$PACKAGE_NAME" -v "$PACKAGE_VER" --all 2>/dev/null || true
dkms remove -m tuxedo-keyboard -v 3.2.10 --all 2>/dev/null || true
rm -rf "$DKMS_DEST" /usr/src/tuxedo-keyboard-3.2.10

# 4. Copy current patched source tree to /usr/src
mkdir -p "$DKMS_DEST"
cp -rf "$SCRIPT_DIR"/Makefile "$SCRIPT_DIR"/dkms.conf "$SCRIPT_DIR"/src "$DKMS_DEST"/

# 5. Build and install DKMS module
echo "[*] Compiling module against kernel $(uname -r)..."
dkms add -m "$PACKAGE_NAME" -v "$PACKAGE_VER"
dkms build -m "$PACKAGE_NAME" -v "$PACKAGE_VER"
dkms install -m "$PACKAGE_NAME" -v "$PACKAGE_VER" --force

# 6. Configure Autoloading on boot
echo "[*] Configuring module autoloading in /etc/modules-load.d/tuxedo.conf..."
mkdir -p /etc/modules-load.d
cat << 'EOF' > /etc/modules-load.d/tuxedo.conf
clevo_acpi
clevo_wmi
tuxedo_keyboard
tuxedo_io
uniwill_wmi
EOF

# 7. Configure Modprobe options (force_load=1 for non-Tuxedo Clevo/Acer/OEM laptops)
echo "[*] Setting default modprobe options in /etc/modprobe.d/tuxedo_keyboard.conf..."
mkdir -p /etc/modprobe.d
cat << 'EOF' > /etc/modprobe.d/tuxedo_keyboard.conf
options tuxedo_keyboard force_load=1
EOF

# 8. Configure Udev rules (allows users to adjust lighting without sudo)
echo "[*] Setting up udev rules for non-root backlight access..."
mkdir -p /etc/udev/rules.d
cat << 'EOF' > /etc/udev/rules.d/99-clevo-backlight.rules
# Clevo / Tuxedo keyboard backlight SysFS permissions for non-root desktop users
SUBSYSTEM=="leds", KERNEL=="*kbd_backlight*", ACTION=="add", RUN+="/bin/chmod 0666 /sys%p/brightness /sys%p/multi_intensity"
SUBSYSTEM=="platform", DRIVERS=="clevo_keyboard|tuxedo_keyboard", ACTION=="add", RUN+="/bin/chmod 0666 /sys%p/kbd_backlight_mode"
EOF
udevadm control --reload-rules 2>/dev/null || true
udevadm trigger 2>/dev/null || true

# 9. Install Native GUI Application and Desktop Launcher
echo "[*] Installing Clevo Keyboard Control GUI..."
if [ -f "$SCRIPT_DIR/clevo-keyboard-gui.py" ]; then
  cp -f "$SCRIPT_DIR/clevo-keyboard-gui.py" /usr/local/bin/clevo-keyboard-gui
  chmod 755 /usr/local/bin/clevo-keyboard-gui
fi

if [ -f "$SCRIPT_DIR/clevo-keyboard.svg" ]; then
  mkdir -p /usr/share/icons/hicolor/scalable/apps
  cp -f "$SCRIPT_DIR/clevo-keyboard.svg" /usr/share/icons/hicolor/scalable/apps/clevo-keyboard.svg
  chmod 644 /usr/share/icons/hicolor/scalable/apps/clevo-keyboard.svg
fi

if [ -f "$SCRIPT_DIR/clevo-keyboard-tray-symbolic.svg" ]; then
  mkdir -p /usr/share/icons/hicolor/scalable/status
  cp -f "$SCRIPT_DIR/clevo-keyboard-tray-symbolic.svg" /usr/share/icons/hicolor/scalable/status/clevo-keyboard-tray-symbolic.svg
  chmod 644 /usr/share/icons/hicolor/scalable/status/clevo-keyboard-tray-symbolic.svg
fi
gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor 2>/dev/null || true

mkdir -p /usr/share/applications
cat << 'EOF' > /usr/share/applications/clevo-keyboard-gui.desktop
[Desktop Entry]
Name=Clevo Keyboard Backlight
GenericName=Keyboard Lighting Control
Comment=Configure RGB keyboard lighting, 15 standard colors, and brightness
Exec=/usr/local/bin/clevo-keyboard-gui
Icon=clevo-keyboard
Terminal=false
Type=Application
Categories=Settings;HardwareSettings;Utility;Qt;
Keywords=clevo;tuxedo;keyboard;backlight;rgb;lighting;
EOF
chmod 644 /usr/share/applications/clevo-keyboard-gui.desktop

# 10. Load kernel modules into running system
echo "[*] Loading kernel modules..."
modprobe -r clevo_acpi clevo_wmi tuxedo_io uniwill_wmi 2>/dev/null || true
modprobe -r tuxedo_keyboard 2>/dev/null || true
modprobe tuxedo_keyboard force_load=1 2>/dev/null || true
modprobe clevo_acpi 2>/dev/null || true
modprobe clevo_wmi 2>/dev/null || true
modprobe tuxedo_io 2>/dev/null || true
modprobe uniwill_wmi 2>/dev/null || true

# Apply permissions on active sysfs nodes immediately (directories need +x to be searchable)
chmod -R a+rX /sys/devices/platform/tuxedo_keyboard* 2>/dev/null || true
chmod a+rw /sys/class/leds/*kbd_backlight*/* 2>/dev/null || true
chmod a+rw /sys/devices/platform/tuxedo_keyboard*/kbd_backlight_mode 2>/dev/null || true
chmod a+rw /sys/devices/platform/clevo_keyboard*/kbd_backlight_mode 2>/dev/null || true

echo "=================================================================="
echo "  [+] Installation Successful!"
echo "  - Drivers installed via DKMS for Linux Kernel $(uname -r)"
echo "  - Launch the GUI anytime from your Application Menu or:"
echo "      clevo-keyboard-gui"
echo "  - CLI commands:"
echo "      clevo-keyboard-gui --color cyan"
echo "      clevo-keyboard-gui --brightness 150"
echo "      clevo-keyboard-gui --off"
echo "      clevo-keyboard-gui --on"
echo "=================================================================="
exit 0
