from microdot import Microdot, send_file
from microdot_websocket import with_websocket

app = Microdot()

@app.route('/')
async def index(request):
    return send_file('index.html')

@app.route('/echo')

@with_websocket
async def echo(request, ws):
    while True:
        data = await ws.receive()
        await ws.send(data)
        # print(f'{type(data)} : {data}')
        print(data)

app.run(host='0.0.0.0', port='5000')
