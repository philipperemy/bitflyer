import hmac
import json
import time
from hashlib import sha256
from queue import Queue
from secrets import token_hex
from threading import Thread

import websocket


class PrivateRealtimeAPI:  # For OrderStatus events only.
    def __init__(self, key, secret):
        self.end_point = 'wss://ws.lightstream.bitflyer.com/json-rpc'
        self.private_channels = ['child_order_events', 'parent_order_events']
        self.key = key
        self.secret = secret
        self.JSONRPC_ID_AUTH = 1
        self.message_queue = Queue()
        self.lock = Queue()

    def on_open(self, ws):
        print("Websocket connected")
        if len(self.private_channels) > 0:
            self.auth(ws)

    def on_error(self, ws, error):
        print(f'PrivateRealtimeAPI - {error}.')

    def on_close(self, ws):
        print("Websocket closed")

    def run(self, ws):
        while True:
            ws.run_forever()
            time.sleep(3)

    def wait(self):
        self.lock.get()

    def on_message(self, ws, message):
        messages = json.loads(message)
        if 'id' in messages and messages['id'] == self.JSONRPC_ID_AUTH:
            if 'error' in messages:
                print('auth error: {}'.format(messages["error"]))
            elif 'result' in messages and messages['result']:
                print('auth success.')
                params = [{'method': 'subscribe', 'params': {'channel': c}}
                          for c in self.private_channels]
                ws.send(json.dumps(params))
                time.sleep(5)
                self.lock.put('READY')
        if 'method' not in messages or messages['method'] != 'channelMessage':
            return
        self.message_queue.put(messages['params']['message'])

    def auth(self, ws):
        now = int(time.time())
        nonce = token_hex(16)
        sign = hmac.new(self.secret.encode(
            'utf-8'), ''.join([str(now), nonce]).encode('utf-8'), sha256).hexdigest()
        params = {'method': 'auth', 'params': {
            'api_key': self.key, 'timestamp': now,
            'nonce': nonce, 'signature': sign
        }, 'id': self.JSONRPC_ID_AUTH}
        ws.send(json.dumps(params))

    def start_and_wait_for_stream(self):
        ws = websocket.WebSocketApp(self.end_point,
                                    on_open=self.on_open,
                                    on_message=self.on_message,
                                    on_error=self.on_error,
                                    on_close=self.on_close)
        thread = Thread(target=self.run, args=(ws,))
        thread.start()
        self.wait()
