LS = ADC(Pin(0))
LS.atten(ADC.ATTN_11DB)
RS = ADC(Pin(1))
RS.atten(ADC.ATTN_11DB)
BTN = Pin(2, Pin.IN)

while True:
    msg = f"X:{LS.read()}\tY:{RS.read()}\tB:{BTN.value()}"
    print(msg)
    e.send(peer, msg)
    sleep(0.025) # lantecy above 25ms
