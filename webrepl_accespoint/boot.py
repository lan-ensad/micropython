# ===== STEP 1 =====
# #Configure webrepl_cfg.py
# import webrepl_setup

# ===== STEP 2 =====
# #launch STA OR AP
import time
import network
import webrepl
# ------ STA ------
def do_connect(ssid, pwd):
    import network
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print('connecting to network...')
        sta_if.active(True)
        sta_if.connect(ssid, pwd)
        while not sta_if.isconnected():
            pass
    print('network config:', sta_if.ifconfig())
 
# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
do_connect('domo', 'th1Sp4((!')
webrepl.start()

# ------ AP ------
# webrepl.start()
# ssid = 'TRY'
# password = 'try-pass'
# ap = network.WLAN(network.AP_IF);
# ap.active(True);
# ap.config(essid=ssid,authmode=network.AUTH_WPA_WPA2_PSK, password=password)
# print(ap.ifconfig())


# ------ CONNECT ------
#ws://<IP>:8266
