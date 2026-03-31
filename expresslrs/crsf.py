SYNC_BYTE = 0xC8
TYPE_RC_CHANNELS = 0x16
MAX_FRAME = 64
BUFFER_MAX = 128


def crc8_dvb_s2(data):
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0xD5) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc


CRSF_MIN = 172
CRSF_MAX = 1811
RC_MIN = 1000
RC_MAX = 2000


def decode_channels(payload):
    channels = []
    for i in range(16):
        byte_idx = (i * 11) // 8
        bit_off = (i * 11) % 8
        val = (payload[byte_idx] | (payload[byte_idx + 1] << 8)) >> bit_off
        val &= 0x7FF
        # Scaling CRSF 172-1811 → 1000-2000
        rc = RC_MIN + (val - CRSF_MIN) * (RC_MAX - RC_MIN) // (CRSF_MAX - CRSF_MIN)
        if rc < RC_MIN:
            rc = RC_MIN
        elif rc > RC_MAX:
            rc = RC_MAX
        channels.append(rc)
    return channels


class CRSFParser:
    def __init__(self):
        self.buf = bytearray()

    def parse(self, new_data):
        self.buf.extend(new_data)

        # Limite la taille du buffer
        if len(self.buf) > BUFFER_MAX:
            self.buf = self.buf[-MAX_FRAME:]

        while True:
            # Chercher le sync byte
            sync_pos = -1
            for i in range(len(self.buf)):
                if self.buf[i] == SYNC_BYTE:
                    sync_pos = i
                    break

            if sync_pos < 0:
                self.buf = bytearray()
                return None

            # Supprimer les octets avant le sync
            if sync_pos > 0:
                self.buf = self.buf[sync_pos:]

            # Il faut au moins 2 octets (sync + length)
            if len(self.buf) < 2:
                return None

            length = self.buf[1]

            # Valider la longueur
            if length < 2 or length > 62:
                self.buf = self.buf[1:]
                continue

            frame_size = 2 + length  # sync + length + (type + payload + crc)

            # Attendre la trame complète
            if len(self.buf) < frame_size:
                return None

            # Extraire la trame
            frame_type = self.buf[2]
            crc_idx = frame_size - 1
            expected_crc = self.buf[crc_idx]
            actual_crc = crc8_dvb_s2(self.buf[2:crc_idx])

            if actual_crc != expected_crc:
                # CRC invalide, sauter ce sync byte
                self.buf = self.buf[1:]
                continue

            # Trame valide - extraire payload
            payload = self.buf[3:crc_idx]
            self.buf = self.buf[frame_size:]

            if frame_type == TYPE_RC_CHANNELS and len(payload) >= 22:
                return decode_channels(payload)

            # Trame valide mais pas RC channels, continuer à chercher
            continue

        return None
