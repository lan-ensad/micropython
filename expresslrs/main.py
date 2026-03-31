from machine import UART, Pin
from crsf import CRSFParser
import time

# UART sur XIAO ESP32-C3
# ATTENTION : GPIO20/21 sont utilisés par UART0 (REPL via USB)
# Utiliser d'autres pins pour CRSF : RX=GPIO4 (D2), TX=GPIO5 (D3)
# Brancher le TX du récepteur ELRS sur GPIO4 (D2)
RX_PIN = 4
TX_PIN = 5

uart = UART(1, baudrate=420000, tx=Pin(TX_PIN), rx=Pin(RX_PIN),
            bits=8, parity=None, stop=1, timeout=0)

# Ordre CRSF standard : AETR (Aileron/Roll, Elevator/Pitch, Throttle, Rudder/Yaw)
CHANNEL_NAMES = [
    "Roll", "Pitch", "Throttle", "Yaw",
    "Aux1", "Aux2", "Aux3", "Aux4",
    "Aux5", "Aux6", "Aux7", "Aux8",
    "Aux9", "Aux10", "Aux11", "Aux12"
]

THRESHOLD = 5
PRINT_INTERVAL = 100  # ms

parser = CRSFParser()
last_channels = None
link_stats = None
last_print = time.ticks_ms()

print("CRSF receiver demarre - RX sur GPIO{} - Ctrl+C pour arreter".format(RX_PIN))

try:
    while True:
        data = uart.read(64)
        if data:
            result = parser.parse(data)
            if result:
                msg_type, payload = result

                if msg_type == "link_stats":
                    link_stats = payload

                elif msg_type == "channels":
                    now = time.ticks_ms()
                    if time.ticks_diff(now, last_print) >= PRINT_INTERVAL:
                        show = False
                        if last_channels is None:
                            show = True
                        else:
                            for i in range(16):
                                if abs(payload[i] - last_channels[i]) > THRESHOLD:
                                    show = True
                                    break

                        if show:
                            print("\033[2J\033[H")
                            print("CRSF RC Channels")
                            print("-" * 30)
                            for i, val in enumerate(payload):
                                print("{:8s}: {:4d}".format(CHANNEL_NAMES[i], val))
                            print("-" * 30)
                            if link_stats:
                                print("RSSI: {}dBm  LQ: {}%  SNR: {}dB".format(
                                    link_stats["rssi1"], link_stats["lq"], link_stats["snr"]))
                            last_channels = list(payload)

                        last_print = now

        time.sleep_ms(1)

except KeyboardInterrupt:
    uart.deinit()
    print("\nStop.")
