import hmac
import json
import logging
import threading
import time
from collections import defaultdict
from datetime import datetime
from hashlib import sha256
from queue import Queue
from secrets import token_hex
from threading import Thread

import attr
import iso8601 as iso8601
import pybitflyer
import websocket


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


logger = logging.getLogger(__name__)


class OrderEventsAPI:
    OPEN = 'open'
    FULLY_FILL = 'full_fill'
    PARTIAL_FILL = 'partial_fill'
    CANCEL = 'cancel'
    EXPIRE = 'expire'
    CANCEL_FAILED = 'cancel_failed'

    def __init__(self, key, secret):
        self.private = PrivateRealtimeAPI(key, secret)
        self.private.start_and_wait_for_stream()
        self.order_status_by_parent_order_id = defaultdict(list)
        self.lock = Queue()
        self.thread = Thread(target=self.run_forever)
        self.thread.start()
        logger.debug('OrderStatusBook - feed ready.')

    def wait_for_new_msg(self):
        return self.lock.get()

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
            logger.warning('Could not fetch the order quantity. Bug ahead.')
        avg_price = float(executed_value) / float(executed_quantity) if executed_quantity != 0 else 0
        return OrderStatus(
            order_id=order_id,
            status=status,
            avg_price=avg_price,
            executed_quantity=executed_quantity,
            outstanding_size=outstanding_size
        )

    def run_forever(self):
        logger.debug('OrderStatusBook start.')
        while True:
            messages = self.private.message_queue.get(block=True)
            for message in messages:
                acceptance_id = message['child_order_acceptance_id']
                self.order_status_by_parent_order_id[acceptance_id].append(message)
                self.lock.put(acceptance_id)


# NEW ORDER
# {'child_order_acceptance_id': 'JRF20200513-070354-573906',
#                                             'child_order_id': 'JFX20200513-070354-562409F',
#                                             'child_order_type': 'MARKET',
#                                             'event_date': '2020-05-13T07:03:54.8905877Z',
#                                             'event_type': 'ORDER',
#                                             'expire_date': '2020-06-12T07:03:54',
#                                             'price': 0,
#                                             'product_code': 'FX_BTC_JPY',
#                                             'side': 'SELL',
#                                             'size': 0.01}

# EXECUTION
# {'child_order_acceptance_id': 'JRF20200513-070354-573906',
#                                             'child_order_id': 'JFX20200513-070354-562409F',
#                                             'commission': 0,
#                                             'event_date': '2020-05-13T07:03:54.8905877Z',
#                                             'event_type': 'EXECUTION',
#                                             'exec_id': 1739873670,
#                                             'price': 965998,
#                                             'product_code': 'FX_BTC_JPY',
#                                             'sfd': 0,
#                                             'side': 'SELL',
#                                             'size': 0.01}]})

# https://note.com/kunmosky1/n/n2a0085d71426
class PrivateRealtimeAPI:
    def __init__(self, key, secret):
        self.end_point = 'wss://ws.lightstream.bitflyer.com/json-rpc'
        self.private_channels = ['child_order_events', 'parent_order_events']
        self.key = key
        self.secret = secret
        self.JSONRPC_ID_AUTH = 1
        self.message_queue = Queue()
        self.lock = Queue()

    def on_open(self, ws):
        logger.debug("Websocket connected")
        if len(self.private_channels) > 0:
            self.auth(ws)

    def on_error(self, ws, error):
        logger.warning(f'PrivateRealtimeAPI - {error}.')

    def on_close(self, ws):
        logger.debug("Websocket closed")

    def run(self, ws):
        while True:
            ws.run_forever()
            time.sleep(3)

    def wait(self):
        self.lock.get()

    def on_message(self, ws, message):
        messages = json.loads(message)
        if 'id' in messages and messages['id'] == self.JSONRPC_ID_AUTH:
            if 'error' in messages:
                logger.debug('auth error: {}'.format(messages["error"]))
            elif 'result' in messages and messages['result']:
                logger.debug('auth success.')
                params = [{'method': 'subscribe', 'params': {'channel': c}}
                          for c in self.private_channels]
                ws.send(json.dumps(params))
                time.sleep(5)
                self.lock.put('READY')
        if 'method' not in messages or messages['method'] != 'channelMessage':
            return
        self.message_queue.put(messages['params']['message'])

    def auth(self, ws):
        now = int(time.time())
        nonce = token_hex(16)
        sign = hmac.new(self.secret.encode(
            'utf-8'), ''.join([str(now), nonce]).encode('utf-8'), sha256).hexdigest()
        params = {'method': 'auth', 'params': {
            'api_key': self.key, 'timestamp': now,
            'nonce': nonce, 'signature': sign
        }, 'id': self.JSONRPC_ID_AUTH}
        ws.send(json.dumps(params))

    def start_and_wait_for_stream(self):
        ws = websocket.WebSocketApp(self.end_point,
                                    on_open=self.on_open,
                                    on_message=self.on_message,
                                    on_error=self.on_error,
                                    on_close=self.on_close)
        thread = Thread(target=self.run, args=(ws,))
        thread.start()
        self.wait()


