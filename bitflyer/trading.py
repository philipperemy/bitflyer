import pybitflyer


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
