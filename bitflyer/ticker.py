# coding: utf-8
import time
from logging import getLogger

from bitflyer.order_book import OrderBook
from bitflyer.socketio import WebSocketIO

logger = getLogger(__name__)

KEY = ''
SECRET = ''


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

        ws = WebSocketIO('https://io.lightstream.bitflyer.com', KEY, SECRET)
        ws.start_auth()

        ws.register_handler(
            channel='lightning_ticker_FX_BTC_JPY',
            handler=on_ticker)

        ws.register_handler(
            channel='lightning_board_snapshot_FX_BTC_JPY',
            handler=on_order_book_snapshot)

        ws.register_handler(
            channel='lightning_board_FX_BTC_JPY',
            handler=on_order_book)

        while self.bbo == (None, None):
            time.sleep(0.001)

    def get_bbo(self):
        return self.bbo
