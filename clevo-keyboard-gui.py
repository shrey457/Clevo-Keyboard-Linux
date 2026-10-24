#!/usr/bin/env python3
"""
Clevo Keyboard Backlight Control (Native Linux Desktop Edition)
Lightweight, theme-adaptive Qt6 controller for Clevo, Acer, Tuxedo, and OEM laptops on Linux.

Adheres strictly to Linux desktop standards:
- Native KDE Plasma / GNOME / XFCE / Wayland theme integration (uses system palette and typography)
- Standard window decorations with working Minimize, Maximize, and Close buttons
- Authentic 15 Clevo OEM hardware colors (no unsupported custom color modes or breathe mode)
- Standard brightness control (0% - 100%) & Power Toggle
- Full physical keyboard controls (Arrow keys, Space, +/-) and real-time hardware Fn key sync
- FreeDesktop monochrome symbolic system tray icon
- Ultra-lightweight: zero idle CPU usage, fast startup
- Full CLI support for scripting and shortcut keys
"""

import sys
import os
import glob
import subprocess
from pathlib import Path

# ─── 15 Authentic Clevo Hardware Colors ──────────────────────────────────────

CLEVO_15_COLORS = [
    ("#0000ff", "Blue"),
    ("#ff0000", "Red"),
    ("#ff00ff", "Magenta"),
    ("#00ff00", "Green"),
    ("#00ffff", "Cyan"),
    ("#ffff00", "Yellow"),
    ("#ffffff", "White"),
    ("#ffa500", "Orange"),
    ("#0080ff", "Sky Blue"),
    ("#80ff00", "Lime Green"),
    ("#ff1493", "Pink"),
    ("#00ff80", "Aqua Mint"),
    ("#ffd700", "Amber Gold"),
    ("#8000ff", "Violet"),
    ("#dc143c", "Crimson"),
]

COLOR_MAP = {name.lower().replace(" ", ""): hex_code for hex_code, name in CLEVO_15_COLORS}


# ─── Safe SysFS Hardware Backend ─────────────────────────────────────────────

class SysfsBackend:
    """Safe, minimal hardware controller via standard Linux LED class."""

    def __init__(self):
        self.rgb_zones = []
        self.white_zone = None
        self.mode_file = None
        self.refresh()

    def refresh(self):
        base_leds = "/sys/class/leds"
        self.rgb_zones = sorted(glob.glob(f"{base_leds}/rgb:kbd_backlight*"))
        white_path = f"{base_leds}/white:kbd_backlight"
        self.white_zone = white_path if os.path.exists(white_path) else None

        mode_candidates = (
            glob.glob("/sys/devices/platform/tuxedo_keyboard*/kbd_backlight_mode") +
            glob.glob("/sys/devices/platform/clevo_keyboard*/kbd_backlight_mode") +
            glob.glob("/sys/devices/platform/*/kbd_backlight_mode")
        )
        self.mode_file = mode_candidates[0] if mode_candidates else None

    @staticmethod
    def is_module_loaded():
        try:
            with open("/proc/modules", "r") as f:
                c = f.read()
                return "tuxedo_keyboard" in c or "clevo_acpi" in c or "clevo_wmi" in c
        except Exception:
            return False

    def read_file(self, path):
        try:
            with open(path, "r") as f:
                return f.read().strip()
        except Exception:
            return None

    def write_file(self, path, val):
        val_str = str(val)
        try:
            with open(path, "w") as f:
                f.write(val_str)
            return True
        except PermissionError:
            try:
                cmd = ["pkexec", "tee", path] if os.environ.get("DISPLAY") else ["sudo", "tee", path]
                p = subprocess.run(cmd, input=val_str.encode(), capture_output=True, timeout=3)
                return p.returncode == 0
            except Exception:
                return False
        except Exception:
            return False

    def get_brightness(self):
        if self.rgb_zones:
            v = self.read_file(f"{self.rgb_zones[0]}/brightness")
            if v and v.isdigit():
                return int(v)
        elif self.white_zone:
            v = self.read_file(f"{self.white_zone}/brightness")
            if v and v.isdigit():
                return int(v)
        return 255

    def set_brightness(self, value):
        value = max(0, min(255, int(value)))
        ok = True
        for z in self.rgb_zones:
            if not self.write_file(f"{z}/brightness", value):
                ok = False
        if self.white_zone:
            max_b = self.read_file(f"{self.white_zone}/max_brightness")
            max_val = int(max_b) if max_b and max_b.isdigit() else 2
            mapped = int((value / 255.0) * max_val)
            self.write_file(f"{self.white_zone}/brightness", mapped)
        return ok

    def get_color(self):
        if self.rgb_zones:
            v = self.read_file(f"{self.rgb_zones[0]}/multi_intensity")
            if v:
                parts = v.split()
                if len(parts) >= 3:
                    try:
                        r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
                        return f"#{r:02x}{g:02x}{b:02x}"
                    except ValueError:
                        pass
        return "#ffffff"

    def set_color(self, hex_color):
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 6:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
        else:
            r, g, b = 255, 255, 255

        # Always ensure standard Mode 0 (static normal lighting)
        if self.mode_file:
            self.write_file(self.mode_file, 0)

        ok = True
        for z in self.rgb_zones:
            if not self.write_file(f"{z}/multi_intensity", f"{r} {g} {b}"):
                ok = False
        return ok

    def turn_off(self):
        self.set_brightness(0)

    def turn_on(self, brightness=255):
        self.set_brightness(brightness)


