"""
Exemple d'utilisation du module DFPlayer Mini sur ESP32.

Cablage typique :
    DFPlayer VCC  -> 5V
    DFPlayer GND  -> GND
    DFPlayer RX   -> ESP32 GPIO17 (TX) via resistance 1k
    DFPlayer TX   -> ESP32 GPIO16 (RX)
    DFPlayer SPK1 -> haut-parleur
    DFPlayer SPK2 -> haut-parleur

Carte SD : structure FAT32 avec fichiers nommes 0001.mp3, 0002.mp3 ...
a la racine, ou dossiers 01/ ... 99/ contenant 001.mp3 ... 255.mp3.
"""

from machine import UART, Pin
import time
from dfplayer import DFPlayer, EQ_BASS, SOURCE_SD


def main():
    uart = UART(1, baudrate=9600, tx=Pin(17), rx=Pin(16))
    mp3 = DFPlayer(uart, ack=False, do_reset=True)

    print("nb fichiers SD :", mp3.query_file_count(SOURCE_SD))
    print("version firmware :", mp3.query_version())

    mp3.volume(20)
    mp3.eq(EQ_BASS)

    print("lecture piste 1")
    mp3.play(1)
    time.sleep(5)

    print("piste suivante")
    mp3.next()
    time.sleep(3)

    print("pause")
    mp3.pause()
    time.sleep(2)

    print("reprise")
    mp3.resume()
    time.sleep(3)

    # Lecture d'un fichier dans un sous-dossier (02/003.mp3)
    mp3.play_folder(folder=2, track=3)
    time.sleep(3)

    mp3.stop()


def boucle_evenements():
    """Demonstration de la reception d'evenements asynchrones."""
    uart = UART(1, baudrate=9600, tx=Pin(17), rx=Pin(16))
    mp3 = DFPlayer(uart)

    mp3.volume(15)
    mp3.play(1)

    while True:
        evt = mp3.poll()
        if evt is not None:
            code, param = evt
            print("evenement 0x%02X parametre=%d" % (code, param))
        time.sleep_ms(100)


if __name__ == "__main__":
    main()