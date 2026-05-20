# main.py — point d'entree principal du clavier HID.
#
# Sequence de demarrage :
#   1. Fenetre de securite de 3 s pendant laquelle la LED clignote.
#      Maintenir BOOTSEL durant cette fenetre pour conserver le REPL
#      et eviter le basculement en mode HID.
#   2. Sans appui, initialisation de l'interface clavier USB HID.
#   3. Boucle de scrutation des 4 entrees configurees dans KEYS, avec
#      gestion tap / hold par touche.

import time
import rp2
from machine import ADC, Pin

led = Pin("LED", Pin.OUT)
SAFETY_WINDOW_MS = 3000


def safe_mode_requested():
    """Retourner True si BOOTSEL est presse pendant la fenetre de demarrage."""
    deadline = time.ticks_add(time.ticks_ms(), SAFETY_WINDOW_MS)
    while time.ticks_diff(deadline, time.ticks_ms()) > 0:
        led.toggle()
        if rp2.bootsel_button():
            led.on()
            return True
        time.sleep_ms(100)
    led.off()
    return False


if safe_mode_requested():
    print("Mode REPL conserve. HID desactive.")
    raise SystemExit

# --- Au-dela de ce point, le Pico W devient un clavier HID ---
import usb.device
from usb.device.keyboard import KeyboardInterface, KeyCode

# ---------------------------------------------------------------------------
# Configuration des 4 touches fleches.
#
# Cablage attendu pour chaque bouton :
#   GPIO <-- bouton --> GND
#   Le PULL_UP interne maintient la ligne a 1 au repos ; l'appui tire a 0.
#
# Champs par entree :
#   - name      : libelle pour les logs.
#   - mode      : "gpio" (numerique) ou "adc" (analogique 0..65535).
#   - pin       : numero de broche GPIO.
#   - tap       : KeyCode HID emis sur appui court.
#   - hold      : KeyCode HID emis sur appui maintenu, ou None.
#                 Pour des fleches, laisser None : l'OS gere la repetition
#                 automatique quand la touche reste enfoncee.
#   - threshold : seuil de detection.
#       * mode "gpio" : nombre de scans consecutifs actifs (debounce).
#                       Avec POLL_INTERVAL_MS=10, threshold=2 ≈ 20 ms.
#       * mode "adc"  : 0..65535, appui si lecture >= seuil.
#   - hold_ms   : duree (ms) au-dela de laquelle un appui devient un hold.
#                 Ignore si hold vaut None.
#   - pull      : "up", "down" ou None. Mode "gpio" uniquement.
#
# Semantique tap / hold :
#   - hold = None        → comportement clavier classique : tap emis tant
#                          que l'entree est active (auto-repeat OS).
#   - hold = <KeyCode>   → relache < hold_ms → emission breve de tap.
#                          maintien >= hold_ms → emission de hold tant
#                          que l'entree reste active.
# ---------------------------------------------------------------------------
KEYS = [
    {"name": "UP",    "mode": "gpio", "pin": 10, "tap": KeyCode.UP_ARROW,
     "hold": None, "threshold": 2, "hold_ms": 250, "pull": "up"},
    {"name": "DOWN",  "mode": "gpio", "pin": 11, "tap": KeyCode.DOWN_ARROW,
     "hold": None, "threshold": 2, "hold_ms": 250, "pull": "up"},
    {"name": "LEFT",  "mode": "gpio", "pin": 12, "tap": KeyCode.LEFT_ARROW,
     "hold": None, "threshold": 2, "hold_ms": 250, "pull": "up"},
    {"name": "RIGHT", "mode": "gpio", "pin": 13, "tap": KeyCode.RIGHT_ARROW,
     "hold": None, "threshold": 2, "hold_ms": 250, "pull": "up"},
]

POLL_INTERVAL_MS = 10
TAP_EMIT_MS = 30  # duree d'emission du code tap apres relachement court


def build_inputs(keys):
    """Instancier ADC ou Pin selon le mode declare et initialiser l'etat."""
    inputs = []
    for cfg in keys:
        if cfg["mode"] == "adc":
            reader = ADC(cfg["pin"])
        elif cfg["mode"] == "gpio":
            pull = {"up": Pin.PULL_UP, "down": Pin.PULL_DOWN, None: None}[cfg["pull"]]
            reader = Pin(cfg["pin"], Pin.IN, pull) if pull else Pin(cfg["pin"], Pin.IN)
        else:
            raise ValueError("mode inconnu: " + cfg["mode"])
        inputs.append({
            "cfg": cfg,
            "reader": reader,
            "debounce": 0,    # compteur de scans actifs (mode gpio)
            "state": "idle",  # idle | waiting | holding | tap_emit
            "press_start": 0,
            "tap_end": 0,
        })
    return inputs


def is_active(entry):
    """Evaluer l'etat physique brut d'une entree apres application du seuil.

    ADC  : actif si lecture >= seuil.
    GPIO : actif si N scans consecutifs au niveau attendu (N = threshold).
    """
    cfg = entry["cfg"]
    reader = entry["reader"]
    if cfg["mode"] == "adc":
        return reader.read_u16() >= cfg["threshold"]
    active_level = 0 if cfg["pull"] == "up" else 1
    raw_pressed = reader.value() == active_level
    entry["debounce"] = entry["debounce"] + 1 if raw_pressed else 0
    return entry["debounce"] >= cfg["threshold"]


def update_state(entry, active, now_ms):
    """Faire avancer la machine a etats tap/hold et retourner le code a emettre.

    Renvoyer None si la touche ne doit rien emettre durant ce cycle.
    """
    cfg = entry["cfg"]
    has_hold = cfg.get("hold") is not None

    # Sans code de hold : pas de discrimination, emission directe pendant
    # toute la duree d'appui — comportement clavier classique.
    if not has_hold:
        return cfg["tap"] if active else None

    state = entry["state"]
    hold_ms = cfg["hold_ms"]

    if state == "idle":
        if active:
            entry["state"] = "waiting"
            entry["press_start"] = now_ms
        return None

    if state == "waiting":
        if not active:
            # Relachement avant le seuil de hold : il s'agit d'un tap.
            # Programmer une emission breve pour que l'hote enregistre
            # une frappe distincte du repos.
            entry["state"] = "tap_emit"
            entry["tap_end"] = time.ticks_add(now_ms, TAP_EMIT_MS)
            return cfg["tap"]
        if time.ticks_diff(now_ms, entry["press_start"]) >= hold_ms:
            entry["state"] = "holding"
            return cfg["hold"]
        return None

    if state == "holding":
        if not active:
            entry["state"] = "idle"
            return None
        return cfg["hold"]

    if state == "tap_emit":
        if time.ticks_diff(entry["tap_end"], now_ms) <= 0:
            entry["state"] = "idle"
            return None
        return cfg["tap"]

    return None


kbd = KeyboardInterface()
usb.device.get().init(kbd, builtin_driver=True)

while not kbd.is_open():
    time.sleep_ms(50)

inputs = build_inputs(KEYS)

# Boucle principale : agreger les codes a emettre puis envoyer au HID
# uniquement lorsque l'ensemble change, pour eviter le spam USB.
try:
    previous = None
    while True:
        now_ms = time.ticks_ms()
        active_codes = []
        for entry in inputs:
            code = update_state(entry, is_active(entry), now_ms)
            if code is not None:
                active_codes.append(code)
        if active_codes != previous:
            kbd.send_keys(active_codes)
            previous = active_codes
        time.sleep_ms(POLL_INTERVAL_MS)
except Exception as e:
    print("Erreur:", e)
    raise SystemExit
