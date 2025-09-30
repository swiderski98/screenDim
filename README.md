# screenDim
In multi-display environment, gradually turns-off unused screens

# HOW TO RUN:
1) pip install monitorcontrol pyqt5 pyautogui wmi
2) python screenDimmer.py

# HOW IT WORKS:
1) A tray icon appeears
2) Single-click on icon to toggle active/inactive
3) Double-click to exit the program
4) If active, program check mouse activity on every disaply
5) If no mouse activity, then display is slowly being turned off (brightness -> low & pixels -> black)
6) On mouse movement, the display goes back to original value
7) Idea is to avoid switching off displays completely so the operating system does not mess up the windows arrangement

# TODOs:
1) Potential issue: May firstly check if <readLuminance> worked (try) and only if worked assign level_default !
2) May use some power-saving mode for modern display (still keeping display detected by the operating system)
3) May apply semi-transparent background for older displays to achive gradient dimming
4) Full testing and adaptation to different OS (was written on Windows)
5) Add options to tray icon (to change the parameters on-the-fly)
