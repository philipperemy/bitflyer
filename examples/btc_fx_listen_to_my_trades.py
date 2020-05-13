import os
from time import sleep

from bitflyer.bitflyer import OrderEventsAPI, BitflyerRestAPI


def main():
    order_status = OrderEventsAPI(os.environ['BITFLYER_KEY'], os.environ['BITFLYER_SECRET'])
    credentials = {
        'apiKey': os.environ['BITFLYER_KEY'],
        'secret': os.environ['BITFLYER_SECRET']
    }

    for i in range(10):
        private_rest = BitflyerRestAPI(credentials=credentials, timeout=1)
        private_rest.create_market_buy_order('FX_BTC_JPY', 0.01)
        sleep(2)
        private_rest.create_market_sell_order('FX_BTC_JPY', 0.01)
        for j in range(4):
            order_id = order_status.wait_for_new_msg()
            print(order_status.fetch_order_status(order_id))
        print('Next step in 10 seconds.')
        sleep(10)


if __name__ == '__main__':
    main()
