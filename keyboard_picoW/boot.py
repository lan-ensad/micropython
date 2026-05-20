# boot.py — execute avant main.py a chaque demarrage du Pico W.
# Maintenir ce fichier minimal : ne JAMAIS initialiser le mode USB HID
# ici, sous peine de court-circuiter le garde-fou BOOTSEL place dans
# main.py et de rendre la carte injoignable en cas de bug.

print("boot.py: demarrage Pico W")
