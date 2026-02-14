# HOW TO RUN:
# 1) pip install monitorcontrol pyqt5 pyautogui wmi
# 2) python screenDimmer.py

# HOW IT WORKS:
# 1) A tray icon appeears
# 2) Single-click on icon to toggle active/inactive
# 3) Double-click to exit the program
# 4) Right-click to display the settings (saved to a .json file)
# 5) If active, program checks mouse activity on every display
# 6) If no mouse activity, then display is slowly being turned off (brightness -> low & pixels -> black)
# 7) On mouse movement, the display goes back to original state
# 8) Idea is to avoid switching off displays completely so the operating system does not mess up the windows arrangement

# TODOs:
# 1) Potential issue: May firstly check if <readLuminance> worked (try) and only if worked assign level_default !
# 2) May use some power-saving mode for modern display (still keeping display detected by the operating system)
# 3) May apply semi-transparent background for older displays to achive gradient dimming
# 4) Full testing and adaptation to different OS (was written on Windows)
# 5) Apply the dim-layer to all virtual desktops (not only the current one)
# 6) Do not display the dim-layer window as a program in the bottom bar; do not disturb user when applying the dim-layer
# 7) Identify the screens and allow for separate brightness setting, and memorize the screens and adapt program on-the-fly
# 8) Allow to export and import settings for different screen configurations, and switch on-the-fly if configuration has changed


CHECK_TIME = 1000   # mouse movement checking period in [ms]
DIM_STEP = 1        # dimming step in [%]
TIMEOUT = 180       # time to start dimming a display, in [s]
DEFAULT_DIM = True  # True - program activated by default / False - program desactivated by default
MIN_LEVEL = 2       # minimum brightness value allowed, in [%]
FORCED_BRIGHT = 75  # brightness level to be set manually

import json, os
import sys, time
from PyQt5 import QtWidgets, QtCore 
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor
import pyautogui

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")

# Try to import monitorcontrol (for external monitors)
try:
    from monitorcontrol import get_monitors
    MONITORCONTROL_AVAILABLE = True
except ImportError:
    MONITORCONTROL_AVAILABLE = False

# Try to import WMI (for laptop internal display)
try:
    import wmi
    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False


def load_settings():
    """Load saved user settings if file exists."""
    global CHECK_TIME, DIM_STEP, TIMEOUT, DEFAULT_DIM, MIN_LEVEL
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
            CHECK_TIME = data.get("CHECK_TIME", CHECK_TIME)
            DIM_STEP = data.get("DIM_STEP", DIM_STEP)
            TIMEOUT = data.get("TIMEOUT", TIMEOUT)
            DEFAULT_DIM = data.get("DEFAULT_DIM", DEFAULT_DIM)
            MIN_LEVEL = data.get("MIN_LEVEL", MIN_LEVEL)
            print(f"Settings loaded from {SETTINGS_FILE}")
        except Exception as e:
            print(f"Failed to load settings: {e}")
    else:
        print("No settings file found, using defaults.")


def save_settings():
    """Save current settings to file."""
    data = {
        "CHECK_TIME": CHECK_TIME,
        "DIM_STEP": DIM_STEP,
        "TIMEOUT": TIMEOUT,
        "DEFAULT_DIM": DEFAULT_DIM,
        "MIN_LEVEL": MIN_LEVEL,
    }
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(data, f, indent=4)
        print(f"Settings saved to {SETTINGS_FILE}")
    except Exception as e:
        print(f"Failed to save settings: {e}")


