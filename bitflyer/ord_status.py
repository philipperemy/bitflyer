import json
from collections import defaultdict
from queue import Queue

import attr
import iso8601 as iso8601

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
    OPEN = 'open'
    FULLY_FILL = 'full_fill'
    PARTIAL_FILL = 'partial_fill'
    CANCEL = 'cancel'
    EXPIRE = 'expire'
    CANCEL_FAILED = 'cancel_failed'

    def __init__(self, key, secret):
        self.order_status_by_parent_order_id = defaultdict(list)
        self.acceptance_ids = Queue()
        ws = WebSocketIO('https://io.lightstream.bitflyer.com', key, secret)
        ws.start_auth()

        def on_ord_status(messages):
            for message in messages:
                acceptance_id = message['child_order_acceptance_id']
                self.order_status_by_parent_order_id[acceptance_id].append(message)
                self.acceptance_ids.put(acceptance_id)

        for private_channel in ['child_order_events', 'parent_order_events']:
            ws.register_handler(channel=private_channel, handler=on_ord_status)

    def wait_for_new_msg(self):
        return self.acceptance_ids.get()

    def fetch_order_status(self, order_id):
        if order_id not in self.order_status_by_parent_order_id:
            return None
        messages = self.order_status_by_parent_order_id[order_id]
        sorted_messages = sorted(messages, key=lambda tup: iso8601.parse_date(tup['event_date']))
        executed_quantity = 0
        executed_value = 0
        status = None
        order_quantity = None
        outstanding_size = None
        # https://bf-lightning-api.readme.io/docs/realtime-child-order-events
        for message in sorted_messages:
            et = message['event_type']
            if et == 'ORDER':  # new order.
                order_quantity = message['size']
                outstanding_size = order_quantity  # it's a new order.
                status = self.OPEN
            elif et == 'ORDER_FAILED':
                raise OrderFailed(sorted_messages)
            elif et == 'CANCEL':
                status = self.CANCEL
            elif et == 'CANCEL_FAILED':
                status = self.CANCEL_FAILED
            elif et == 'EXECUTION':
                status = self.OPEN
                executed_value += message['size'] * message['price']
                executed_quantity += message['size']
                outstanding_size = message['outstanding_size']
            elif et == 'EXPIRE':
                status = self.EXPIRE
        if float(executed_quantity) > 0:
            status = self.PARTIAL_FILL
        if order_quantity is not None:
            if abs(float(executed_quantity) - float(order_quantity)) < 1e-6:
                status = self.FULLY_FILL
        else:
            print('Could not fetch the order quantity. Bug ahead.')
        avg_price = float(executed_value) / float(executed_quantity) if executed_quantity != 0 else 0
        return OrderStatus(
            order_id=order_id,
            status=status,
            avg_price=avg_price,
            executed_quantity=executed_quantity,
            outstanding_size=outstanding_size
        )
