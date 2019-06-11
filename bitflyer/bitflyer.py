import json
import threading
import time
from datetime import datetime

import websocket


class BitflyerRealtimeAPI:

    def __init__(self,
                 channel='lightning_ticker_FX_BTC_JPY',
                 debug=False):
        self._channel = channel
        self._url = 'wss://ws.lightstream.bitflyer.com/json-rpc'
        self._channel = channel
        self._debug = debug
        self._ws = websocket.WebSocketApp(self._url,
                                          header=None,
                                          on_open=self._on_open,
                                          on_message=self._on_message,
                                          on_error=self._on_error,
                                          on_close=self._on_close)
        self._ticker = None
        self._best_bid = None
        self._best_ask = None
        self._best_bid_size = None
        self._best_ask_size = None
        self._thread = threading.Thread(target=self._run)

    def get_ticker(self):
        return self._ticker

    def get_best_bid(self):
        return self._best_bid

    def get_best_ask(self):
        return self._best_ask

    def get_best_bid_size(self):
        return self._best_bid_size

    def get_best_ask_size(self):
        return self._best_ask_size

    def start(self):
        if self._debug:
            print(f'Connecting...')
        self._thread.start()
        while self._ticker is None:
            time.sleep(0.01)
        if self._debug:
            print('Connected... OK')

    def _run(self):
        self._ws.run_forever()

    def _on_message(self, ws, message):
        j = json.loads(message)
        j['jst_time'] = str(datetime.now())
        m = j['params']['message']
        self._best_bid = m['best_bid']
        self._best_bid_size = m['best_bid_size']
        self._best_ask = m['best_ask']
        self._best_ask_size = m['best_ask_size']
        self._ticker = j

    def _on_error(self, ws, error):
        if self._debug:
            print(error)

    def _on_close(self, ws):
        if self._debug:
            print('disconnected streaming server.')

    def _on_open(self, ws):
        if self._debug:
            print('connected streaming server.')
        output_json = json.dumps(
            {'method': 'subscribe',
             'params': {'channel': self._channel}
             }
        )
        ws.send(output_json)
