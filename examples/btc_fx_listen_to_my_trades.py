import os

from bitflyer.ord_status import OrderEventsAPI
from bitflyer.trading import BitflyerRestAPI


def main():
    key = os.environ['BITFLYER_KEY']
    secret = os.environ['BITFLYER_SECRET']

    order_status = OrderEventsAPI(key, secret)
    for i in range(10):
        private_rest = BitflyerRestAPI(credentials={'apiKey': key, 'secret': secret}, timeout=1)
        best_bid = private_rest.ticker(ticker='FX_BTC_JPY')['best_bid']
        order = private_rest.create_limit_buy_order('FX_BTC_JPY', 0.01, price=best_bid - 100_000,
                                                    params={'minute_to_expire': 1})
        print(f'posted order {order}.')
        while True:
            print(order_status.message_queue.get())


if __name__ == '__main__':
    main()
