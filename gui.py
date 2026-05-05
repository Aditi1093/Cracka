"""
gui_app/gui.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRACKA AI v3.0 — Ultimate PyQt5 GUI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Features:
  ✅ Glowing animated CRACKA orb (exact image match)
  ✅ Real-time voice waveform bars
  ✅ Animated avatar — state se color change
  ✅ System stats — CPU, RAM, Battery live
  ✅ Network threat alert popup
  ✅ Chat history with scroll
  ✅ Quick action buttons
  ✅ Dark / Light theme toggle
  ✅ Minimize to system tray
  ✅ Smooth animations 60fps

Install: pip install PyQt5
"""

import sys
import os
import math
import random
import threading
import queue
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QFrame, QSystemTrayIcon,
    QMenu, QAction, QGraphicsDropShadowEffect, QSizePolicy,
    QMessageBox, QDialog
)
from PyQt5.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QPropertyAnimation,
    QEasingCurve, QPoint, QSize, QRect
)
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QLinearGradient, QRadialGradient,
    QFont, QFontDatabase, QPainterPath, QIcon, QPixmap, QPalette
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Color Themes ──────────────────────────────────────────────────────────────
THEMES = {
    "dark": {
        "bg":          "#000000",
        "bg2":         "#050d14",
        "bg3":         "#080f1a",
        "panel":       "#0a1520",
        "border":      "#0d2030",
        "primary":     "#00e5ff",
        "secondary":   "#00bcd4",
        "dim":         "#005f6b",
        "text":        "#c8e8f0",
        "text2":       "#7ab8cc",
        "success":     "#00ff88",
        "warning":     "#ffab00",
        "danger":      "#ff2d55",
        "speaking":    "#bf80ff",
    },
    "light": {
        "bg":          "#f0f8ff",
        "bg2":         "#e0f0fa",
        "bg3":         "#d0e8f5",
        "panel":       "#ffffff",
        "border":      "#b0d0e8",
        "primary":     "#0077aa",
        "secondary":   "#0099cc",
        "dim":         "#4488aa",
        "text":        "#1a3a4a",
        "text2":       "#336680",
        "success":     "#008844",
        "warning":     "#cc7700",
        "danger":      "#cc0033",
        "speaking":    "#7700cc",
    }
}

# States
IDLE      = "idle"
LISTENING = "listening"
THINKING  = "thinking"
SPEAKING  = "speaking"

current_theme = "dark"
T = THEMES["dark"]


def theme():
    return THEMES[current_theme]


