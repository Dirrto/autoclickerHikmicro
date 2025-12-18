"""
Prueba REAL de automatización por imagen (misma lógica que Hikmicro)
- Template matching (OpenCV)
- Click físico controlado
- Restauración y foco de ventana
- Protección contra minimización accidental
"""

import time
import os
import csv
import datetime
import logging

import cv2
import numpy as np
import pyautogui
from pywinauto import Application
from pywinauto.findwindows import find_windows

# ================= CONFIG =================

WINDOW_TITLE = r"HIKMICRO Analyzer"
TEMPLATE_PATH = "templates/restart_images.png"

POLL_INTERVAL_SECONDS = 3600 #Una hora
MATCH_THRESHOLD = 0.95

TOP_SAFE_MARGIN = 90     # px prohibidos cerca de barra de título
LOG_DIR = "logs"
LOG_CSV = os.path.join(LOG_DIR, "actions.csv")

# ==========================================

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, "debug.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def log_action(action, comment):
    timestamp = datetime.datetime.now().isoformat(timespec="seconds")

    # Consola (log en vivo)
    print(f"[{timestamp.replace('T',' ')}] {action:<9} | {comment}")

    # CSV
    write_header = not os.path.exists(LOG_CSV)
    with open(LOG_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["timestamp", "action", "comment"])
        writer.writerow([timestamp, action, comment])


def restore_and_focus_window(title_regex):
    wins = find_windows(title_re=title_regex)
    if not wins:
        log_action("NO_CLICK", "window-not-found")
        return None

    app = Application(backend="uia").connect(handle=wins[0])
    win = app.window(handle=wins[0])

    if win.is_minimized():
        win.restore()
        time.sleep(0.5)

    win.set_focus()
    win.wait("ready", timeout=5)
    return win


def template_match_and_click(win):
    rect = win.rectangle()
    left, top, right, bottom = rect.left, rect.top, rect.right, rect.bottom
    width, height = right - left, bottom - top

    screenshot = pyautogui.screenshot(region=(left, top, width, height))
    gray_screen = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)

    template = cv2.imread(TEMPLATE_PATH, cv2.IMREAD_GRAYSCALE)
    if template is None:
        raise RuntimeError("Template no encontrado")

    res = cv2.matchTemplate(gray_screen, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)

    if max_val < MATCH_THRESHOLD:
        log_action("NO_CLICK", f"no-match ({max_val:.2f})")
        return

    h, w = template.shape
    cx = left + max_loc[0] + w // 2
    cy = top + max_loc[1] + h // 2

    if cy < top + TOP_SAFE_MARGIN:
        log_action("NO_CLICK", "match-too-close-to-titlebar")
        return

    pyautogui.moveTo(cx, cy, duration=0.2)
    pyautogui.click()

    log_action("CLICK", f"clicked ({max_val:.2f})")


def main_loop():
    print("Automatización por imagen iniciada (CTRL+C para detener)\n")

    while True:
        try:
            win = restore_and_focus_window(WINDOW_TITLE)
            if win is not None:
                template_match_and_click(win)

            time.sleep(POLL_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            print("\nScript detenido por el usuario.")
            break

        except Exception as e:
            log_action("ERROR", str(e))
            time.sleep(10)


if __name__ == "__main__":
    main_loop()