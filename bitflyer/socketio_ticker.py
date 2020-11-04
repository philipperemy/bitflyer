# coding: utf-8
import hmac
import time
from hashlib import sha256
from secrets import token_hex

import socketio

from bitflyer.order_book import OrderBook

KEY = ''
SECRET = ''


class bFwebsocket(object):
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

    def on_auth(self, recept_data):
        print('Auth process done')
        self._auth_completed = True

    def regist_handler(self, channel, handler):
        self._sio.on(channel, handler)
        self._sio.emit('subscribe', channel)


class SocketIOFastTickerAPI:

    def __init__(self):
        self.order_book = OrderBook()
        self.bbo = None, None
        self.updater = 'TICKER'

        def on_order_book_snapshot(message):
            self.order_book.snapshot_update(message)
            self.bbo = self.order_book.best_bid, self.order_book.best_ask
            self.updater = 'SNAPSHOT'

        def on_order_book(message):
            if self.order_book.snapshot_received:
                self.order_book.book_update(message)
                self.bbo = self.order_book.best_bid, self.order_book.best_ask
                self.updater = 'OB'

        def on_ticker(message):
            self.bbo = message['best_bid'], message['best_ask']
            self.updater = 'TICKER'

        ws = bFwebsocket('https://io.lightstream.bitflyer.com', KEY, SECRET)
        ws.start_auth()

        ws.regist_handler(
            channel='lightning_ticker_FX_BTC_JPY',
            handler=on_ticker)

        ws.regist_handler(
            channel='lightning_board_snapshot_FX_BTC_JPY',
            handler=on_order_book_snapshot)

        ws.regist_handler(
            channel='lightning_board_FX_BTC_JPY',
            handler=on_order_book)

        while self.bbo == (None, None):
            time.sleep(0.001)

    def get_bbo(self):
        return self.bbo