def set_internal_brightness(level):
    """Set brightness on laptop panel using WMI"""
    if not WMI_AVAILABLE:
        return False
    try:
        w = wmi.WMI(namespace="root\\wmi")
        methods = w.WmiMonitorBrightnessMethods()[0]
        methods.WmiSetBrightness(level, 1)
        return True
    except Exception as e:
        print(f"Laptop brightness control failed: {e}")
        return False


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, tray):
        super().__init__()
        self.tray = tray
        self.setWindowTitle("Display Dimmer Settings")
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.setFixedWidth(320)

        layout = QtWidgets.QFormLayout()

        # Editable fields for current parameters
        self.check_time = QtWidgets.QSpinBox()
        self.check_time.setRange(100, 1000)
        self.check_time.setValue(CHECK_TIME)

        self.dim_step = QtWidgets.QSpinBox()
        self.dim_step.setRange(1, 5)
        self.dim_step.setValue(DIM_STEP)

        self.timeout = QtWidgets.QSpinBox()
        self.timeout.setRange(10, 3600)
        self.timeout.setValue(TIMEOUT)

        self.min_level = QtWidgets.QSpinBox()
        self.min_level.setRange(1, 10)
        self.min_level.setValue(MIN_LEVEL)

        self.default_dim = QtWidgets.QCheckBox()
        self.default_dim.setChecked(DEFAULT_DIM)

        self.forced_brightness = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.forced_brightness.setRange(5, 100)
        self.forced_brightness.setValue(FORCED_BRIGHT)
        self.forced_brightness_label = QtWidgets.QLabel("Brightness %")

        self.forced_brightness.valueChanged.connect(
            lambda v: self.forced_brightness_label.setText(f"{v} %")
        )

        apply_btn = QtWidgets.QPushButton("Apply Brightness")
        apply_btn.clicked.connect(self.apply_forced_brightness)

        layout.addRow("Mouse Check (ms):", self.check_time)
        layout.addRow("Dim Step (%):", self.dim_step)
        layout.addRow("Timeout (s):", self.timeout)
        layout.addRow("Min Brightness (%):", self.min_level)
        layout.addRow("Enabled by Default:", self.default_dim)
        layout.addRow(QtWidgets.QLabel("Forced Default Brightness"))
        layout.addRow(self.forced_brightness, self.forced_brightness_label)
        layout.addRow(apply_btn)

        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.apply)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
        self.setLayout(layout)

    def apply(self):
        """Apply new settings to the running app"""
        global CHECK_TIME, DIM_STEP, TIMEOUT, MIN_LEVEL, DEFAULT_DIM

        CHECK_TIME = self.check_time.value()
        DIM_STEP = self.dim_step.value()
        TIMEOUT = self.timeout.value()
        MIN_LEVEL = self.min_level.value()
        DEFAULT_DIM = self.default_dim.isChecked()

        # Update timer interval and monitor timeout dynamically
        self.tray.manager.timer.setInterval(CHECK_TIME)
        self.tray.manager.timeout = TIMEOUT

        save_settings()
        self.accept()

    def apply_forced_brightness(self):
        """Apply temporary brightness to all monitors immediately"""
        value = self.forced_brightness.value()
        print(f"Applying forced brightness: {value}%")

        for m in self.tray.manager.monitors:
            m.level_default = value
            # Only change brightness if not dimmed
            if not m.dimmed:
                try:
                    # Detect monitor type dynamically to avoid import issues
                    if "Laptop" in type(m).__name__:
                        set_internal_brightness(value)
                        m.level_current = value
                    elif "External" in type(m).__name__ and m.communicative and MONITORCONTROL_AVAILABLE:
                        with get_monitors()[m.index] as mon:
                            mon.set_luminance(value)
                        m.level_current = value
                except Exception as e:
                    print(f"Failed to set brightness for monitor: {e}")


class BlackOverlay(QtWidgets.QWidget):
    def __init__(self, screen_geometry):
        super().__init__()
        self.setGeometry(screen_geometry)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.setStyleSheet("background-color: black;")
        self.hide()


class BaseMonitorWrapper:
    """Base class for all monitors"""
    def __init__(self, geom):
        self.geom = geom
        self.overlay = BlackOverlay(geom)
        self.last_seen = time.time()
        self.dimmed = False
        self.dimmed_completely = False
        self.level_default = 70
        self.level_current = 70
        self.level_min = 10
        self.communicative = True

    def dim(self):
        raise NotImplementedError

    def restore(self):
        raise NotImplementedError


class LaptopMonitorWrapper(BaseMonitorWrapper):
    """Laptop panel controlled via WMI"""
    def __init__(self,geom):
        super().__init__(geom)
        if WMI_AVAILABLE:
            w = wmi.WMI(namespace="root\\wmi")
            methods = w.WmiMonitorBrightnessMethods()[0]
            self.level_default = w.WmiMonitorBrightness()[0].CurrentBrightness
            # May firstly check if CurrentBrightness worked (try) and only if worked assign level_default !
            if self.level_default < MIN_LEVEL:
                self.level_default = MIN_LEVEL
            if self.level_min > self.level_default:
                self.level_min = self.level_default
            self.level_current = self.level_default

    def dim(self):
        if not self.dimmed_completely:
            if self.level_current > self.level_min:
                self.level_current = self.level_current - DIM_STEP
                set_internal_brightness(self.level_current)
            else:
                self.overlay.show()
                self.dimmed_completely = 1
                # TODO turn off completely or enter power saving mode
        self.dimmed = True

    def restore(self):
        if self.dimmed:
            set_internal_brightness(self.level_default)
            self.level_current = self.level_default
            if self.overlay.isVisible():
                self.overlay.hide()
            self.dimmed_completely = False
            self.dimmed = False


