def parse_msg(msg):
    if isinstance(msg, bytes):
        msg = msg.decode('utf-8')
    return {k: int(v) if v.lstrip('-').isdigit() else v 
            for k, v in (p.split(':') for p in msg.split('\t'))}

while True:
    host, msg = e.recv()
    if msg:
        display.fill(0)
        data = parse_msg(msg)
        y = 0
        for key, value in data.items():
            display.text(f"{key}: {value}", 0, y)
            y += 8
        display.show()
        print(f"{data}")
