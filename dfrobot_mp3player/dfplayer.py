"""
Pilote MicroPython pour DFPlayer Mini (DFRobot DFR0299).

Communication UART 9600 bauds, 8N1.
Format des trames d'envoi (10 octets) :
    0x7E 0xFF 0x06 CMD ACK PH PL CKH CKL 0xEF

Le checksum est calcule sur les octets Version..ParametreLow :
    CK = -(0xFF + 0x06 + CMD + ACK + PH + PL) sur 16 bits.

Reference : https://wiki.dfrobot.com/dfr0299
"""

from machine import UART
import time

# --- Octets fixes de trame -------------------------------------------------
_START = 0x7E
_VERSION = 0xFF
_LENGTH = 0x06
_END = 0xEF

# --- Egaliseurs ------------------------------------------------------------
EQ_NORMAL = 0
EQ_POP = 1
EQ_ROCK = 2
EQ_JAZZ = 3
EQ_CLASSIC = 4
EQ_BASS = 5

# --- Sources de lecture ----------------------------------------------------
SOURCE_USB = 1
SOURCE_SD = 2
SOURCE_AUX = 3
SOURCE_SLEEP = 4
SOURCE_FLASH = 5

# --- Commandes de controle -------------------------------------------------
CMD_NEXT = 0x01
CMD_PREV = 0x02
CMD_PLAY_TRACK = 0x03
CMD_VOL_UP = 0x04
CMD_VOL_DOWN = 0x05
CMD_SET_VOLUME = 0x06
CMD_SET_EQ = 0x07
CMD_LOOP_TRACK = 0x08
CMD_SET_SOURCE = 0x09
CMD_STANDBY = 0x0A
CMD_NORMAL = 0x0B
CMD_RESET = 0x0C
CMD_RESUME = 0x0D
CMD_PAUSE = 0x0E
CMD_PLAY_FOLDER = 0x0F
CMD_DAC_GAIN = 0x10
CMD_REPEAT_ALL = 0x11
CMD_PLAY_MP3 = 0x12
CMD_INSERT_AD = 0x13
CMD_PLAY_LARGE_FOLDER = 0x14
CMD_STOP_AD = 0x15
CMD_STOP = 0x16
CMD_LOOP_FOLDER = 0x17
CMD_RANDOM = 0x18
CMD_LOOP_CURRENT = 0x19
CMD_DAC = 0x1A

# --- Commandes de requete --------------------------------------------------
CMD_QUERY_STATUS = 0x42
CMD_QUERY_VOLUME = 0x43
CMD_QUERY_EQ = 0x44
CMD_QUERY_FILES_USB = 0x47
CMD_QUERY_FILES_SD = 0x48
CMD_QUERY_FILES_FLASH = 0x49
CMD_QUERY_VERSION = 0x46
CMD_QUERY_TRACK_USB = 0x4B
CMD_QUERY_TRACK_SD = 0x4C
CMD_QUERY_TRACK_FLASH = 0x4D
CMD_QUERY_FILES_FOLDER = 0x4E
CMD_QUERY_FOLDERS = 0x4F

# --- Codes d'evenements asynchrones (poll) ---------------------------------
EVT_USB_INSERTED = 0x3A
EVT_USB_REMOVED = 0x3B
EVT_USB_FINISHED = 0x3C
EVT_SD_FINISHED = 0x3D
EVT_FLASH_FINISHED = 0x3E
EVT_INIT = 0x3F
EVT_ERROR = 0x40
EVT_ACK = 0x41


class DFPlayerError(Exception):
    """Erreur de communication avec le DFPlayer."""
    pass


