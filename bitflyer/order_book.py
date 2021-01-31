import logging
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

    def __init__(self, enable_qos=True, enable_statistics=True):
        self.bid_order_book = SortedDict()
        self.ask_order_book = SortedDict()
        self.snapshot_received = False
        self._cond_len = 1000
        self._mid_price_cond = deque(maxlen=self._cond_len)
        self._bid_ask_cond = deque(maxlen=self._cond_len)
        self.best_adjusted_bid = None
        self.best_adjusted_ask = None
        self.mid_price = None
        self.qos = 1.0  # 1.0: perfect synchronised stream, <0.9 degraded stream.
        self.ups = NumUpdatesPerSeconds()
        self.enable_qos = enable_qos
        self.enable_statistics = enable_statistics

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
        except IndexError:
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
        except IndexError:
            return None

    def updates_per_second(self):
        return self.ups.rate

    def liquidity_for(self, quantity: float):
        if not self.snapshot_received:
            return 0, 0, 0, 0
        bid_total_value = 0
        bid_total_quantity = 0
        level_price = 0
        for i in range(-1, -len(self.bid_order_book), -1):
            level_price, liquidity = self.bid_order_book.peekitem(i)
            if bid_total_quantity < quantity:
                bid_total_value += level_price * liquidity
                bid_total_quantity += liquidity
            else:
                break
        bid_average_price = int(bid_total_value / bid_total_quantity)
        bid_lowest_price = level_price

        ask_total_value = 0
        ask_total_quantity = 0
        for i in range(len(self.ask_order_book)):
            level_price, liquidity = self.ask_order_book.peekitem(i)
            if ask_total_quantity < quantity:
                ask_total_value += level_price * liquidity
                ask_total_quantity += liquidity
            else:
                break
        ask_average_price = int(ask_total_value / ask_total_quantity)
        ask_highest_price = level_price
        return bid_average_price, ask_average_price, bid_lowest_price, ask_highest_price

    def snapshot_update(self, snapshot):
        if self.enable_statistics:
            self.ups.count()
        self.best_adjusted_bid = None
        self.best_adjusted_ask = None
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
        if self.enable_statistics:
            self.ups.count()
        price = int(price)
        book = self.bid_order_book if is_bid else self.ask_order_book
        book[price] = size

    def book_update(self, update: dict):
        self.best_adjusted_bid = None
        self.best_adjusted_ask = None
        self.mid_price = update['mid_price']
        for bid in update['bids']:
            self._single_book_update(bid['price'], bid['size'], is_bid=True)
        for ask in update['asks']:
            self._single_book_update(ask['price'], ask['size'], is_bid=False)

        if self.enable_qos:
            self._mid_price_cond.append(self.best_bid <= update["mid_price"] <= self.best_ask)
            self._bid_ask_cond.append(self.best_bid <= self.best_ask)

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
        if self.enable_qos and len(self._mid_price_cond) == self._cond_len:
            self.qos = (0.5 * np.mean(self._bid_ask_cond) + 0.5 * np.mean(self._mid_price_cond))


if __name__ == '__main__':
    ob = OrderBook(enable_qos=False, enable_statistics=False)
    ob.snapshot_update('../ob.json')
    # ob.book_update('../update.json')
    print(ob.best_bid, ob.best_ask)
    print(ob.liquidity_for(0.01))
    print(ob.liquidity_for(1))
    print(ob.liquidity_for(3))
    print(ob.liquidity_for(10))
    print(ob.liquidity_for(25))
    print(ob.liquidity_for(60))
    print(ob.liquidity_for(100))