class ExternalMonitorWrapper(BaseMonitorWrapper):
    """External monitor controlled via DDC/CI (monitorcontrol)"""
    def __init__(self, geom, index):
        super().__init__(geom)
        self.index = index
        if MONITORCONTROL_AVAILABLE:
            try:
                with get_monitors()[self.index] as m:
                    self.level_default = m.get_luminance()
                    # May firstly check if get_luminance worked (try) and only if worked assign level_default !
                    if self.level_default < MIN_LEVEL:
                        self.level_default = MIN_LEVEL
                    if self.level_default < 10:
                        self.level_min = self.level_default
                    self.level_current = self.level_default
            except Exception as e:
                print(f"Failed to get luminance from external display.")
                self.communicative = False

    def dim(self):
        if not self.dimmed_completely:
            if self.level_current > self.level_min:
                self.level_current = self.level_current - DIM_STEP
                if MONITORCONTROL_AVAILABLE & self.communicative:
                    try:
                        with get_monitors()[self.index] as m:
                            m.set_luminance(self.level_current)
                    except Exception as e:
                        print(f"Brightness control failed on external {self.index}: {e}")
            else:
                self.overlay.show()
                self.dimmed_completely = True
                # TODO turn off completely or enter power saving mode
        self.dimmed = True

    def restore(self):
        if self.dimmed:
            if MONITORCONTROL_AVAILABLE:
                try:
                    with get_monitors()[self.index] as m:
                        m.set_luminance(self.level_default)
                        self.level_current = self.level_default
                except Exception as e:
                    print(f"Brightness restore failed on external {self.index}: {e}")
            if self.overlay.isVisible():
                self.overlay.hide()
            self.dimmed_completely = False
            self.dimmed = False


class MonitorManager(QtCore.QObject):
    def __init__(self, app, timeout=30):
        super().__init__()
        self.app = app
        self.timeout = timeout
        self.monitors = []
        self.enabled = True

        screens = app.screens()

        # If WMI works, assume first screen is laptop panel
        if WMI_AVAILABLE:
            print("Laptop panel detected via WMI.")
            self.monitors.append(LaptopMonitorWrapper(screens[0].geometry()))
            external_start = 1
        else:
            external_start = 0

        # Assign the rest as external monitors
        for i in range(external_start, len(screens)):
            geom = screens[i].geometry()
            self.monitors.append(ExternalMonitorWrapper(geom, i))

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.check_mouse)
        self.timer.start(CHECK_TIME)

    def check_mouse(self):
        if not self.enabled:
            #for m in self.monitors:
                #m.restore()
            return
        # otherwise continue checking the mouse position
        x, y = pyautogui.position()
        for m in self.monitors:
            if m.geom.contains(QtCore.QPoint(x, y)):
                m.last_seen = time.time()
                m.restore()
            else:
                if time.time() - m.last_seen > self.timeout:
                    m.dim()


class TrayIcon(QtWidgets.QSystemTrayIcon):
    def __init__(self, manager, app):
        super().__init__()
        self.manager = manager
        self.app = app
        self.active = DEFAULT_DIM

        # Create green/red circle icons dynamically
        self.icon_green = self.create_icon(QColor("green"))
        self.icon_red = self.create_icon(QColor("red"))

        self.setIcon(self.icon_green)
        self.setToolTip("Display Dimmer (active)")
        self.activated.connect(self.on_click)

        # Context menu with exit option
        menu = QtWidgets.QMenu()
        settings_action = menu.addAction("Settings")
        settings_action.triggered.connect(self.open_settings)
        exit_action = menu.addAction("Exit")
        exit_action.triggered.connect(self.app.quit)
        self.setContextMenu(menu)
        self.show()

    def create_icon(self, color):
        pix = QPixmap(16, 16)
        pix.fill(QtCore.Qt.transparent)
        painter = QPainter(pix)
        painter.setBrush(color)
        painter.setPen(QtCore.Qt.black)
        painter.drawEllipse(0, 0, 15, 15)
        painter.end()
        return QIcon(pix)

    def on_click(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.Trigger:  # single click
            self.active = not self.active
            self.manager.enabled = self.active
            self.setIcon(self.icon_green if self.active else self.icon_red)
            if not self.active:
                for m in self.manager.monitors:
                    m.restore()
            self.setToolTip(f"Display Dimmer ({'active' if self.active else 'disabled'})")
        elif reason == QtWidgets.QSystemTrayIcon.DoubleClick:  # double click
            for m in self.manager.monitors:
                m.restore()
            self.app.quit()

    def open_settings(self):
        dlg = SettingsDialog(self) # right click
        dlg.setWindowModality(QtCore.Qt.ApplicationModal)
        dlg.exec_()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    load_settings()
    manager = MonitorManager(app, timeout=TIMEOUT)
    tray = TrayIcon(manager, app)
    sys.exit(app.exec_())