class BitflyerRealtimeAPI:

    def __init__(self,
                 channel='lightning_ticker_FX_BTC_JPY',
                 debug=False):
        self._channel = channel
        self._url = 'wss://ws.lightstream.bitflyer.com/json-rpc'
        self._channel = channel
        self._debug = debug
        self._queue = Queue()
        self._ws = websocket.WebSocketApp(self._url,
                                          header=None,
                                          on_open=self._on_open,
                                          on_message=self._on_message,
                                          on_error=self._on_error,
                                          on_close=self._on_close)
        self._last_msg = None
        self._best_bid = None
        self._best_ask = None
        self._best_bid_size = None
        self._best_ask_size = None
        self._thread = threading.Thread(target=self._run)

    def get_last_msg(self):
        return self._last_msg

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
            logger.debug('Connecting...')
        self._thread.start()
        while self._last_msg is None:
            time.sleep(0.01)
        if self._debug:
            logger.debug('Connected... OK')

    def get(self, block=True, timeout=None):
        return self._queue.get(block, timeout)

    def _run(self):
        self._ws.run_forever()

    def _on_message(self, ws, message):
        j = json.loads(message)
        j['jst_time'] = str(datetime.now())
        self._last_msg = j
        self._queue.put(j)
        c = j['params']['channel']
        m = j['params']['message']
        if c.startswith('lightning_ticker_'):
            self._best_bid = m['best_bid']
            self._best_bid_size = m['best_bid_size']
            self._best_ask = m['best_ask']
            self._best_ask_size = m['best_ask_size']
        elif c.startswith('lightning_board_snapshot'):
            logger.debug('update')
            self.bids = m['bids']
            self.asks = m['asks']
            self._best_bid = self.bids[0]['price']
            self._best_ask = self.asks[0]['price']
            self._best_bid_size = self.bids[0]['size']
            self._best_ask_size = self.asks[0]['size']
        else:
            logger.debug('Unknown %s' % message)

    def _on_error(self, ws, error):
        if self._debug:
            logger.warning(f'BitflyerRealtimeAPI - {error}')

    def _on_close(self, ws):
        if self._debug:
            logger.debug('disconnected streaming server.')

    def _on_open(self, ws):
        if self._debug:
            logger.debug('connected streaming server.')
        output_json = json.dumps(
            {'method': 'subscribe',
             'params': {'channel': self._channel}
             }
        )
        ws.send(output_json)


class BitflyerRestAPI(pybitflyer.API):

    def __init__(self, credentials={}, timeout=None):
        super().__init__(credentials['apiKey'], credentials['secret'], timeout)

    def _wrap_new_order(self, resp):
        resp['id'] = resp['child_order_acceptance_id']
        return resp

    def create_limit_buy_order(self, ticker, quantity, price, params={}):
        return self._create_limit_order(ticker, quantity, price, 'BUY', params)

    def create_limit_sell_order(self, ticker, quantity, price, params={}):
        return self._create_limit_order(ticker, quantity, price, 'SELL', params)

    def create_market_buy_order(self, ticker, quantity, params={}):
        return self._create_market_order(ticker, quantity, 'BUY', params)

    def create_market_sell_order(self, ticker, quantity, params={}):
        return self._create_market_order(ticker, quantity, 'SELL', params)

    def fetch_order(self, order_id, symbol):
        return self.getchildorders(child_order_acceptance_id=order_id, product_code=symbol)

    def cancel_order(self, order_id, symbol, params={}):
        return self.cancelchildorder(product_code=symbol, child_order_acceptance_id=order_id)

    def _create_limit_order(self, ticker, quantity, price, side, params={}):
        time_in_force = params['time_in_force'] if 'time_in_force' in params else None
        minute_to_expire = params['minute_to_expire'] if 'minute_to_expire' in params else None
        resp = self.sendchildorder(product_code=ticker,
                                   child_order_type='LIMIT',
                                   price=price,
                                   side=side,
                                   size=quantity,
                                   minute_to_expire=minute_to_expire,
                                   time_in_force=time_in_force)
        try:
            return self._wrap_new_order(resp)
        except Exception:
            return resp

    def _create_market_order(self, ticker, quantity, side, params={}):
        resp = self.sendchildorder(product_code=ticker,
                                   child_order_type='MARKET',
                                   side=side,
                                   size=quantity)
        try:
            return self._wrap_new_order(resp)
        except Exception:
            return resp

    def fetch_order_status(self, order_id, symbol):  # does not handle partial fills.
        order = self.fetch_order(order_id, symbol)
        if len(order) == 0:  # either executed or canceled.
            trades = self.getexecutions(product_code=symbol, child_order_acceptance_id=order_id)
            if len(trades) == 0:
                return 'CANCELED'
            else:
                return 'COMPLETED'
        assert len(order) == 1
        order = order[0]
        return order['child_order_state']

    def fetch_executed_size(self, order_id, symbol):
        trades = self.getexecutions(product_code=symbol, child_order_acceptance_id=order_id)
        executed_size = 0.0
        for trade in trades:
            executed_size += float(trade['size'])
        return executed_size

    def fetch_executed_quantity_and_average_price(self, order_id, symbol):
        trades = self.getexecutions(product_code=symbol, child_order_acceptance_id=order_id)
        average_price = 0
        total_size = 0
        for trade in trades:
            average_price += trade['size'] * trade['price']
            total_size += trade['size']
        if total_size == 0:
            return 0, 0
        else:
            average_price /= total_size
            return total_size, average_price

    def get_positions(self):
        # self.getpositions() => buggy.
        positions = self.request('/v1/me/getpositions', params={'product_code': 'FX_BTC_JPY'})
        position_quantity = 0.0
        for position in positions:
            if position['side'] == 'BUY':
                position_quantity += position['size']
            else:
                position_quantity -= position['size']
        return position_quantity
