# setup_wifi.py — script utilitaire a executer UNE seule fois depuis
# le REPL pour :
#   1. Connecter le Pico W au WiFi.
#   2. Installer la bibliotheque usb-device-keyboard via mip.
#
# Ne PAS placer ce fichier en autorun (boot.py / main.py).
# A lancer manuellement : `mpremote run setup_wifi.py`
# ou depuis le REPL : `exec(open("setup_wifi.py").read())`.
#
# Apres execution reussie, la dependance est installee dans
# /lib/usb/device/ et persiste a travers les redemarrages.

import network
import rp2
import time

SSID = "domo"
PASSWORD = "th1Sp4((!))"
COUNTRY = "FR"
TIMEOUT_S = 10


def connect_wifi():
    """Tenter une connexion WiFi et retourner l'adresse IP obtenue."""
    rp2.country(COUNTRY)
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)

    deadline = time.ticks_add(time.ticks_ms(), TIMEOUT_S * 1000)
    while time.ticks_diff(deadline, time.ticks_ms()) > 0:
        if wlan.isconnected():
            return wlan.ifconfig()[0]
        time.sleep_ms(200)
    raise RuntimeError("Echec de connexion WiFi")


def install_keyboard_lib():
    """Telecharger et installer usb-device-keyboard depuis micropython-lib."""
    import mip
    mip.install("usb-device-keyboard")


def main():
    print("Connexion WiFi en cours...")
    ip = connect_wifi()
    print("Connecte. IP:", ip)

    print("Installation de usb-device-keyboard...")
    install_keyboard_lib()
    print("Installation terminee.")

    print("Verification de l'import :")
    from usb.device.keyboard import KeyboardInterface, KeyCode  # noqa: F401
    print("OK — bibliotheque operationnelle.")


main()