class DFPlayer:
    """
    Pilote du module DFPlayer Mini.

    Exemple :
        from machine import UART, Pin
        from dfplayer import DFPlayer

        uart = UART(1, baudrate=9600, tx=Pin(17), rx=Pin(16))
        mp3 = DFPlayer(uart)
        mp3.volume(20)
        mp3.play(1)
    """

    def __init__(self, uart, ack=False, do_reset=True, ready_delay_ms=2000):
        """
        Parametres :
            uart            instance machine.UART deja configuree (9600 bauds)
            ack             True pour activer l'acquittement materiel
            do_reset        True pour reinitialiser le module au demarrage
            ready_delay_ms  delai d'attente apres reset (ms)
        """
        self._uart = uart
        self._ack = 1 if ack else 0
        if do_reset:
            self.reset()
            time.sleep_ms(ready_delay_ms)
            self._flush_rx()

    # -- Construction et envoi des trames -----------------------------------

    @staticmethod
    def _checksum(frame):
        s = 0
        for i in range(1, 7):
            s += frame[i]
        cs = (-s) & 0xFFFF
        return (cs >> 8) & 0xFF, cs & 0xFF

    def _build(self, cmd, param=0):
        ph = (param >> 8) & 0xFF
        pl = param & 0xFF
        frame = bytearray(10)
        frame[0] = _START
        frame[1] = _VERSION
        frame[2] = _LENGTH
        frame[3] = cmd
        frame[4] = self._ack
        frame[5] = ph
        frame[6] = pl
        ckh, ckl = self._checksum(frame)
        frame[7] = ckh
        frame[8] = ckl
        frame[9] = _END
        return frame

    def _flush_rx(self):
        while self._uart.any():
            self._uart.read(self._uart.any())

    def _send(self, cmd, param=0, settle_ms=30):
        self._flush_rx()
        self._uart.write(self._build(cmd, param))
        time.sleep_ms(settle_ms)

    def _read_frame(self, timeout_ms=200):
        """Lit une trame complete (10 octets) avec verification du checksum."""
        deadline = time.ticks_add(time.ticks_ms(), timeout_ms)
        buf = bytearray()
        while time.ticks_diff(deadline, time.ticks_ms()) > 0:
            n = self._uart.any()
            if n:
                chunk = self._uart.read(n)
                if chunk:
                    buf.extend(chunk)
                if len(buf) >= 10:
                    break
            else:
                time.sleep_ms(5)
        # Recherche d'une trame valide dans le tampon
        for i in range(0, len(buf) - 9):
            if buf[i] == _START and buf[i + 9] == _END:
                frame = bytes(buf[i:i + 10])
                ckh, ckl = self._checksum(frame)
                if frame[7] == ckh and frame[8] == ckl:
                    return frame
        return None

    def _query(self, cmd, param=0, timeout_ms=300):
        """Envoie une requete et retourne le parametre 16 bits de la reponse."""
        self._flush_rx()
        self._uart.write(self._build(cmd, param))
        frame = self._read_frame(timeout_ms)
        if frame is None:
            raise DFPlayerError("aucune reponse a la requete 0x%02X" % cmd)
        if frame[3] == EVT_ERROR:
            raise DFPlayerError("erreur module 0x%02X" % ((frame[5] << 8) | frame[6]))
        return (frame[5] << 8) | frame[6]

    # -- Commandes de lecture -----------------------------------------------

    def play(self, track=1):
        """Joue la piste numero <track> (1-2999) a la racine de la carte."""
        if not 1 <= track <= 2999:
            raise ValueError("track doit etre entre 1 et 2999")
        self._send(CMD_PLAY_TRACK, track)

    def next(self):
        self._send(CMD_NEXT)

    def previous(self):
        self._send(CMD_PREV)

    def pause(self):
        self._send(CMD_PAUSE)

    def resume(self):
        self._send(CMD_RESUME)

    def start(self):
        """Alias de resume(), demarre la lecture."""
        self._send(CMD_RESUME)

    def stop(self):
        self._send(CMD_STOP)

    def play_folder(self, folder, track):
        """
        Joue le fichier <track> (1-255) du dossier <folder> (1-99).
        Le dossier doit s'appeler 01, 02 ... 99 et contenir des fichiers
        nommes 001.mp3, 002.mp3 ...
        """
        if not 1 <= folder <= 99:
            raise ValueError("folder doit etre entre 1 et 99")
        if not 1 <= track <= 255:
            raise ValueError("track doit etre entre 1 et 255")
        self._send(CMD_PLAY_FOLDER, (folder << 8) | track)

    def play_mp3(self, track):
        """
        Joue 0001.mp3 .. 9999.mp3 dans le dossier nomme 'mp3'.
        """
        if not 1 <= track <= 9999:
            raise ValueError("track doit etre entre 1 et 9999")
        self._send(CMD_PLAY_MP3, track)

    def play_large_folder(self, folder, track):
        """
        Joue dans un dossier 1-15 un fichier 1-3000.
        Le dossier occupe les 4 bits de poids fort du parametre, le fichier
        les 12 bits restants.
        """
        if not 1 <= folder <= 15:
            raise ValueError("folder doit etre entre 1 et 15")
        if not 1 <= track <= 3000:
            raise ValueError("track doit etre entre 1 et 3000")
        param = ((folder & 0x0F) << 12) | (track & 0x0FFF)
        self._send(CMD_PLAY_LARGE_FOLDER, param)

    def insert_advert(self, track):
        """Insere une publicite (fichier 0001-9999 du dossier 'advert')."""
        if not 1 <= track <= 9999:
            raise ValueError("track doit etre entre 1 et 9999")
        self._send(CMD_INSERT_AD, track)

    def stop_advert(self):
        """Arrete la publicite et reprend la lecture interrompue."""
        self._send(CMD_STOP_AD)

    def loop_track(self, track):
        """Joue la piste <track> en boucle."""
        if not 1 <= track <= 2999:
            raise ValueError("track doit etre entre 1 et 2999")
        self._send(CMD_LOOP_TRACK, track)

    def loop_folder(self, folder):
        """Lit en boucle tous les fichiers du dossier 1-99."""
        if not 1 <= folder <= 99:
            raise ValueError("folder doit etre entre 1 et 99")
        self._send(CMD_LOOP_FOLDER, folder)

    def loop_all(self, enable=True):
        """Active ou desactive la lecture en boucle de tous les fichiers."""
        self._send(CMD_REPEAT_ALL, 1 if enable else 0)

    def loop_current(self, enable=True):
        """Active ou desactive la repetition du fichier courant."""
        # Convention DFPlayer : 0 = active, 1 = desactive
        self._send(CMD_LOOP_CURRENT, 0 if enable else 1)

    def random_all(self):
        """Lecture aleatoire de tous les fichiers."""
        self._send(CMD_RANDOM)

    # -- Volume et egaliseur ------------------------------------------------

    def volume(self, level):
        """Regle le volume entre 0 et 30."""
        if not 0 <= level <= 30:
            raise ValueError("level doit etre entre 0 et 30")
        self._send(CMD_SET_VOLUME, level)

    def volume_up(self):
        self._send(CMD_VOL_UP)

    def volume_down(self):
        self._send(CMD_VOL_DOWN)

    def eq(self, mode):
        """Regle l'egaliseur (constantes EQ_*)."""
        if not 0 <= mode <= 5:
            raise ValueError("mode EQ doit etre entre 0 et 5")
        self._send(CMD_SET_EQ, mode)

    # -- Source et alimentation ---------------------------------------------

    def set_source(self, source):
        """Selectionne la source : SOURCE_USB, SOURCE_SD, SOURCE_AUX,
        SOURCE_SLEEP, SOURCE_FLASH."""
        if source not in (SOURCE_USB, SOURCE_SD, SOURCE_AUX,
                          SOURCE_SLEEP, SOURCE_FLASH):
            raise ValueError("source invalide")
        self._send(CMD_SET_SOURCE, source)
        # Le module a besoin d'un peu de temps pour monter le support
        time.sleep_ms(200)

    def standby(self):
        """Met le module en veille."""
        self._send(CMD_STANDBY)

    def wake(self):
        """Sort de veille."""
        self._send(CMD_NORMAL)

    def reset(self):
        """Reinitialise le module (compte ~1.5 a 3 s avant d'etre pret)."""
        self._send(CMD_RESET)

    def dac(self, enable=True):
        """Active ou desactive la sortie DAC."""
        # Convention DFPlayer : 0 = active, 1 = desactive
        self._send(CMD_DAC, 0 if enable else 1)

    def set_dac_gain(self, gain):
        """Regle le gain de l'amplificateur (0-31)."""
        if not 0 <= gain <= 31:
            raise ValueError("gain doit etre entre 0 et 31")
        # PH = 1 (active la fonction), PL = gain
        self._send(CMD_DAC_GAIN, (1 << 8) | gain)

    # -- Requetes -----------------------------------------------------------

    def query_status(self):
        """Retourne l'etat courant : 0=stop, 1=play, 2=pause."""
        return self._query(CMD_QUERY_STATUS)

    def query_volume(self):
        return self._query(CMD_QUERY_VOLUME)

    def query_eq(self):
        return self._query(CMD_QUERY_EQ)

    def query_version(self):
        return self._query(CMD_QUERY_VERSION)

    def query_file_count(self, source=SOURCE_SD):
        cmd = {SOURCE_USB: CMD_QUERY_FILES_USB,
               SOURCE_SD: CMD_QUERY_FILES_SD,
               SOURCE_FLASH: CMD_QUERY_FILES_FLASH}.get(source)
        if cmd is None:
            raise ValueError("source non supportee pour cette requete")
        return self._query(cmd)

    def query_current_track(self, source=SOURCE_SD):
        cmd = {SOURCE_USB: CMD_QUERY_TRACK_USB,
               SOURCE_SD: CMD_QUERY_TRACK_SD,
               SOURCE_FLASH: CMD_QUERY_TRACK_FLASH}.get(source)
        if cmd is None:
            raise ValueError("source non supportee pour cette requete")
        return self._query(cmd)

    def query_files_in_folder(self, folder):
        if not 1 <= folder <= 99:
            raise ValueError("folder doit etre entre 1 et 99")
        return self._query(CMD_QUERY_FILES_FOLDER, folder)

    def query_folder_count(self):
        return self._query(CMD_QUERY_FOLDERS)

    # -- Reception d'evenements asynchrones ---------------------------------

    def poll(self, timeout_ms=0):
        """
        Lit une trame asynchrone si disponible (fin de piste, insertion
        de carte, erreur ...).

        Retourne un tuple (event_code, parameter) ou None si rien.
        """
        if timeout_ms == 0 and not self._uart.any():
            return None
        frame = self._read_frame(timeout_ms if timeout_ms > 0 else 50)
        if frame is None:
            return None
        return frame[3], (frame[5] << 8) | frame[6]