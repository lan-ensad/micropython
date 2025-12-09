from machine import Pin, TouchPad
import time

touch = TouchPad(Pin(1))
led = Pin(21, Pin.OUT)

# non-blocking detection 
last_state = False
last_check = time.ticks_ms()
debounce_ms = 50

# Calibrating
print("Calibration...")
baseline = 0
for _ in range(10):
    baseline += touch.read()
baseline = baseline // 10

# Threshold
threshold = baseline * 1.15 #value to ajust from hardware configuration
print(f"Baseline: {baseline}, Seuil: {threshold}")


def on_touch():
    print("Touch detecte!")
    led.value(not led.value())

while True:
    now = time.ticks_ms()
    
    # Check
    if time.ticks_diff(now, last_check) >= debounce_ms:
        last_check = now
        
        value = touch.read()
        current_state = value > threshold
        
        # Raise detect
        if current_state and not last_state:
            on_touch()
        
        last_state = current_state
