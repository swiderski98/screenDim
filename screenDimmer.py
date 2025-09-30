# HOW TO RUN:
# 1) pip install monitorcontrol pyqt5 pyautogui wmi
# 2) python screenDimmer.py

# HOW IT WORKS:
# 1) A tray icon appeears
# 2) Single-click on icon to toggle active/inactive
# 3) Double-click to exit the program
# 4) If active, program check mouse activity on every disaply
# 5) If no mouse activity, then display is slowly being turned off (brightness -> low & pixels -> black)
# 6) On mouse movement, the display goes back to original value
# 7) Idea is to avoid switching off displays completely so the operating system does not mess up the windows arrangement

# TODOs:
# 1) Potential issue: May firstly check if <readLuminance> worked (try) and only if worked assign level_default !
# 2) May use some power-saving mode for modern display (still keeping display detected by the operating system)
# 3) May apply semi-transparent background for older displays to achive gradient dimming
# 4) Full testing and adaptation to different OS (was written on Windows)
# 5) Add options to tray icon (to change the parameters on-the-fly)

CHECK_TIME = 1000   # mouse movement checking period in [ms]
DIM_STEP = 1        # dimming step in [%]
TIMEOUT = 120       # time to start dimming a display, in [s]
DEFAULT_DIM = True  # True - program activated by default / False - program desactivated by default
MIN_LEVEL = 5       # minimum brightness value allowed, in [%]

import sys, time
from PyQt5 import QtWidgets, QtCore 
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor
import pyautogui

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
                self.overlay.showFullScreen()
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
                self.overlay.showFullScreen()
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


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    manager = MonitorManager(app, timeout=TIMEOUT)
    tray = TrayIcon(manager, app)
    sys.exit(app.exec_())