# Émulation clavier USB sur Raspberry Pi Pico W — Mise en place

Guide pas à pas pour transformer un Pico W en clavier USB HID avec MicroPython, en utilisant la bibliothèque officielle `usb-device-keyboard` installée via `mip` par WiFi.

---

## Prérequis

| Élément | Détail |
|---|---|
| Carte | Raspberry Pi Pico W |
| Câble | USB type A vers micro-USB (data, pas seulement alim.) |
| Firmware | MicroPython **≥ 1.23** pour RPI_PICO_W |
| Outil hôte | Thonny ou `mpremote` |
| Réseau | WiFi 2,4 GHz accessible |

---

## Étape 1 — Flasher MicroPython

1. Télécharger le firmware : <https://micropython.org/download/RPI_PICO_W/> (fichier `.uf2`).
2. Maintenir le bouton **BOOTSEL** enfoncé puis brancher le câble USB.
3. Le lecteur `RPI-RP2` apparaît sur l'ordinateur.
4. Glisser le fichier `.uf2` dessus.
5. Le Pico W redémarre automatiquement en MicroPython.

---

## Étape 2 — Ouvrir le REPL

Avec `mpremote` :

```bash
mpremote connect auto
```

Ou via Thonny : *Run → Configure interpreter → MicroPython (Raspberry Pi Pico)*.

Le prompt `>>>` confirme la connexion.

---

## Étape 3 — Connecter le Pico W au WiFi

Saisir dans le REPL (adapter SSID et mot de passe) :

```python
import network, time, rp2

rp2.country("FR")
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect("MON_SSID", "MON_MOT_DE_PASSE")

for _ in range(20):
    if wlan.isconnected():
        break
    time.sleep(0.5)

print("IP:", wlan.ifconfig()[0] if wlan.isconnected() else "echec")
```

Une adresse IP s'affiche → réseau OK.

---

## Étape 4 — Installer la bibliothèque

Toujours dans le REPL :

```python
import mip
mip.install("usb-device-keyboard")
```

Le paquet et sa dépendance `usb-device` se copient dans `/lib/usb/device/`.

Vérification :

```python
from usb.device.keyboard import KeyboardInterface, KeyCode
print("OK")
```

---

## Étape 5 — Créer `main.py` avec sécurité BOOTSEL

> **Important** : sans la sécurité, un bug dans `main.py` rendra le Pico W injoignable, et la seule solution sera de reflasher le firmware (perte des fichiers).

Copier ce code dans `main.py` à la racine du Pico W :

```python
# main.py
import time
import rp2
from machine import Pin

led = Pin("LED", Pin.OUT)
SAFETY_WINDOW_MS = 3000

def safe_mode_requested():
    """Retourne True si BOOTSEL est presse pendant la fenetre de demarrage."""
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

kbd = KeyboardInterface()
usb.device.get().init(kbd, builtin_driver=True)

while not kbd.is_open():
    time.sleep_ms(50)

# Exemple : envoyer "HI" toutes les 5 secondes
try:
    while True:
        kbd.send_keys([KeyCode.H, KeyCode.I])
        time.sleep_ms(50)
        kbd.send_keys([])
        time.sleep(5)
except Exception as e:
    print("Erreur:", e)
    raise SystemExit
```

Transfert via `mpremote` :

```bash
mpremote connect auto cp main.py :main.py
```

Ou via Thonny : *File → Save as → Raspberry Pi Pico → main.py*.

---

## Étape 6 — Tester

1. Redémarrer le Pico W (débrancher/rebrancher ou `machine.soft_reset()`).
2. La LED clignote pendant 3 secondes — **ne pas** presser BOOTSEL.
3. Le Pico W se réénumère en clavier HID.
4. Ouvrir un éditeur de texte sur l'ordinateur : la frappe "HI" s'affiche toutes les 5 secondes.

---

## Procédure de récupération

### Récupération douce (depuis MicroPython)

À chaque démarrage, maintenir BOOTSEL pendant que la LED clignote → `main.py` saute l'init HID, le REPL reste accessible pour corriger le code.

### Récupération matérielle (dernier recours)

Si le Pico W ne répond plus du tout :

1. Débrancher.
2. Maintenir BOOTSEL physique.
3. Rebrancher tout en gardant BOOTSEL.
4. Relâcher dès que `RPI-RP2` apparaît.
5. Reflasher le `.uf2` MicroPython.

**Cette opération efface tous les fichiers `.py`** → versionner le code en local avant chaque déploiement.

---

## Aide-mémoire des commandes

| Action | Commande |
|---|---|
| Connexion REPL | `mpremote connect auto` |
| Lister fichiers du Pico | `mpremote ls` |
| Copier un fichier | `mpremote cp main.py :main.py` |
| Récupérer un fichier | `mpremote cp :main.py main.py` |
| Soft reset | `mpremote reset` ou `Ctrl+D` dans le REPL |
| Effacer un fichier | `mpremote rm :main.py` |
| Installer un paquet (hôte) | `mpremote mip install usb-device-keyboard` |
| Installer un paquet (réseau) | `import mip; mip.install("usb-device-keyboard")` |

---

## Codes touches utiles

```python
from usb.device.keyboard import KeyCode

# Lettres
KeyCode.A, KeyCode.B, ..., KeyCode.Z

# Chiffres
KeyCode.N1, KeyCode.N2, ..., KeyCode.N0

# Modificateurs (a passer dans send_keys avec d'autres touches)
KeyCode.LEFT_CTRL, KeyCode.LEFT_SHIFT, KeyCode.LEFT_ALT, KeyCode.LEFT_GUI

# Speciales
KeyCode.ENTER, KeyCode.ESCAPE, KeyCode.BACKSPACE, KeyCode.TAB, KeyCode.SPACE
KeyCode.F1, ..., KeyCode.F12
KeyCode.RIGHT_ARROW, KeyCode.LEFT_ARROW, KeyCode.UP_ARROW, KeyCode.DOWN_ARROW
```

Exemple combinaison Ctrl+C :

```python
kbd.send_keys([KeyCode.LEFT_CTRL, KeyCode.C])
time.sleep_ms(50)
kbd.send_keys([])  # relache
```

---

## Ressources

- Lib officielle : <https://github.com/micropython/micropython-lib/tree/master/micropython/usb>
- Exemple complet : <https://github.com/micropython/micropython-lib/blob/master/micropython/usb/examples/device/keyboard_example.py>
- Firmware Pico W : <https://micropython.org/download/RPI_PICO_W/>
- Documentation `mpremote` : <https://docs.micropython.org/en/latest/reference/mpremote.html>

---

## Attention : usage légitime uniquement

Un Pico W configuré en HID peut être utilisé pour des projets parfaitement légitimes (raccourcis clavier, automatisations, accessibilité, macros). Ce même type de montage peut aussi être détourné en outil d'attaque type "BadUSB". Tout déploiement doit se limiter à du matériel personnel ou à des environnements où l'autorisation est explicite.