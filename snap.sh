# Take a Dolphin screenshot (F9) and print its path.
cd "$(dirname "$0")" && python kbinput.py press F9 0.1 && sleep 2 && ls -t "$APPDATA/Dolphin Emulator/ScreenShots/SSPP52/"*.png | head -1
