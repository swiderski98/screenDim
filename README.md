# screenDim
In multi-display environment, gradually turns-off unused screens

# HOW TO RUN:
1) pip install monitorcontrol pyqt5 pyautogui wmi
2) python screenDimmer.py

# HOW IT WORKS:
1) A tray icon appeears
2) Single-click on icon to toggle active/inactive
3) Double-click to exit the program
4) Right-click to display the settings (saved to a .json file)
5) If active, program check mouse activity on every disaply
6) If no mouse activity, then display is slowly being turned off (brightness -> low & pixels -> black)
7) On mouse movement, the display goes back to original state
8) Idea is to avoid switching off displays completely so the operating system does not mess up the windows arrangement

# AVAILABLE SETTINGS:
- CHECK_TIME = 1000   # mouse movement checking period in [ms]
- DIM_STEP = 1        # dimming step in [%]
- TIMEOUT = 180       # time to start dimming a display, in [s]
- DEFAULT_DIM = True  # True - program activated by default / False - program desactivated by default
- MIN_LEVEL = 2       # minimum brightness value allowed, in [%]
- FORCED_BRIGHT = 75  # brightness level to be forced manually

# TODOs:
- Potential issue: May firstly check if <readLuminance> worked (try), and only if worked assign level_default !
- May use some power-saving mode for modern display (still keeping display detected by the operating system)
- May apply semi-transparent background for older displays to achive gradient dimming
- Full testing and adaptation to different OS (was written on Windows)
- Apply the dim-layer to all virtual desktops (not only the current one)
- Do not display the dim-layer window as a program in the bottom bar; do not disturb user when applying the dim-layer
