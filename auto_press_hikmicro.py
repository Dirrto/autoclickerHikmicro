"""
test_reloj_template_match_robusto.py
Automatización GUI por imagen (robusta a resolución y DPI)

- Template matching MULTI-ESCALA
- Matching por BORDES (Canny)
- Click físico controlado
- Log en CSV + consola
- Misma lógica que Hikmicro
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

WINDOW_TITLE = r"Reloj|Clock"
TEMPLATE_PATH = "templates/flag_clock.png"

POLL_INTERVAL_SECONDS = 5

MATCH_THRESHOLD = 0.65          # más permisivo
SCALES = np.linspace(0.05, 0.8, 17)

TOP_SAFE_MARGIN = 90            # px protegidos (barra de título)
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


# ================= LOG ====================

def log_action(action, comment):
    timestamp = datetime.datetime.now().isoformat(timespec="seconds")
    print(f"[{timestamp.replace('T',' ')}] {action:<9} | {comment}")

    write_header = not os.path.exists(LOG_CSV)
    with open(LOG_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["timestamp", "action", "comment"])
        writer.writerow([timestamp, action, comment])


# ============ WINDOW CONTROL ==============

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


# ============ MATCH + CLICK ===============

def template_match_and_click(win):
    rect = win.rectangle()
    left, top, right, bottom = rect.left, rect.top, rect.right, rect.bottom
    width, height = right - left, bottom - top

    screenshot = pyautogui.screenshot(region=(left, top, width, height))
    gray_screen = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)

    # Normalización + blur (robustez)
    gray_screen = cv2.GaussianBlur(gray_screen, (3, 3), 0)
    edges_screen = cv2.Canny(gray_screen, 50, 150)

    template = cv2.imread(TEMPLATE_PATH, cv2.IMREAD_GRAYSCALE)
    if template is None:
        log_action("ERROR", "template-not-found")
        return

    template = cv2.GaussianBlur(template, (3, 3), 0)
    edges_tpl = cv2.Canny(template, 50, 150)

    best_val = -1
    best_loc = None
    best_scale = None
    best_size = None

    for scale in SCALES:
        new_w = int(edges_tpl.shape[1] * scale)
        new_h = int(edges_tpl.shape[0] * scale)
        if new_w < 15 or new_h < 15:
            continue
        if new_w > edges_screen.shape[1] or new_h > edges_screen.shape[0]:
            continue

        tpl_resized = cv2.resize(edges_tpl, (new_w, new_h))
        res = cv2.matchTemplate(edges_screen, tpl_resized, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        if max_val > best_val:
            best_val = max_val
            best_loc = max_loc
            best_scale = scale
            best_size = (new_w, new_h)

    if best_val < MATCH_THRESHOLD:
        log_action("NO_CLICK", f"no-match (best={best_val:.2f})")
        return

    cx = left + best_loc[0] + best_size[0] // 2
    cy = top + best_loc[1] + best_size[1] // 2

    if cy < top + TOP_SAFE_MARGIN:
        log_action("NO_CLICK", "match-too-close-to-titlebar")
        return

    pyautogui.moveTo(cx, cy, duration=0.2)
    pyautogui.click()

    log_action(
        "CLICK",
        f"clicked (score={best_val:.2f}, scale={best_scale:.2f})"
    )


# ============== MAIN LOOP =================

def main_loop():
    print("\nAutomatización robusta por imagen iniciada (CTRL+C para detener)\n")

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
