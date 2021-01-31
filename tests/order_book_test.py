import json
import unittest

from bitflyer.order_book import OrderBook


class OrderBookTest(unittest.TestCase):

    def test_1(self):
        ob = OrderBook(enable_qos=False, enable_statistics=False)
        with open('../ob.json', 'r') as r:
            snapshot = json.load(r)
        ob.snapshot_update(snapshot)
        self.assertEqual(955328, ob.best_bid)
        self.assertEqual(955406, ob.best_ask)
        # 955328 955406

        ob.book_update({
            "mid_price": 955360,
            "bids": [{"price": 955330.0, "size": 1.210}],
            "asks": [{"price": 955398.0, "size": 1.621}]
        })

        self.assertEqual(955330, ob.best_bid)
        self.assertEqual(955398, ob.best_ask)

        # wrong mid.
        ob.book_update({
            "mid_price": 1_955_360,
            "bids": [{"price": 955330.0, "size": 1.210}],
            "asks": [{"price": 955398.0, "size": 1.621}]
        })
        self.assertEqual(955330, ob.best_bid)
        self.assertEqual(1_955_361, ob.best_ask)

        ob.book_update({
            "mid_price": 955360,
            "bids": [{"price": 955330.0, "size": 1.210}],
            "asks": [{"price": 955398.0, "size": 1.621}]
        })

        self.assertEqual(955330, ob.best_bid)
        self.assertEqual(955398, ob.best_ask)

        ob.snapshot_update(snapshot)
        self.assertEqual(955328, ob.best_bid)
        self.assertEqual(955406, ob.best_ask)

        ob.book_update({
            "mid_price": 955360,
            "bids": [],
            "asks": [{"price": 955398.0, "size": 1.621}]
        })
        self.assertEqual(955328, ob.best_bid)
        self.assertEqual(955398, ob.best_ask)

        # clear bid.
        #     {
        #       "price": 955328.0,
        #       "size": 0.04
        #     },
        #     {
        #       "price": 955324.0,
        #       "size": 0.02
        #     },
        ob.book_update({
            "mid_price": 955360,
            "bids": [{"price": 955328.0, "size": 0}],
            "asks": []
        })
        self.assertEqual(955324, ob.best_bid)
        self.assertEqual(955398, ob.best_ask)

        ob.book_update({
            "mid_price": 955360,
            "bids": [{"price": 955328.0, "size": 0}],
            "asks": [{"price": 955398.0, "size": 0}]
        })
        self.assertEqual(955324, ob.best_bid)
        self.assertEqual(955406, ob.best_ask)
