# ExpressLRS CRSF - Fonctionnalités à implémenter

## Statut actuel

- [x] Canaux RC (16 channels, type `0x16`)
- [x] Link Statistics (RSSI, LQ, SNR, type `0x14`)

---

## 1. Failsafe - Détection perte de signal

**Priorité : haute**

Détecter la perte de liaison radio et mettre les actionneurs en sécurité.

### Principe
- Surveiller `lq` (Link Quality) dans les link stats
- Si `lq == 0` pendant plus de X ms : failsafe activé
- Si aucune trame RC reçue depuis X ms : failsafe timeout
- Timeout recommandé : 250-500ms (configurable)

### Comportement failsafe
- Couper throttle (channel 2 → 1000)
- Centrer roll/pitch/yaw (→ 1500)
- Aux channels : valeurs prédéfinies par l'utilisateur
- Callback optionnel pour actions custom (couper relais, sirène, etc.)

### Implémentation
```python
# Dans CRSFParser
last_rc_time = time.ticks_ms()
FAILSAFE_TIMEOUT = 500  # ms

def is_failsafe(self):
    return time.ticks_diff(time.ticks_ms(), self.last_rc_time) > FAILSAFE_TIMEOUT
```

### Trame CRSF concernée
Pas de trame spécifique. C'est l'absence de trame `0x16` ou un `lq == 0` dans `0x14` qui déclenche le failsafe.

---

## 2. Telemetry Batterie (TX vers radio)

**Priorité : haute**

Envoyer la tension/courant batterie vers la radiocommande pour affichage en temps réel.

### Trame CRSF
- Type : `0x08` (Battery Sensor)
- Direction : ESP32 → récepteur ELRS → radio TX
- Payload : 8 octets

### Format payload
| Offset | Taille | Contenu | Unité |
|--------|--------|---------|-------|
| 0-1 | 2 octets | Tension | 0.1V (big-endian) |
| 2-3 | 2 octets | Courant | 0.1A (big-endian) |
| 4-6 | 3 octets | Capacité utilisée | mAh (big-endian) |
| 7 | 1 octet | Pourcentage restant | % |

### Implémentation
```python
def build_battery_frame(voltage_v, current_a, capacity_mah, percent):
    payload = bytearray(8)
    v = int(voltage_v * 10)
    a = int(current_a * 10)
    payload[0] = (v >> 8) & 0xFF
    payload[1] = v & 0xFF
    payload[2] = (a >> 8) & 0xFF
    payload[3] = a & 0xFF
    payload[4] = (capacity_mah >> 16) & 0xFF
    payload[5] = (capacity_mah >> 8) & 0xFF
    payload[6] = capacity_mah & 0xFF
    payload[7] = percent
    return build_crsf_frame(0x08, payload)

def build_crsf_frame(frame_type, payload):
    length = len(payload) + 2  # type + payload + crc
    frame = bytearray([0xC8, length, frame_type]) + payload
    frame.append(crc8_dvb_s2(frame[2:]))
    return frame
```

### Matériel nécessaire
- ADC pour lire la tension batterie (diviseur de tension si > 3.3V)
- Optionnel : capteur de courant (INA219, ACS712)
- Le pin TX (GPIO5/D3) doit être connecté au RX du récepteur ELRS

### Note
La telemetry nécessite que le TX du ESP32 soit connecté au RX du récepteur. Le câblage passe de 2 fils (RX + GND) à 3 fils (RX + TX + GND).

---

## 3. Flight Mode - Texte custom sur la radio

**Priorité : moyenne**

Afficher un texte d'état sur l'écran de la radiocommande (max 15 caractères).

### Trame CRSF
- Type : `0x21` (Flight Mode)
- Payload : chaîne de caractères terminée par `\0`
- Max : 15 caractères + null

### Implémentation
```python
def build_flight_mode_frame(text):
    text = text[:15]  # max 15 chars
    payload = bytearray(text.encode()) + bytearray([0x00])
    return build_crsf_frame(0x21, payload)
```

### Exemples d'utilisation
```python
# Afficher l'état sur la radio
uart.write(build_flight_mode_frame("ARMED"))
uart.write(build_flight_mode_frame("AUTO"))
uart.write(build_flight_mode_frame("LOW BATT"))
uart.write(build_flight_mode_frame("GPS LOCK"))
```

