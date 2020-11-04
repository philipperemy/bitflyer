import json
from logging import getLogger
from queue import Queue
from threading import Thread
from time import sleep

import websocket

from bitflyer.order_book import OrderBook

logger = getLogger(__name__)


class FastTickerAPI:

    def __init__(self, log_on_bbo_update=True):
        self.channel_snapshot = 'lightning_board_snapshot_FX_BTC_JPY'
        self.channel_updates = 'lightning_board_FX_BTC_JPY'
        self.queue = Queue()

        self.snapshot = _RealtimeAPI(channel=self.channel_snapshot, message_queue=self.queue)
        self.snapshot.run_no_wait()

        self.updates = _RealtimeAPI(channel=self.channel_updates, message_queue=self.queue)
        self.updates.run_no_wait()

        self.order_book = OrderBook()

        self.thread = Thread(target=self._track_ticker)
        self.thread.start()
        self.bbo = None, None
        self.log_on_bbo_update = log_on_bbo_update
        # wait to receive our first BBO.
        while self.bbo == (None, None):
            sleep(0.001)

    def _track_ticker(self):
        while True:
            message = self.queue.get()
            channel = message['params']['channel']
            if channel == 'lightning_board_snapshot_FX_BTC_JPY':
                self.order_book.snapshot_update(message['params']['message'])
            elif channel == 'lightning_board_FX_BTC_JPY':
                if self.order_book.snapshot_received:
                    self.order_book.book_update(message['params']['message'])
                    # mid is in in range.
            if self.order_book.best_bid is not None:
                new_bbo = self.order_book.best_bid, self.order_book.best_ask
                if new_bbo != self.bbo:
                    self.bbo = new_bbo
                    if self.log_on_bbo_update:
                        bid, ask = self.bbo
                        spread = ask - bid
                        r = int(self.order_book.updates_per_second())
                        logger.info(f'BID: {int(bid)}, '
                                    f'ASK: {int(ask)}, '
                                    f'BID/ASK SPR: {str(int(spread)).zfill(4)}, '
                                    f'STREAM QUALITY: {self.order_book.qos:.3f}, '
                                    f'RATE: {str(r).zfill(5)} updates/sec.')

    def get_bbo(self):
        return self.bbo


class _RealtimeAPI:

    def __init__(self, channel, message_queue: Queue):
        self.url = 'wss://ws.lightstream.bitflyer.com/json-rpc'
        self.channel = channel
        self.message_queue = message_queue
        self.ws = websocket.WebSocketApp(self.url, header=None, on_open=self.on_open,
                                         on_message=self.on_message, on_error=self.on_error,
                                         on_close=self.on_close)
        self.thread = Thread(name=channel, target=self.run)

    def run_no_wait(self):
        self.thread.start()

    def join(self):
        self.thread.join()

    def run(self):
        self.ws.run_forever()
        logger.debug('Web Socket process ended.')

    # when we get message
    def on_message(self, ws, message):
        j = json.loads(message)
        logger.debug(j)
        self.message_queue.put(j)

    # when error occurs
    def on_error(self, ws, error):
        logger.error(error)
        '''Called on fatal websocket errors. We exit on these.'''
        print('_RealtimeAPI', self.channel)
        print('Trying to reconnect...')
        self.ws.run_forever()
        raise websocket.WebSocketException(error)

    # when websocket closed.
    def on_close(self, ws):
        logger.debug('disconnected streaming server')

    # when websocket opened.
    def on_open(self, ws):
        logger.debug('connected streaming server')
        output_json = json.dumps(
            {
                'method': 'subscribe',
                'params': {
                    'channel': self.channel
                }
            }
        )
        ws.send(output_json)
