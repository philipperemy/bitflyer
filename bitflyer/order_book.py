import json
import logging
import os
from collections import deque
from time import time

import numpy as np
from sortedcontainers import SortedDict

logger = logging.getLogger(__name__)


class NumUpdatesPerSeconds:

    def __init__(self, max_num_updates=1000):
        self.c = 0
        self.max_num_updates = max_num_updates
        self.timer = None
        self.rate = 0
        self.timer = None

    def count(self):
        if self.c == 0:
            self.timer = time()
        self.c += 1
        if self.c == self.max_num_updates:
            self.rate = self.c / (time() - self.timer)
            self.c = 0


class OrderBook:

    def __init__(self):
        self.bid_order_book = SortedDict()
        self.ask_order_book = SortedDict()
        self.snapshot_received = False
        self.cond_history = 1000
        self.mid_price_cond = deque(maxlen=self.cond_history)
        self.bid_ask_cond = deque(maxlen=self.cond_history)
        self.best_adjusted_bid = None
        self.best_adjusted_ask = None
        self.mid_price = None
        self.qos = 1.0  # 1.0: perfect synchronised stream, <0.9 degraded stream.
        self.ups = NumUpdatesPerSeconds()

    @property
    def best_bid(self):
        if self.best_adjusted_bid is not None:
            return self.best_adjusted_bid
        try:
            i = -1
            while True:
                val = self.bid_order_book.peekitem(i)
                if val[1] != 0:
                    return val[0]
                i -= 1
        except Exception:
            return None

    @property
    def best_ask(self):
        if self.best_adjusted_ask is not None:
            return self.best_adjusted_ask
        try:
            i = 0
            while True:
                val = self.ask_order_book.peekitem(i)
                if val[1] != 0:
                    return val[0]
                i += 1
        except Exception:
            return None

    def updates_per_second(self):
        return self.ups.rate

    def snapshot_update(self, snapshot):
        self.ups.count()
        self.best_adjusted_bid = None
        self.best_adjusted_ask = None

        if isinstance(snapshot, str) and os.path.isfile(snapshot):
            with open(snapshot, 'r') as r:
                snapshot = json.load(r)
        self.mid_price = snapshot['mid_price']
        self.bid_order_book = SortedDict()
        self.ask_order_book = SortedDict()
        for bid in snapshot['bids']:
            self._single_book_update(bid['price'], bid['size'], is_bid=True)
        for ask in snapshot['asks']:
            self._single_book_update(ask['price'], ask['size'], is_bid=False)
        assert self.best_bid <= snapshot['mid_price'] <= self.best_ask
        self.snapshot_received = True

    def _single_book_update(self, price, size, is_bid=True):
        self.ups.count()
        price = int(price)
        book = self.bid_order_book if is_bid else self.ask_order_book
        book[price] = size

    def book_update(self, update):
        self.best_adjusted_bid = None
        self.best_adjusted_ask = None
        if isinstance(update, str) and os.path.isfile(update):
            with open(update, 'r') as r:
                update = json.load(r)
        self.mid_price = update['mid_price']
        for bid in update['bids']:
            self._single_book_update(bid['price'], bid['size'], is_bid=True)
        for ask in update['asks']:
            self._single_book_update(ask['price'], ask['size'], is_bid=False)
        # debug = f'{self.best_bid}, {update["mid_price"]}, {self.best_ask}'
        self.mid_price_cond.append(self.best_bid <= update["mid_price"] <= self.best_ask)
        self.bid_ask_cond.append(self.best_bid <= self.best_ask)
        # It should never happen in practice.
        # But sometimes the messages don't arrive sequentially.
        if self.best_bid >= update["mid_price"]:
            self.best_adjusted_bid = update["mid_price"] - 1
        if update["mid_price"] >= self.best_ask:
            self.best_adjusted_ask = update["mid_price"] + 1
        if self.best_bid >= self.best_ask:
            self.best_adjusted_bid = update["mid_price"] - 1
        if self.best_ask <= self.best_bid:
            self.best_adjusted_ask = update["mid_price"] + 1
        assert self.best_bid < self.best_ask
        assert self.best_bid <= update["mid_price"] <= self.best_ask
        if len(self.mid_price_cond) == self.cond_history:
            self.qos = (0.5 * np.mean(self.bid_ask_cond) + 0.5 * np.mean(self.mid_price_cond))


if __name__ == '__main__':
    ob = OrderBook()
    ob.snapshot_update('../ob.json')
    ob.book_update('../update.json')
