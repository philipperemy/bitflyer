import hmac
import json
import time
from hashlib import sha256
from secrets import token_hex
from threading import Thread

import websocket


class ClientRPC:
    def __init__(self, key, secret):  # only compatible with 0.47.0
        self.end_point = 'wss://ws.lightstream.bitflyer.com/json-rpc'
        self.private_channels = []
        self.key = key
        self.secret = secret
        self.JSON_RPC_ID_AUTH = 1
        self.handler = None
        self.ready = False

    def register_channels(self, private_channels):
        self.private_channels = private_channels

    def register_handler(self, handler):
        self.handler = handler

    def on_open(self, ws):
        print("Websocket connected.")
        if len(self.private_channels) > 0:
            self.auth(ws)

    def on_error(self, ws, error):
        print(f'Websocket error: {error}.')

    def on_close(self, ws):
        print("Websocket closed")

    def on_message(self, ws, message):
        messages = json.loads(message)
        if 'id' in messages and messages['id'] == self.JSON_RPC_ID_AUTH:
            if 'error' in messages:
                print('auth error: {}'.format(messages["error"]))
            elif 'result' in messages and messages['result']:
                print('auth success.')
                params = [{'method': 'subscribe', 'params': {'channel': c}}
                          for c in self.private_channels]
                ws.send(json.dumps(params))
                time.sleep(5)
                self.ready = True
        if 'method' not in messages or messages['method'] != 'channelMessage':
            return
        self.handler(messages['params']['message'])

    def auth(self, ws):
        now = int(time.time())
        nonce = token_hex(16)
        sign = hmac.new(self.secret.encode(
            'utf-8'), ''.join([str(now), nonce]).encode('utf-8'), sha256).hexdigest()
        params = {'method': 'auth', 'params': {
            'api_key': self.key, 'timestamp': now,
            'nonce': nonce, 'signature': sign
        }, 'id': self.JSON_RPC_ID_AUTH}
        ws.send(json.dumps(params))

    def start_and_wait_for_stream(self):
        ws = websocket.WebSocketApp(
            self.end_point,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )

        def wrap_run():
            while True:
                ws.run_forever()

        Thread(target=wrap_run).start()
        while not self.ready:
            time.sleep(0.01)
