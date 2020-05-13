import os
from time import sleep

from bitflyer.bitflyer import OrderStatusBook, BitflyerRestAPI


def main():
    order_status = OrderStatusBook(os.environ['BITFLYER_KEY'], os.environ['BITFLYER_SECRET'])
    credentials = {
        'apiKey': os.environ['BITFLYER_KEY'],
        'secret': os.environ['BITFLYER_SECRET']
    }

    for i in range(10):
        private_rest = BitflyerRestAPI(credentials=credentials, timeout=1)
        private_rest.create_limit_buy_order('FX_BTC_JPY', 0.01, 980_000)
        sleep(2)
        private_rest.create_limit_sell_order('FX_BTC_JPY', 0.01, 920_000)
        for j in range(4):
            order_id = order_status.wait_for_new_msg()
            print(order_status.fetch_order_status(order_id))
        print('Next step in 10 seconds.')
        sleep(10)


if __name__ == '__main__':
    main()
