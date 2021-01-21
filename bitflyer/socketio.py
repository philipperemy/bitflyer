import hmac
import time
from hashlib import sha256
from secrets import token_hex

import socketio


class WebSocketIO(object):
    def __init__(self, end_point, key, secret):
        self._connected = False
        self._auth_completed = False
        self._end_point = end_point
        self._key = key
        self._secret = secret

        self._sio = socketio.Client()
        self._sio.on('connect', self.on_connect)
        self._sio.connect(self._end_point, transports=['websocket'])
        while not self._connected:
            time.sleep(1)

    def on_connect(self):
        print('SocketIO connected')
        self._connected = True

    def start_auth(self):
        now = int(time.time())
        nonce = token_hex(16)
        sign = hmac.new(self._secret.encode('utf-8'),
                        ''.join([str(now), nonce]).encode('utf-8'),
                        sha256).hexdigest()
        params = {'api_key': self._key, 'timestamp': now,
                  'nonce': nonce, 'signature': sign}
        self._sio.emit('auth', params, callback=self.on_auth)
        print('Auth process started')
        while not self._auth_completed:
            time.sleep(1)

    def on_auth(self, data):
        print('Auth process done')
        self._auth_completed = True

    def register_handler(self, channel, handler):
        self._sio.on(channel, handler)
        self._sio.emit('subscribe', channel)
