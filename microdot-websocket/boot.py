import network, utime

# =====	STA MODE =====
# SSID = "domo"
# SSI_PASSWORD = "th1Sp4((!"
# 
# def do_connect():
#     import network
#     sta_if = network.WLAN(network.STA_IF)
#     if not sta_if.isconnected():
#         print('connecting to network...')
#         sta_if.active(True)
#         sta_if.connect(SSID, SSI_PASSWORD)
#         while not sta_if.isconnected():
#             pass
#     print('Connected! Network config:', sta_if.ifconfig())
#     
# print("Connecting to your wifi...")
# do_connect()

# ===== AP MODE =====
AP_SSID = "ESP32-AP"  # Name of the Access Point
AP_PASSWORD = "12345678"  # Password for the Access Point

ap_if = network.WLAN(network.AP_IF)
ap_if.active(True)
ap_if.config(essid=AP_SSID, password=AP_PASSWORD)
print('Access Point started. Config:', ap_if.ifconfig())
