import pyautogui
import os

try:
    screens = pyautogui.screenshot()
    screens.save("desktop_capture.png")
    print("Screenshot saved to desktop_capture.png")
except Exception as e:
    print(f"Failed to capture screen: {e}")
