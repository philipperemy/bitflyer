import os
import time
from pprint import pprint

from bitflyer.bitflyer import OrderStatusBook, BitflyerRestAPI


def main():
    order_status = OrderStatusBook(os.environ['BITFLYER_KEY'], os.environ['BITFLYER_SECRET'])
    credentials = {
        'apiKey': os.environ['BITFLYER_KEY'],
        'secret': os.environ['BITFLYER_SECRET']
    }
    private_rest = BitflyerRestAPI(credentials=credentials, timeout=1)
    order = private_rest.create_limit_buy_order('FX_BTC_JPY', 0.01, 980_000)
    print(order)
    while True:
        time.sleep(5)
        print(pprint(order_status.order_status_by_parent_order_id))


if __name__ == '__main__':
    main()
