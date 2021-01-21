import json
from queue import Queue

import attr

from bitflyer.socketio import WebSocketIO


class OrderFailed(Exception):
    pass


class CancelFailed(Exception):
    pass


@attr.s
class OrderStatus:
    order_id = attr.ib(type=str)
    status = attr.ib(type=str)
    avg_price = attr.ib(type=float)
    executed_quantity = attr.ib(type=float)
    outstanding_size = attr.ib(type=float)

    def __str__(self):
        if self.outstanding_size is not None:
            os = round(self.outstanding_size * 100000) / 100000
        else:
            os = 'N/A'
        return f'Order status (id={self.order_id}, ' \
               f'status={self.status}, ' \
               f'avg_px={round(self.avg_price * 100000) / 100000}, ' \
               f'execQty={round(self.executed_quantity * 100000) / 100000}, ' \
               f'outstandingSize={os})'

    def json(self):
        return json.dumps({
            'order_id': self.order_id,
            'status': self.status,
            'avg_price': self.avg_price,
            'executed_quantity': self.executed_quantity,
            'outstanding_size': self.outstanding_size
        })


class OrderEventsAPI:

    def __init__(self, key, secret):
        self.message_queue = Queue()
        ws = WebSocketIO('https://io.lightstream.bitflyer.com', key, secret)
        ws.start_auth()

        def on_ord_status(messages):
            for message in messages:
                self.message_queue.put(message)

        for private_channel in ['child_order_events', 'parent_order_events']:
            ws.register_handler(channel=private_channel, handler=on_ord_status)