### Note
Nécessite la connexion TX (comme la telemetry batterie). Très utile pour le debug ou indiquer l'état d'une machine à états.

---

## 4. GPS - Envoi de position vers la radio

**Priorité : moyenne**

Envoyer des coordonnées GPS vers la radiocommande pour affichage/enregistrement.

### Trame CRSF
- Type : `0x02` (GPS)
- Payload : 15 octets

### Format payload
| Offset | Taille | Contenu | Unité |
|--------|--------|---------|-------|
| 0-3 | 4 octets | Latitude | degré / 1e7 (signé, big-endian) |
| 4-7 | 4 octets | Longitude | degré / 1e7 (signé, big-endian) |
| 8-9 | 2 octets | Vitesse sol | km/h * 10 (big-endian) |
| 10-11 | 2 octets | Cap | degré * 100 (big-endian) |
| 12-13 | 2 octets | Altitude | mètres + 1000 (big-endian) |
| 14 | 1 octet | Nb satellites | — |

### Implémentation
```python
import struct

def build_gps_frame(lat, lon, speed_kmh, heading_deg, alt_m, sats):
    payload = struct.pack('>iiHHHB',
        int(lat * 1e7),
        int(lon * 1e7),
        int(speed_kmh * 10),
        int(heading_deg * 100),
        int(alt_m + 1000),
        sats
    )
    return build_crsf_frame(0x02, payload)
```

### Matériel nécessaire
- Module GPS UART (NEO-6M, BN-220, etc.)
- Second UART pour le GPS ou parsing NMEA en soft serial

---

## 5. Attitude - Orientation IMU

**Priorité : basse**

Envoyer pitch/roll/yaw d'un IMU vers la radio.

### Trame CRSF
- Type : `0x1E` (Attitude)
- Payload : 6 octets

### Format payload
| Offset | Taille | Contenu | Unité |
|--------|--------|---------|-------|
| 0-1 | 2 octets | Pitch | radians * 10000 (signé, big-endian) |
| 2-3 | 2 octets | Roll | radians * 10000 (signé, big-endian) |
| 4-5 | 2 octets | Yaw | radians * 10000 (signé, big-endian) |

### Implémentation
```python
import math, struct

def build_attitude_frame(pitch_deg, roll_deg, yaw_deg):
    to_rad10k = lambda d: int(math.radians(d) * 10000)
    payload = struct.pack('>hhh',
        to_rad10k(pitch_deg),
        to_rad10k(roll_deg),
        to_rad10k(yaw_deg)
    )
    return build_crsf_frame(0x1E, payload)
```

### Matériel nécessaire
- IMU I2C (MPU6050, BNO055, ICM20948)
- Filtre complémentaire ou Madgwick pour fusionner accéléromètre + gyroscope

---

## 6. Device Info - Identification sur le bus

**Priorité : basse**

Permet au ESP32 de s'identifier comme un périphérique sur le bus CRSF. Utile si on veut apparaître dans la liste des devices dans le Lua script ELRS.

### Trame CRSF
- Type : `0x29` (Device Info)
- Payload : nom du device (string null-terminated) + infos hardware

### Note
Principalement utile pour le debug ou l'intégration poussée avec l'écosystème ELRS.

---

## Câblage récapitulatif

### Actuel (RX seulement - channels + link stats)
| Récepteur ELRS | XIAO ESP32-C3 |
|---|---|
| TX | GPIO4 (D2) |
| GND | GND |
| 5V | 3.3V |

### Avec telemetry (RX + TX)
| Récepteur ELRS | XIAO ESP32-C3 |
|---|---|
| TX | GPIO4 (D2) |
| RX | GPIO5 (D3) |
| GND | GND |
| 5V | 3.3V |

---

## Ordre d'implémentation recommandé

1. **Failsafe** - sécurité, indispensable pour piloter des actionneurs
2. **Telemetry batterie** - très utile en pratique, simple à implémenter
3. **Flight Mode texte** - debug facile, quelques lignes de code
4. **GPS** - nécessite du matériel supplémentaire
5. **Attitude** - nécessite IMU + filtre, plus complexe
