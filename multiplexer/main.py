from machine import Pin, ADC
import time

# Broches de selection du canal (S0..S3)
S0 = Pin(1, Pin.OUT)
S1 = Pin(2, Pin.OUT)
S2 = Pin(3, Pin.OUT)
S3 = Pin(4, Pin.OUT)

select_pins = (S0, S1, S2, S3)

# Broche commune SIG du multiplexeur, cote MCU en entree ADC
sig = ADC(Pin(0))
sig.atten(ADC.ATTN_11DB)      # plage 0-3.3 V (ESP32)
sig.width(ADC.WIDTH_12BIT)    # valeurs 0-4095


def select_channel(ch):
    """Selectionne un canal entre 0 et 15."""
    if not 0 <= ch <= 15:
        raise ValueError("canal hors plage 0-15")
    for i, pin in enumerate(select_pins):
        pin.value((ch >> i) & 1)
    time.sleep_us(5)  # petit delai de stabilisation


def read_channel(ch):
    """Selectionne le canal et renvoie la lecture ADC brute."""
    select_channel(ch)
    return sig.read()


# Boucle de demonstration : lecture des 16 canaux
while True:
    for ch in range(16):
        valeur = read_channel(ch)
        tension = valeur * 3.3 / 4095
        print("C{:02d} : {:4d}  ({:.2f} V)".format(ch, valeur, tension))
    print("-" * 30)
    time.sleep(1)