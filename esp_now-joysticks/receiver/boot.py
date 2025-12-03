import network
import espnow
from time import sleep
from machine import Pin, I2C
import ssd1306

i2c = I2C(sda=Pin(22), scl=Pin(23))
display = ssd1306.SSD1306_I2C(128, 64, i2c)

sta = network.WLAN(network.STA_IF)
sta.active(True)

e = espnow.ESPNow()
e.active(True)

print(sta.config('mac'))
display.text_wrap(f"mac address : {sta.config('mac')}", 0, 0)
display.show()
