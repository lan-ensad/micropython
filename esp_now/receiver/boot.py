import network
import espnow

sta = network.WLAN(network.STA_IF)
sta.active(True)

e = espnow.ESPNow()
e.active(True)

while True:
    host, msg = e.recv()
    if msg:
        print(f"De {host}: {msg}")