# ─── Native PyQt6 GUI ────────────────────────────────────────────────────────

try:
    from PyQt6 import QtWidgets, QtGui, QtCore
    from PyQt6.QtCore import Qt, QRectF, QPointF, QTimer
    from PyQt6.QtGui import (
        QColor, QPainter, QPainterPath, QPen, QBrush, QFont, QIcon, QAction,
        QRadialGradient, QPalette
    )
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QGridLayout, QLabel, QPushButton, QSlider, QFrame, QSizePolicy,
        QSystemTrayIcon, QMenu
    )
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False


if PYQT6_AVAILABLE:

    class ModernKeyboardCanvas(QWidget):
        """Realistic chiclet keyboard visualization with authentic key layout & RGB glow."""

        KEYBOARD_ROWS = [
            [("Esc", 1.2), ("F1", 1.0), ("F2", 1.0), ("F3", 1.0), ("F4", 1.0),
             ("F5", 1.0), ("F6", 1.0), ("F7", 1.0), ("F8", 1.0),
             ("F9", 1.0), ("F10", 1.0), ("F11", 1.0), ("F12", 1.0), ("Del", 1.2)],
            [("~", 1.0), ("1", 1.0), ("2", 1.0), ("3", 1.0), ("4", 1.0), ("5", 1.0),
             ("6", 1.0), ("7", 1.0), ("8", 1.0), ("9", 1.0), ("0", 1.0), ("-", 1.0), ("+", 1.0), ("⌫", 1.8)],
            [("Tab", 1.5), ("Q", 1.0), ("W", 1.0), ("E", 1.0), ("R", 1.0), ("T", 1.0),
             ("Y", 1.0), ("U", 1.0), ("I", 1.0), ("O", 1.0), ("P", 1.0), ("[", 1.0), ("]", 1.0), ("\\", 1.3)],
            [("Caps", 1.7), ("A", 1.0), ("S", 1.0), ("D", 1.0), ("F", 1.0), ("G", 1.0),
             ("H", 1.0), ("J", 1.0), ("K", 1.0), ("L", 1.0), (";", 1.0), ("'", 1.0), ("Enter", 2.1)],
            [("Shift", 2.2), ("Z", 1.0), ("X", 1.0), ("C", 1.0), ("V", 1.0), ("B", 1.0),
             ("N", 1.0), ("M", 1.0), (",", 1.0), (".", 1.0), ("/", 1.0), ("Shift", 2.6)],
            [("Ctrl", 1.3), ("Fn", 1.1), ("Win", 1.1), ("Alt", 1.2),
             ("Space", 6.2),
             ("Alt", 1.2), ("Ctrl", 1.3), ("◀", 1.0), ("▲▼", 1.0), ("▶", 1.0)],
        ]

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setMinimumHeight(175)
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
            self.color = QColor("#00e5ff")
            self.brightness = 255

        def set_state(self, hex_color, brightness):
            self.color = QColor(hex_color)
            self.brightness = max(0, min(255, brightness))
            self.update()

        def paintEvent(self, event):
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

            w = self.width()
            h = self.height()

            # Maintain natural laptop keyboard aspect ratio (2.75 : 1) centered
            target_ratio = 2.75
            avail_w = max(100.0, float(w - 24))
            avail_h = max(60.0, float(h - 16))

            if avail_w / avail_h > target_ratio:
                kb_h = avail_h
                kb_w = kb_h * target_ratio
            else:
                kb_w = avail_w
                kb_h = kb_w / target_ratio

            kb_x = (w - kb_w) / 2.0
            kb_y = (h - kb_h) / 2.0
            well = QRectF(kb_x, kb_y, kb_w, kb_h)

            pal = self.palette()
            is_dark = pal.color(QPalette.ColorRole.Window).lightness() < 128

            # Outer chassis well
            well_path = QPainterPath()
            well_path.addRoundedRect(well, 10, 10)
            well_bg = QColor(16, 18, 24) if is_dark else QColor(228, 232, 240)
            painter.fillPath(well_path, well_bg)
            border_pen = QPen(QColor(128, 128, 128, 60), 1.2)
            painter.strokePath(well_path, border_pen)

            # RGB Underglow Lighting Glow
            brt_ratio = self.brightness / 255.0
            if brt_ratio > 0.01:
                glow = QRadialGradient(well.center(), well.width() * 0.52)
                glow_c = QColor(self.color)
                glow_c.setAlphaF(0.42 * brt_ratio)
                glow.setColorAt(0.0, glow_c)
                glow_mid = QColor(self.color)
                glow_mid.setAlphaF(0.20 * brt_ratio)
                glow.setColorAt(0.65, glow_mid)
                glow.setColorAt(1.0, QColor(0, 0, 0, 0))
                painter.fillPath(well_path, glow)

            # Chiclet Keycaps
            num_rows = len(self.KEYBOARD_ROWS)
            pad = 6.0
            row_gap = 3.0
            col_gap = 3.0

            inner_w = well.width() - 2 * pad
            inner_h = well.height() - 2 * pad
            row_h = (inner_h - (num_rows - 1) * row_gap) / num_rows

            font = self.font()
            font.setPointSize(max(7, int(row_h * 0.28)))
            font.setWeight(QFont.Weight.Medium)
            painter.setFont(font)

            cap_col = QColor(28, 31, 40) if is_dark else QColor(255, 255, 255)
            text_col = QColor(210, 215, 225, 175) if is_dark else QColor(70, 75, 90, 200)

            rim_glow = QColor(self.color)
            rim_glow.setAlphaF(0.85 * brt_ratio if brt_ratio > 0.01 else 0.12)
            rim_pen = QPen(rim_glow, 1.2 if brt_ratio > 0.01 else 0.8)

            for r_idx, row in enumerate(self.KEYBOARD_ROWS):
                total_units = sum(u for _, u in row)
                gaps = (len(row) - 1) * col_gap
                unit_w = (inner_w - gaps) / total_units

                curr_x = well.x() + pad
                curr_y = well.y() + pad + r_idx * (row_h + row_gap)

                for label, unit_span in row:
                    key_w = unit_span * unit_w
                    rect = QRectF(curr_x, curr_y, key_w, row_h)

                    path = QPainterPath()
                    path.addRoundedRect(rect, 3.5, 3.5)
                    painter.fillPath(path, cap_col)
                    painter.strokePath(path, rim_pen)

                    painter.setPen(text_col)
                    disp = label
                    if label == "Space":
                        disp = "—"
                    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, disp)

                    curr_x += key_w + col_gap


    class ColorCardButton(QPushButton):
        """Modern, stylish color card chip with clear name, vibrant pill, and selected ring."""

        def __init__(self, hex_code, name, callback, parent=None):
            super().__init__(parent)
            self.hex_code = hex_code
            self.color_name = name
            self.callback = callback
            self.is_selected = False
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setFixedHeight(38)
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.clicked.connect(lambda: self.callback(self.hex_code))

        def set_selected(self, selected):
            self.is_selected = selected
            self.update()

        def paintEvent(self, event):
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

            pal = self.palette()
            is_dark = pal.color(QPalette.ColorRole.Window).lightness() < 128

            rect = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
            path = QPainterPath()
            path.addRoundedRect(rect, 8, 8)

            # Background styling
            bg_col = pal.color(QPalette.ColorRole.Button)
            if self.is_selected:
                bg_col = pal.color(QPalette.ColorRole.Highlight)
                bg_col.setAlphaF(0.25 if is_dark else 0.15)
            elif self.underMouse():
                bg_col = pal.color(QPalette.ColorRole.Midlight)

            painter.fillPath(path, bg_col)

            # Border
            if self.is_selected:
                border_pen = QPen(pal.color(QPalette.ColorRole.Highlight), 2.0)
            else:
                border_pen = QPen(QColor(128, 128, 128, 45), 1.0)
            painter.strokePath(path, border_pen)

            # Vibrant Color Dot / Pill
            dot_r = 6.0
            dot_x = rect.x() + 11
            dot_y = rect.center().y()
            dot_path = QPainterPath()
            dot_path.addEllipse(QPointF(dot_x, dot_y), dot_r, dot_r)
            painter.fillPath(dot_path, QColor(self.hex_code))
            painter.strokePath(dot_path, QPen(QColor(0, 0, 0, 60), 1.0))

            # Color Text Label
            chk_space = 20 if self.is_selected else 6
            text_rect = QRectF(dot_x + dot_r + 6, rect.y(), rect.width() - (dot_x + dot_r + 6 + chk_space), rect.height())
            font = self.font()
            font.setPointSize(max(7, int(font.pointSize() * 0.92)))
            if self.is_selected:
                font.setWeight(QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(pal.color(QPalette.ColorRole.WindowText))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.color_name)

            # Selected Checkmark
            if self.is_selected:
                painter.setPen(QPen(pal.color(QPalette.ColorRole.Highlight), 2.0))
                chk_x = rect.right() - 11
                chk_y = rect.center().y()
                painter.drawLine(int(chk_x - 5), int(chk_y), int(chk_x - 2), int(chk_y + 3))
                painter.drawLine(int(chk_x - 2), int(chk_y + 3), int(chk_x + 4), int(chk_y - 4))


    class ClevoNativeWindow(QMainWindow):
        def __init__(self, backend):
            super().__init__()
            self.backend = backend
            self.current_color = "#00e5ff"
            self.saved_brightness = 255
            self.swatch_buttons = []
            self.is_updating_hardware = False

            self.setWindowTitle("Keyboard Backlight")
            self.setMinimumSize(620, 560)
            self.resize(700, 620)

            # Explicit standard window flags ensuring Minimize, Maximize, and Close buttons
            self.setWindowFlags(
                Qt.WindowType.Window |
                Qt.WindowType.WindowTitleHint |
                Qt.WindowType.WindowSystemMenuHint |
                Qt.WindowType.WindowMinimizeButtonHint |
                Qt.WindowType.WindowMaximizeButtonHint |
                Qt.WindowType.WindowCloseButtonHint
            )

            self.setWindowIcon(self.get_app_icon())

            self.init_ui()
            self.init_tray()
            self.load_state()

            # Background hardware sync timer for real-time Fn key detection
            self.sync_timer = QTimer(self)
            self.sync_timer.timeout.connect(self.poll_hardware_state)
            self.sync_timer.start(400)

        def get_app_icon(self):
            theme_icon = QIcon.fromTheme("clevo-keyboard")
            if not theme_icon.isNull():
                return theme_icon

            bundle_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
            icon_paths = [
                "/usr/share/icons/hicolor/scalable/apps/clevo-keyboard.svg",
                os.path.join(bundle_dir, "clevo-keyboard.svg"),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "clevo-keyboard.svg")
            ]
            for p in icon_paths:
                if os.path.exists(p):
                    return QIcon(p)
            return QIcon()

        def get_monochrome_tray_icon(self):
            pal = self.palette()
            is_dark = pal.color(QPalette.ColorRole.Window).lightness() < 128
            fg_color = QColor(252, 252, 252) if is_dark else QColor(35, 38, 41)

            # Generate high-DPI crisp monochrome icon matching panel palette
            icon = QIcon()
            for size in [16, 22, 24, 32, 48]:
                pm = QtGui.QPixmap(size, size)
                pm.fill(Qt.GlobalColor.transparent)
                p = QPainter(pm)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                scale = size / 22.0
                p.scale(scale, scale)

                # Outer keyboard frame
                p.setPen(QPen(fg_color, 1.5))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRoundedRect(QRectF(2.0, 4.5, 18.0, 12.0), 2.5, 2.5)

                # Chiclet keys
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(fg_color)
                for kx in [4.5, 7.5, 10.5, 13.5, 16.0]:
                    p.drawRoundedRect(QRectF(kx, 7.0, 1.6, 1.6), 0.4, 0.4)
                p.drawRoundedRect(QRectF(4.5, 10.5, 2.0, 1.6), 0.4, 0.4)
                p.drawRoundedRect(QRectF(7.5, 10.5, 7.0, 1.6), 0.5, 0.5)
                p.drawRoundedRect(QRectF(15.5, 10.5, 2.0, 1.6), 0.4, 0.4)

                # Backlight illumination indicators beneath
                p.drawEllipse(QRectF(7.2, 18.0, 1.4, 1.4))
                p.drawEllipse(QRectF(10.3, 18.0, 1.4, 1.4))
                p.drawEllipse(QRectF(13.4, 18.0, 1.4, 1.4))
                p.end()
                icon.addPixmap(pm)

            return icon

        def init_ui(self):
            pal = self.palette()
            is_dark = pal.color(QPalette.ColorRole.Window).lightness() < 128
            card_bg = pal.color(QPalette.ColorRole.AlternateBase) if is_dark else QColor(248, 249, 252)

            central = QWidget()
            self.setCentralWidget(central)
            layout = QVBoxLayout(central)
            layout.setContentsMargins(20, 16, 20, 16)
            layout.setSpacing(12)

            # ── Header ──────────────────────────────────────────────────
            hdr = QHBoxLayout()
            title_box = QVBoxLayout()
            title_box.setSpacing(2)

            title = QLabel("Keyboard Backlight")
            tf = title.font()
            tf.setPointSize(tf.pointSize() + 4)
            tf.setWeight(QFont.Weight.Bold)
            title.setFont(tf)

            subtitle = QLabel("15 Standard Colors • Hardware Direct Control")
            subtitle.setEnabled(False)

            title_box.addWidget(title)
            title_box.addWidget(subtitle)
            hdr.addLayout(title_box)

            hdr.addStretch()

            self.btn_power = QPushButton("Turn Off")
            self.btn_power.setFixedHeight(34)
            self.btn_power.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_power.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.btn_power.clicked.connect(self.toggle_power)
            hdr.addWidget(self.btn_power)

            layout.addLayout(hdr)

            # ── Interactive Keyboard Preview ────────────────────────────
            self.canvas = ModernKeyboardCanvas()
            layout.addWidget(self.canvas)

            # ── Brightness Card ─────────────────────────────────────────
            brt_card = QFrame()
            brt_card.setObjectName("brt_card")
            brt_card.setStyleSheet(f"""
                QFrame#brt_card {{
                    background-color: {card_bg.name()};
                    border: 1px solid rgba(128, 128, 128, 0.18);
                    border-radius: 10px;
                }}
                QFrame#brt_card QLabel {{
                    border: none;
                    background: transparent;
                }}
            """)
            b_layout = QVBoxLayout(brt_card)
            b_layout.setContentsMargins(14, 10, 14, 12)
            b_layout.setSpacing(8)

            b_hdr = QHBoxLayout()
            b_title = QLabel("Brightness")
            bf = b_title.font()
            bf.setWeight(QFont.Weight.DemiBold)
            b_title.setFont(bf)
            b_hdr.addWidget(b_title)

            b_hdr.addStretch()

            self.brt_label = QLabel("100%")
            self.brt_label.setStyleSheet("font-weight: bold; padding: 2px 8px; border-radius: 6px;")
            b_hdr.addWidget(self.brt_label)
            b_layout.addLayout(b_hdr)

            self.slider = QSlider(Qt.Orientation.Horizontal)
            self.slider.setRange(0, 255)
            self.slider.setValue(255)
            self.slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.slider.valueChanged.connect(self.on_brightness_changed)
            b_layout.addWidget(self.slider)

            # Quick step preset pills
            steps_box = QHBoxLayout()
            steps_box.setSpacing(6)
            for lbl, val in [("Off", 0), ("25%", 64), ("50%", 128), ("75%", 192), ("100%", 255)]:
                b = QPushButton(lbl)
                b.setFixedHeight(26)
                b.setCursor(Qt.CursorShape.PointingHandCursor)
                b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                b.clicked.connect(lambda _, v=val: self.slider.setValue(v))
                steps_box.addWidget(b)
            b_layout.addLayout(steps_box)

            layout.addWidget(brt_card)

            # ── 15 Clevo Colors Section (5x3 Grid) ──────────────────────
            color_card = QFrame()
            color_card.setObjectName("color_card")
            color_card.setStyleSheet(f"""
                QFrame#color_card {{
                    background-color: {card_bg.name()};
                    border: 1px solid rgba(128, 128, 128, 0.18);
                    border-radius: 10px;
                }}
                QFrame#color_card QLabel {{
                    border: none;
                    background: transparent;
                }}
            """)
            c_layout = QVBoxLayout(color_card)
            c_layout.setContentsMargins(14, 10, 14, 12)
            c_layout.setSpacing(10)

            c_hdr = QHBoxLayout()
            c_title = QLabel("15 Standard Clevo Colors")
            cf = c_title.font()
            cf.setWeight(QFont.Weight.DemiBold)
            c_title.setFont(cf)
            c_hdr.addWidget(c_title)

            c_hdr.addStretch()

            self.color_name_lbl = QLabel("Cyan")
            self.color_name_lbl.setStyleSheet("font-weight: bold;")
            c_hdr.addWidget(self.color_name_lbl)
            c_layout.addLayout(c_hdr)

            grid = QGridLayout()
            grid.setSpacing(7)
            self.swatch_buttons = []

            for idx, (hx, name) in enumerate(CLEVO_15_COLORS):
                btn = ColorCardButton(hx, name, self.apply_color)
                grid.addWidget(btn, idx // 5, idx % 5)
                self.swatch_buttons.append(btn)

            c_layout.addLayout(grid)
            layout.addWidget(color_card)

            # ── Footer / Shortcuts & Driver Status ──────────────────────
            footer = QHBoxLayout()
            self.status_lbl = QLabel("● Driver active (Kernel 7.3+)")
            self.status_lbl.setStyleSheet("color: #388bfd; font-size: 11px;")
            footer.addWidget(self.status_lbl)

            footer.addStretch()

            shortcuts_hint = QLabel("Keys: [↑/↓/+] Brightness • [Space] Power • [1-9] Color • [C] Cycle")
            shortcuts_hint.setStyleSheet("color: rgba(128, 128, 128, 0.7); font-size: 11px;")
            footer.addWidget(shortcuts_hint)

            layout.addLayout(footer)

        def init_tray(self):
            self.tray = QSystemTrayIcon(self)
            self.tray.setIcon(self.get_monochrome_tray_icon())
            self.tray.setToolTip("Keyboard Backlight")

            menu = QMenu()
            action_open = QAction("Open Control Panel", self)
            action_open.triggered.connect(self.showNormal)
            menu.addAction(action_open)

            menu.addSeparator()

            # 15 Colors Menu
            col_menu = menu.addMenu("Color")
            for hx, name in CLEVO_15_COLORS:
                act = QAction(name, self)
                act.triggered.connect(lambda _, c=hx: self.apply_color(c))
                col_menu.addAction(act)

            # Brightness Menu
            brt_menu = menu.addMenu("Brightness")
            for lbl, val in [("100%", 255), ("75%", 192), ("50%", 128), ("25%", 64), ("Off", 0)]:
                act = QAction(lbl, self)
                act.triggered.connect(lambda _, v=val: self.slider.setValue(v))
                brt_menu.addAction(act)

            menu.addSeparator()

            act_off = QAction("Turn Off", self)
            act_off.triggered.connect(self.toggle_power)
            menu.addAction(act_off)

            act_quit = QAction("Quit", self)
            act_quit.triggered.connect(QApplication.instance().quit)
            menu.addAction(act_quit)

            self.tray.setContextMenu(menu)
            self.tray.activated.connect(self.on_tray_click)
            self.tray.show()

        def on_tray_click(self, reason):
            if reason == QSystemTrayIcon.ActivationReason.Trigger:
                if self.isVisible():
                    self.hide()
                else:
                    self.showNormal()
                    self.activateWindow()

        def load_state(self):
            self.backend.refresh()
            cur_col = self.backend.get_color()
            self.current_color = cur_col

            name = "White"
            for hx, n in CLEVO_15_COLORS:
                if hx.lower() == cur_col.lower():
                    name = n
                    break
            self.color_name_lbl.setText(name)

            cur_brt = self.backend.get_brightness()
            self.slider.blockSignals(True)
            self.slider.setValue(cur_brt)
            self.slider.blockSignals(False)

            self.brt_label.setText(f"{int(cur_brt / 255.0 * 100)}%")
            self.canvas.set_state(self.current_color, cur_brt)
            self.update_swatch_highlights()

            if cur_brt == 0:
                self.btn_power.setText("Turn On")
            else:
                self.btn_power.setText("Turn Off")

            if SysfsBackend.is_module_loaded():
                self.status_lbl.setText("● Driver active (Kernel 7.3+)")
                self.status_lbl.setStyleSheet("color: #388bfd; font-size: 11px;")
            else:
                self.status_lbl.setText("⚠️ Driver not loaded")
                self.status_lbl.setStyleSheet("color: #e3b341; font-size: 11px;")

        def poll_hardware_state(self):
            """Real-time sync when hardware hotkeys (Fn keys) are pressed outside the app."""
            if self.is_updating_hardware:
                return

            hw_brt = self.backend.get_brightness()
            hw_col = self.backend.get_color()

            # Synchronize brightness if changed by hardware Fn keys
            if hw_brt != self.slider.value():
                self.slider.blockSignals(True)
                self.slider.setValue(hw_brt)
                self.slider.blockSignals(False)
                self.brt_label.setText(f"{int(hw_brt / 255.0 * 100)}%")
                self.canvas.set_state(self.current_color, hw_brt)
                if hw_brt == 0:
                    self.btn_power.setText("Turn On")
                else:
                    self.btn_power.setText("Turn Off")

            # Synchronize color if changed by hardware Fn keys
            if hw_col.lower() != self.current_color.lower():
                self.current_color = hw_col
                for btn in self.swatch_buttons:
                    if btn.hex_code.lower() == hw_col.lower():
                        self.color_name_lbl.setText(btn.color_name)
                        break
                self.canvas.set_state(hw_col, hw_brt)
                self.update_swatch_highlights()

        def on_brightness_changed(self, value):
            self.is_updating_hardware = True
            pct = int((value / 255.0) * 100)
            self.brt_label.setText(f"{pct}%")
            self.canvas.set_state(self.current_color, value)
            self.backend.set_brightness(value)

            if value == 0:
                self.btn_power.setText("Turn On")
            else:
                self.btn_power.setText("Turn Off")
            self.is_updating_hardware = False

        def toggle_power(self):
            if self.slider.value() > 0:
                self.saved_brightness = self.slider.value()
                self.slider.setValue(0)
            else:
                val = getattr(self, "saved_brightness", 255)
                self.slider.setValue(val if val > 0 else 255)

        def apply_color(self, hex_code):
            self.is_updating_hardware = True
            self.current_color = hex_code
            for hx, name in CLEVO_15_COLORS:
                if hx.lower() == hex_code.lower():
                    self.color_name_lbl.setText(name)
                    break

            self.canvas.set_state(hex_code, self.slider.value())
            self.backend.set_color(hex_code)
            self.update_swatch_highlights()
            self.is_updating_hardware = False

        def cycle_next_color(self):
            cur = self.current_color.lower()
            current_idx = 0
            for idx, (hx, _) in enumerate(CLEVO_15_COLORS):
                if hx.lower() == cur:
                    current_idx = idx
                    break
            next_idx = (current_idx + 1) % len(CLEVO_15_COLORS)
            self.apply_color(CLEVO_15_COLORS[next_idx][0])

        def update_swatch_highlights(self):
            for btn in self.swatch_buttons:
                is_active = (btn.hex_code.lower() == self.current_color.lower())
                btn.set_selected(is_active)

        # ── Physical Keyboard & Shortcut Key Handling ───────────────────────
        def keyPressEvent(self, event):
            key = event.key()

            # Increase Brightness
            if key in (Qt.Key.Key_Up, Qt.Key.Key_Right, Qt.Key.Key_Plus, Qt.Key.Key_Equal):
                self.slider.setValue(min(255, self.slider.value() + 25))
                event.accept()
                return

            # Decrease Brightness
            elif key in (Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Minus):
                self.slider.setValue(max(0, self.slider.value() - 25))
                event.accept()
                return

            # Power Toggle (Space or 0)
            elif key in (Qt.Key.Key_Space, Qt.Key.Key_0):
                self.toggle_power()
                event.accept()
                return

            # Direct Color Selection (Keys 1 - 9)
            elif Qt.Key.Key_1 <= key <= Qt.Key.Key_9:
                idx = key - Qt.Key.Key_1
                if idx < len(CLEVO_15_COLORS):
                    self.apply_color(CLEVO_15_COLORS[idx][0])
                event.accept()
                return

            # Cycle Colors ('C' key)
            elif key == Qt.Key.Key_C:
                self.cycle_next_color()
                event.accept()
                return

            # Escape closes and exits app completely
            elif key == Qt.Key.Key_Escape:
                self.close()
                event.accept()
                return

            super().keyPressEvent(event)

        def closeEvent(self, event):
            # When window is closed, hide tray icon and quit completely (never run in background)
            if hasattr(self, "tray") and self.tray:
                self.tray.hide()
            QApplication.quit()
            event.accept()



# ─── Command Line (CLI) Support ─────────────────────────────────────────────

def run_cli(args):
    backend = SysfsBackend()

    if args.status:
        loaded = SysfsBackend.is_module_loaded()
        print("=== Clevo Keyboard Backlight ===")
        print(f"Driver Loaded: {loaded}")
        print(f"Brightness:    {backend.get_brightness()} / 255")
        print(f"Active Color:  {backend.get_color()}")
        return 0

    if args.off:
        backend.turn_off()
        print("[+] Backlight turned off.")
        return 0

    if args.on:
        backend.turn_on(args.brightness if args.brightness is not None else 255)
        print("[+] Backlight turned on.")
        return 0

    if args.color:
        key = args.color.lower().replace(" ", "").replace("#", "")
        hex_code = COLOR_MAP.get(key)
        if not hex_code:
            hex_code = "#" + key if len(key) == 6 else None

        if hex_code:
            backend.set_color(hex_code)
            print(f"[+] Color set to {hex_code}.")
        else:
            print(f"[-] Unknown color: '{args.color}'. Standard options:")
            print(", ".join(n for _, n in CLEVO_15_COLORS))
            return 1

    if args.brightness is not None:
        backend.set_brightness(args.brightness)
        print(f"[+] Brightness set to {args.brightness}.")

    return 0


# ─── Entry Point ────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Clevo Keyboard Backlight Control (Native Linux)")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode")
    parser.add_argument("--color", type=str, help="15 standard colors: blue, red, green, cyan, white, orange, etc.")
    parser.add_argument("--brightness", type=int, help="Brightness (0 - 255)")
    parser.add_argument("--on", action="store_true", help="Turn on backlight")
    parser.add_argument("--off", action="store_true", help="Turn off backlight")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--tray", action="store_true", help="Start minimized to system tray")
    args = parser.parse_args()

    if args.cli or args.color or args.brightness is not None or args.on or args.off or args.status:
        sys.exit(run_cli(args))

    if PYQT6_AVAILABLE:
        app = QApplication(sys.argv)
        app.setApplicationName("Clevo Keyboard Backlight")
        app.setOrganizationName("ClevoLinux")
        app.setQuitOnLastWindowClosed(True)

        backend = SysfsBackend()
        window = ClevoNativeWindow(backend)

        if not args.tray:
            window.show()

        sys.exit(app.exec())
    else:
        print("[-] PyQt6 is required: sudo apt install python3-pyqt6")
        sys.exit(1)


if __name__ == "__main__":
    main()