# ── Orb Widget (Animated CRACKA orb) ─────────────────────────────────────────
class OrbWidget(QWidget):

    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(280, 280)
        self.setCursor(Qt.PointingHandCursor)

        self._state       = IDLE
        self._tick        = 0
        self._ring_angles = [i * 30.0 for i in range(6)]
        self._ring_speeds = [0.4, -0.6, 0.8, -0.5, 0.7, -0.9]
        self._wave_bars   = [0.0] * 48
        self._wave_targets= [0.0] * 48
        self._pulse       = 0.0
        self._particles   = [self._new_particle() for _ in range(30)]

        # Color transition
        self._color_t      = 1.0
        self._prev_primary = QColor("#005f6b")
        self._curr_primary = QColor("#00e5ff")

        # Animation timer 60fps
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick_update)
        self._timer.start(16)

    def _new_particle(self):
        return {
            "angle":      random.uniform(0, math.pi * 2),
            "radius":     random.uniform(85, 130),
            "speed":      random.uniform(0.004, 0.012),
            "size":       random.uniform(1.0, 2.5),
            "life":       random.uniform(0, 1),
            "life_speed": random.uniform(0.004, 0.012),
        }

    def set_state(self, state: str):
        self._prev_primary = self._curr_primary
        self._state        = state
        self._color_t      = 0.0

        colors = {
            IDLE:      "#00e5ff",
            LISTENING: "#00ff88",
            THINKING:  "#ffab00",
            SPEAKING:  "#bf80ff",
        }
        self._curr_primary = QColor(colors.get(state, "#00e5ff"))

    def _tick_update(self):
        self._tick  += 1
        self._pulse  = (math.sin(self._tick * 0.05) + 1) / 2

        if self._color_t < 1.0:
            self._color_t = min(1.0, self._color_t + 0.06)

        # Speed multiplier per state
        speed = {IDLE: 0.3, LISTENING: 1.2, THINKING: 2.0, SPEAKING: 1.6}
        mult  = speed.get(self._state, 0.3)

        for i in range(6):
            self._ring_angles[i] += self._ring_speeds[i] * mult

        # Wave update
        self._update_wave()

        # Particles
        for p in self._particles:
            p["angle"] += p["speed"] * (1.0 + self._pulse * 0.3)
            p["life"]  += p["life_speed"]
            if p["life"] >= 1.0:
                self._particles[self._particles.index(p)] = self._new_particle()

        self.update()

    def _update_wave(self):
        n = len(self._wave_bars)
        for i in range(n):
            if self._state == IDLE:
                phase = (i / n) * math.pi * 4
                self._wave_targets[i] = max(0.02,
                    math.sin(phase + self._tick * 0.025) * 0.12)

            elif self._state == LISTENING:
                phase = (i / n) * math.pi * 6
                self._wave_targets[i] = max(0.05,
                    math.sin(phase + self._tick * 0.10) * 0.38
                    + random.uniform(-0.06, 0.06) + 0.15)

            elif self._state == THINKING:
                pulse = (math.sin(self._tick * 0.07) + 1) / 2
                dist  = abs(i - n/2) / (n/2)
                self._wave_targets[i] = max(0.03, (1 - dist) * pulse * 0.55)

            elif self._state == SPEAKING:
                phase = (i / n) * math.pi * 8
                self._wave_targets[i] = max(0.08,
                    abs(math.sin(phase + self._tick * 0.15)) * 0.55
                    + random.uniform(-0.08, 0.08) + 0.12)

            diff = self._wave_targets[i] - self._wave_bars[i]
            self._wave_bars[i] += diff * 0.2

    def _lerp_color(self, c1: QColor, c2: QColor, t: float) -> QColor:
        t = max(0.0, min(1.0, t))
        r = int(c1.red()   + (c2.red()   - c1.red())   * t)
        g = int(c1.green() + (c2.green() - c1.green()) * t)
        b = int(c1.blue()  + (c2.blue()  - c1.blue())  * t)
        return QColor(r, g, b)

    def paintEvent(self, event):
        p   = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx  = self.width()  // 2
        cy  = self.height() // 2

        primary = self._lerp_color(self._prev_primary, self._curr_primary, self._color_t)
        dim_c   = QColor(0, 50, 60)
        bg_c    = QColor(0, 0, 0)

        # ── Background glow ───────────────────────────────────────────────────
        glow = QRadialGradient(cx, cy, 140)
        glow.setColorAt(0.0, QColor(primary.red()//6, primary.green()//6, primary.blue()//6, 120))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillRect(self.rect(), QBrush(glow))

        # ── Particles ─────────────────────────────────────────────────────────
        for pt in self._particles:
            alpha = math.sin(pt["life"] * math.pi) * pt["size"] * 0.6
            alpha = max(0, min(255, int(alpha * 80)))
            pc    = QColor(primary.red(), primary.green(), primary.blue(), alpha)
            x     = cx + pt["radius"] * math.cos(pt["angle"])
            y     = cy + pt["radius"] * math.sin(pt["angle"])
            s     = pt["size"]
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(pc))
            p.drawEllipse(int(x-s), int(y-s), int(s*2), int(s*2))

        # ── Spinning rings ────────────────────────────────────────────────────
        ring_config = [
            (125, 24, 10, 2),  # radius, segments, gap, width
            (112, 20,  9, 2),
            (100, 18,  8, 2),
            ( 88, 16,  7, 2),
            ( 76, 14,  6, 2),
            ( 64, 12,  5, 2),
        ]

        for i, (radius, segs, gap, lw) in enumerate(ring_config):
            angle_base = self._ring_angles[i]
            seg_size   = 360.0 / segs

            for j in range(segs):
                start = angle_base + j * seg_size
                ext   = seg_size - gap

                # Alternate bright/dim
                if j % 2 == 0:
                    brightness = 0.6 + self._pulse * 0.4
                    color = QColor(
                        int(primary.red()   * brightness),
                        int(primary.green() * brightness),
                        int(primary.blue()  * brightness)
                    )
                    width = lw + (1 if self._state != IDLE else 0)
                else:
                    color = dim_c
                    width = 1

                pen = QPen(color, width)
                p.setPen(pen)
                p.setBrush(Qt.NoBrush)
                rect = QRect(cx-radius, cy-radius, radius*2, radius*2)
                p.drawArc(rect, int(start * 16), int(ext * 16))

        # ── Core circle ───────────────────────────────────────────────────────
        core_r = 52
        core_w = 4 + int(self._pulse * 2) if self._state != IDLE else 3

        # Dark fill
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(0, 5, 10)))
        p.drawEllipse(cx-core_r, cy-core_r, core_r*2, core_r*2)

        # Glowing border
        p.setPen(QPen(primary, core_w))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(cx-core_r, cy-core_r, core_r*2, core_r*2)

        # Inner ring
        inner_r = core_r - 10
        p.setPen(QPen(QColor(primary.red()//2, primary.green()//2, primary.blue()//2, 180), 1))
        p.drawEllipse(cx-inner_r, cy-inner_r, inner_r*2, inner_r*2)

        # ── WAVEFORM bars ─────────────────────────────────────────────────────
        n       = len(self._wave_bars)
        bar_w   = 3
        gap     = 2
        total_w = n * (bar_w + gap)
        start_x = cx - total_w // 2
        wave_y  = cy + 8
        max_h   = 38

        for i in range(n):
            h       = int(self._wave_bars[i] * max_h)
            h       = max(2, h)
            x1      = start_x + i * (bar_w + gap)

            # Gradient color
            bright  = 0.5 + (h / max_h) * 0.5
            bar_col = QColor(
                int(primary.red()   * bright),
                int(primary.green() * bright),
                int(primary.blue()  * bright)
            )
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(bar_col))
            p.drawRect(x1, wave_y - h, bar_w, h)

            # Mirror
            mir_h   = int(h * 0.35)
            mir_col = QColor(primary.red()//4, primary.green()//4, primary.blue()//4)
            p.setBrush(QBrush(mir_col))
            p.drawRect(x1, wave_y, bar_w, mir_h)

        # ── CRACKA text ───────────────────────────────────────────────────────
        txt_color = self._lerp_color(
            QColor(200, 240, 255),
            primary,
            self._pulse * 0.4 if self._state != IDLE else 0
        )
        font = QFont("Consolas", 14, QFont.Bold)
        p.setFont(font)
        p.setPen(QPen(txt_color))
        p.drawText(self.rect().adjusted(0, -20, 0, -20), Qt.AlignCenter, "CRACKA")

        # State text
        state_labels = {
            IDLE:      "STANDBY",
            LISTENING: "LISTENING",
            THINKING:  "THINKING",
            SPEAKING:  "SPEAKING",
        }
        sfont = QFont("Consolas", 7)
        p.setFont(sfont)
        p.setPen(QPen(QColor(primary.red()//2, primary.green()//2, primary.blue()//2)))
        p.drawText(self.rect().adjusted(0, 20, 0, 20), Qt.AlignCenter,
                   state_labels.get(self._state, ""))

        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            dx = event.x() - self.width()  // 2
            dy = event.y() - self.height() // 2
            if math.sqrt(dx*dx + dy*dy) <= 58:
                self.clicked.emit()


# ── System Stats Widget ────────────────────────────────────────────────────────
class StatsWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(16)

        self._cpu_lbl  = self._make_stat("CPU", "—%")
        self._ram_lbl  = self._make_stat("RAM", "—%")
        self._bat_lbl  = self._make_stat("BAT", "—%")
        self._time_lbl = self._make_stat("TIME", "--:--")

        for widget in [self._cpu_lbl, self._ram_lbl,
                       self._bat_lbl, self._time_lbl]:
            layout.addWidget(widget)

        # Update every 3 seconds
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_stats)
        self._timer.start(3000)
        self._update_stats()

    def _make_stat(self, label: str, value: str) -> QFrame:
        frame  = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(0)

        lbl = QLabel(label)
        lbl.setStyleSheet("color: #005f6b; font-size: 9px; font-family: Consolas;")
        lbl.setAlignment(Qt.AlignCenter)

        val = QLabel(value)
        val.setStyleSheet("color: #00e5ff; font-size: 12px; font-family: Consolas; font-weight: bold;")
        val.setAlignment(Qt.AlignCenter)
        val.setObjectName(f"stat_{label}")

        layout.addWidget(lbl)
        layout.addWidget(val)
        frame.setStyleSheet("QFrame { background: #0a1520; border-radius: 6px; }")
        return frame

    def _update_stats(self):
        try:
            import psutil
            cpu  = psutil.cpu_percent(interval=0.1)
            ram  = psutil.virtual_memory().percent

            # CPU
            val = self._cpu_lbl.findChild(QLabel, "stat_CPU")
            if val:
                color = "#ff2d55" if cpu > 80 else "#ffab00" if cpu > 50 else "#00e5ff"
                val.setStyleSheet(f"color: {color}; font-size: 12px; font-family: Consolas; font-weight: bold;")
                val.setText(f"{cpu:.0f}%")

            # RAM
            val = self._ram_lbl.findChild(QLabel, "stat_RAM")
            if val:
                color = "#ff2d55" if ram > 85 else "#ffab00" if ram > 65 else "#00e5ff"
                val.setStyleSheet(f"color: {color}; font-size: 12px; font-family: Consolas; font-weight: bold;")
                val.setText(f"{ram:.0f}%")

            # Battery
            batt = psutil.sensors_battery()
            val  = self._bat_lbl.findChild(QLabel, "stat_BAT")
            if val and batt:
                pct   = batt.percent
                color = "#ff2d55" if pct < 20 else "#ffab00" if pct < 40 else "#00ff88"
                plug  = "⚡" if batt.power_plugged else ""
                val.setStyleSheet(f"color: {color}; font-size: 12px; font-family: Consolas; font-weight: bold;")
                val.setText(f"{plug}{pct:.0f}%")
        except Exception:
            pass

        # Time
        val = self._time_lbl.findChild(QLabel, "stat_TIME")
        if val:
            val.setText(datetime.now().strftime("%H:%M"))


# ── Chat Message Widget ────────────────────────────────────────────────────────
class ChatBubble(QFrame):

    def __init__(self, sender: str, message: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(2)

        is_cracka = sender == "Cracka"
        ts        = datetime.now().strftime("%H:%M")

        # Sender + time row
        top = QHBoxLayout()
        top.setSpacing(6)

        name_lbl = QLabel(sender)
        name_lbl.setStyleSheet(
            f"color: {'#00e5ff' if is_cracka else '#00ff88'}; "
            f"font-size: 11px; font-family: Consolas; font-weight: bold;"
        )
        time_lbl = QLabel(ts)
        time_lbl.setStyleSheet("color: #0a2030; font-size: 9px; font-family: Consolas;")

        top.addWidget(name_lbl)
        top.addStretch()
        top.addWidget(time_lbl)
        layout.addLayout(top)

        # Message
        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet(
            f"color: {'#c8e8f0' if is_cracka else '#d0ffe0'}; "
            f"font-size: 12px; font-family: Consolas;"
        )
        layout.addWidget(msg_lbl)

        bg = "#0a1825" if is_cracka else "#071510"
        self.setStyleSheet(
            f"QFrame {{ background: {bg}; border-radius: 8px; "
            f"border-left: 2px solid {'#00e5ff' if is_cracka else '#00ff88'}; }}"
        )


# ── Quick Actions ──────────────────────────────────────────────────────────────
class QuickActionsWidget(QWidget):

    command_triggered = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        actions = [
            ("🌐", "Search",    "search"),
            ("🌤", "Weather",   "weather"),
            ("📰", "News",      "news"),
            ("🔒", "Network",   "check network"),
            ("📸", "Screen",    "take screenshot"),
            ("🎵", "Music",     "play"),
            ("😄", "Mood",      "detect my mood"),
            ("📋", "Diary",     "show diary"),
        ]

        for emoji, label, cmd in actions:
            btn = QPushButton(f"{emoji}\n{label}")
            btn.setFixedSize(64, 52)
            btn.setStyleSheet("""
                QPushButton {
                    background: #0a1520;
                    color: #00bcd4;
                    border: 1px solid #0d2030;
                    border-radius: 8px;
                    font-size: 10px;
                    font-family: Consolas;
                }
                QPushButton:hover {
                    background: #0d2535;
                    border-color: #00e5ff;
                    color: #00e5ff;
                }
                QPushButton:pressed {
                    background: #112030;
                }
            """)
            btn.clicked.connect(lambda checked, c=cmd: self.command_triggered.emit(c))
            layout.addWidget(btn)

        layout.addStretch()


# ── Threat Alert Dialog ────────────────────────────────────────────────────────
class ThreatAlertDialog(QDialog):

    def __init__(self, threats: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚠ CRACKA SECURITY ALERT")
        self.setFixedWidth(420)
        self.setStyleSheet("""
            QDialog {
                background: #0a0005;
                border: 2px solid #ff2d55;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("⚠  NETWORK THREAT DETECTED")
        title.setStyleSheet("color: #ff2d55; font-size: 15px; font-family: Consolas; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        for threat in threats[:4]:
            row = QFrame()
            row.setStyleSheet("QFrame { background: #150005; border-radius: 6px; border: 1px solid #440010; }")
            rl  = QVBoxLayout(row)
            rl.setContentsMargins(10, 6, 10, 6)

            sev = threat.get("severity", "MEDIUM")
            proc= threat.get("process", "unknown")
            ip  = threat.get("hostname", threat.get("remote_ip", ""))
            port= threat.get("remote_port", "")

            sev_lbl = QLabel(f"[{sev}] {proc} → {ip}:{port}")
            sev_lbl.setStyleSheet(
                f"color: {'#ff2d55' if sev == 'HIGH' else '#ffab00'}; "
                f"font-size: 11px; font-family: Consolas;"
            )
            rl.addWidget(sev_lbl)

            for alert in threat.get("alerts", [])[:2]:
                a_lbl = QLabel(f"  → {alert}")
                a_lbl.setStyleSheet("color: #994455; font-size: 10px; font-family: Consolas;")
                rl.addWidget(a_lbl)

            layout.addWidget(row)

        btn = QPushButton("ACKNOWLEDGE")
        btn.setStyleSheet("""
            QPushButton {
                background: #ff2d55;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
                font-family: Consolas;
                font-weight: bold;
            }
            QPushButton:hover { background: #ff4466; }
        """)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)


# ── Main GUI Window ────────────────────────────────────────────────────────────
class CrackaGUI(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CRACKA AI v3.0")
        self.setFixedWidth(520)
        self.setMinimumHeight(700)
        self._dark_mode  = True
        self._active     = False
        self._msg_queue  = queue.Queue()
        self._on_activate= None

        self._setup_window()
        self._setup_tray()
        self._apply_theme()

        # Queue processor
        self._queue_timer = QTimer(self)
        self._queue_timer.timeout.connect(self._process_queue)
        self._queue_timer.start(80)

    def _setup_window(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # ── Header ────────────────────────────────────────────────────────────
        header = QHBoxLayout()

        title = QLabel("◉  CRACKA AI")
        title.setStyleSheet(
            "color: #00e5ff; font-size: 18px; font-family: Consolas; font-weight: bold;"
        )
        header.addWidget(title)
        header.addStretch()

        # Theme toggle
        self._theme_btn = QPushButton("🌙")
        self._theme_btn.setFixedSize(32, 32)
        self._theme_btn.setStyleSheet(self._icon_btn_style())
        self._theme_btn.clicked.connect(self._toggle_theme)
        self._theme_btn.setToolTip("Toggle Dark/Light theme")
        header.addWidget(self._theme_btn)

        # Minimize to tray
        tray_btn = QPushButton("📌")
        tray_btn.setFixedSize(32, 32)
        tray_btn.setStyleSheet(self._icon_btn_style())
        tray_btn.clicked.connect(self.hide)
        tray_btn.setToolTip("Minimize to system tray")
        header.addWidget(tray_btn)

        main_layout.addLayout(header)

        # ── Status label ──────────────────────────────────────────────────────
        self._status_lbl = QLabel("● STANDBY")
        self._status_lbl.setStyleSheet(
            "color: #005f6b; font-size: 10px; font-family: Consolas;"
        )
        self._status_lbl.setAlignment(Qt.AlignRight)
        main_layout.addWidget(self._status_lbl)

        # ── ORB ───────────────────────────────────────────────────────────────
        orb_container = QHBoxLayout()
        orb_container.setAlignment(Qt.AlignCenter)
        self._orb = OrbWidget()
        self._orb.clicked.connect(self._on_orb_click)
        orb_container.addWidget(self._orb)
        main_layout.addLayout(orb_container)

        # ── System Stats ──────────────────────────────────────────────────────
        self._stats = StatsWidget()
        main_layout.addWidget(self._stats)

        # ── Quick Actions ─────────────────────────────────────────────────────
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setStyleSheet("color: #0d2030;")
        main_layout.addWidget(sep1)

        self._quick = QuickActionsWidget()
        self._quick.command_triggered.connect(self._on_quick_command)
        main_layout.addWidget(self._quick)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("color: #0d2030;")
        main_layout.addWidget(sep2)

        # ── Chat area ─────────────────────────────────────────────────────────
        chat_label = QLabel("CONVERSATION")
        chat_label.setStyleSheet(
            "color: #005f6b; font-size: 9px; font-family: Consolas; letter-spacing: 2px;"
        )
        main_layout.addWidget(chat_label)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                background: #050d14; width: 6px; border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #0d2030; border-radius: 3px; min-height: 20px;
            }
        """)

        self._chat_container = QWidget()
        self._chat_layout    = QVBoxLayout(self._chat_container)
        self._chat_layout.setAlignment(Qt.AlignTop)
        self._chat_layout.setSpacing(6)
        self._chat_layout.setContentsMargins(4, 4, 4, 4)
        self._scroll.setWidget(self._chat_container)
        self._scroll.setMinimumHeight(180)
        main_layout.addWidget(self._scroll)

        # ── Bottom mic bar ────────────────────────────────────────────────────
        bottom = QHBoxLayout()
        self._mic_lbl = QLabel("◉ MIC")
        self._mic_lbl.setStyleSheet(
            "color: #0a1f28; font-size: 10px; font-family: Consolas;"
        )
        bottom.addWidget(self._mic_lbl)
        bottom.addStretch()

        ver = QLabel("CRACKA v3.0  |  Click orb or say 'Cracka'")
        ver.setStyleSheet("color: #0a2030; font-size: 9px; font-family: Consolas;")
        bottom.addWidget(ver)
        main_layout.addLayout(bottom)

    def _icon_btn_style(self):
        return """
            QPushButton {
                background: #0a1520;
                border: 1px solid #0d2030;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover { background: #0d2535; border-color: #00e5ff; }
        """

    def _setup_tray(self):
        """System tray icon setup."""
        self._tray = QSystemTrayIcon(self)

        # Create a simple icon
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor("#00e5ff"), 2))
        painter.setBrush(QBrush(QColor(0, 10, 20)))
        painter.drawEllipse(2, 2, 28, 28)
        painter.setPen(QPen(QColor("#00e5ff")))
        painter.setFont(QFont("Consolas", 10, QFont.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "C")
        painter.end()
        self._tray.setIcon(QIcon(pixmap))

        tray_menu = QMenu()
        show_action = QAction("Show Cracka", self)
        show_action.triggered.connect(self.show)
        quit_action = QAction("Exit", self)
        quit_action.triggered.connect(QApplication.quit)

        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        tray_menu.setStyleSheet("""
            QMenu {
                background: #050d14;
                color: #00e5ff;
                border: 1px solid #0d2030;
                font-family: Consolas;
            }
            QMenu::item:selected { background: #0d2535; }
        """)

        self._tray.setContextMenu(tray_menu)
        self._tray.activated.connect(self._tray_activated)
        self._tray.setToolTip("CRACKA AI v3.0")
        self._tray.show()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            self.raise_()

    def _apply_theme(self):
        """Apply current theme to main window."""
        t = THEMES["dark" if self._dark_mode else "light"]
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background: {t['bg']};
                color: {t['text']};
                font-family: Consolas;
            }}
            QFrame {{
                background: {t['bg2']};
            }}
        """)

    def _toggle_theme(self):
        self._dark_mode = not self._dark_mode
        global current_theme
        current_theme = "dark" if self._dark_mode else "light"
        self._theme_btn.setText("🌙" if self._dark_mode else "☀️")
        self._apply_theme()

    # ── Public API ────────────────────────────────────────────────────────────

    def set_status(self, text: str):
        """Update status + orb state."""
        mapping = {
            "Listening":          (LISTENING, "#00ff88"),
            "Thinking":           (THINKING,  "#ffab00"),
            "Speaking":           (SPEAKING,  "#bf80ff"),
            "Ready":              (IDLE,      "#00e5ff"),
            "Standby":            (IDLE,      "#005f6b"),
            "Initializing...":    (IDLE,      "#005f6b"),
            "Error - Recovering": (IDLE,      "#ff2d55"),
        }
        state, color = mapping.get(text, (IDLE, "#005f6b"))
        self._orb.set_state(state)
        self._status_lbl.setText(f"● {text.upper()}")
        self._status_lbl.setStyleSheet(
            f"color: {color}; font-size: 10px; font-family: Consolas;"
        )

        # Mic indicator
        if state == LISTENING:
            self._mic_lbl.setStyleSheet("color: #00ff88; font-size: 10px; font-family: Consolas;")
            self._mic_lbl.setText("◉ MIC ACTIVE")
        else:
            self._mic_lbl.setStyleSheet("color: #0a1f28; font-size: 10px; font-family: Consolas;")
            self._mic_lbl.setText("◉ MIC")

    def add_message(self, sender: str, message: str):
        """Thread-safe message add."""
        self._msg_queue.put((sender, message))

    def _process_queue(self):
        try:
            while True:
                sender, message = self._msg_queue.get_nowait()
                self._insert_message(sender, message)
        except queue.Empty:
            pass

    def _insert_message(self, sender: str, message: str):
        bubble = ChatBubble(sender, message)
        self._chat_layout.addWidget(bubble)
        # Auto scroll to bottom
        QTimer.singleShot(50, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        ))

    def show_threat_alert(self, threats: list):
        """Show network threat popup."""
        dialog = ThreatAlertDialog(threats, self)
        dialog.exec_()

        # Tray notification too
        self._tray.showMessage(
            "⚠ CRACKA SECURITY ALERT",
            f"{len(threats)} network threat(s) detected!",
            QSystemTrayIcon.Warning,
            5000
        )

    def set_on_activate(self, callback):
        self._on_activate = callback

    def set_active(self, active: bool):
        self._active = active
        self.set_status("Listening" if active else "Standby")

    def _on_orb_click(self):
        self._active = not self._active
        if self._active:
            self.set_status("Listening")
            self.add_message("System", "Cracka activated!")
            if self._on_activate:
                threading.Thread(target=self._on_activate, daemon=True).start()
        else:
            self.set_status("Standby")
            self.add_message("System", "Cracka standing by.")

    def _on_quick_command(self, command: str):
        """Handle quick action button click."""
        self.add_message("You", command)
        self.set_status("Thinking")
        try:
            from core.ai_brain import process
            def run():
                response = process(command)
                if response:
                    self.add_message("Cracka", response)
                    from core.voice_engine import speak
                    speak(response)
                self.set_status("Listening")
            threading.Thread(target=run, daemon=True).start()
        except Exception as e:
            self.add_message("System", f"Error: {e}")
            self.set_status("Standby")

    def run(self):
        self.set_status("Standby")
        self.add_message("System", "CRACKA AI v3.0 ready. Click the orb or say 'Cracka'.")

    def closeEvent(self, event):
        """
        X button → poora Cracka band karo.
        Tray icon → minimize (hide).
        """
        import sys
        self._tray.hide()
        event.accept()
        QApplication.quit()
        sys.exit(0)


# ── App entry point ───────────────────────────────────────────────────────────
def create_app():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    return app


# ── Standalone test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = create_app()
    gui = CrackaGUI()
    gui.show()

    def demo():
        import time
        time.sleep(1)
        gui.add_message("Cracka", "Hello Boss! I am ready.")
        time.sleep(1)
        gui.set_status("Listening")
        time.sleep(2)
        gui.add_message("You", "open youtube")
        gui.set_status("Thinking")
        time.sleep(1.5)
        gui.add_message("Cracka", "Opening YouTube Boss!")
        gui.set_status("Speaking")
        time.sleep(2)
        gui.set_status("Listening")
        time.sleep(2)
        # Test threat alert
        gui.show_threat_alert([{
            "severity": "HIGH",
            "process": "unknown.exe",
            "hostname": "185.220.101.47",
            "remote_port": 4444,
            "alerts": ["Metasploit default port", "Unknown process on external IP"]
        }])

    threading.Thread(target=demo, daemon=True).start()
    gui.run()
    sys.exit(app.exec_())