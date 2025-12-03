from machine import Pin, ADC
from time import sleep
import network
import espnow

sta = network.WLAN(network.STA_IF)
sta.active(True)

e = espnow.ESPNow()
e.active(True)

peer = b'\xe4\xb0cAk@' #Replace macaddress
e.add_peer(peer)
