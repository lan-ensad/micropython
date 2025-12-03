from machine import Pin
from time import sleep
import network
import espnow

sta = network.WLAN(network.STA_IF)
sta.active(True)

e = espnow.ESPNow()
e.active(True)

peer = b'\xe4\xb0cAk@' #Replace macaddress
e.add_peer(peer)

btn = Pin(18, Pin.IN, Pin.PULL_UP)
def send_msg(pin):
    e.send(peer, "hello world")
    print('message send')
    
btn.irq(trigger=Pin.IRQ_FALLING, handler=send_msg)