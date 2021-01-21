import logging
import os
import sys
import threading
from time import sleep, time

from bitflyer.ord_status import OrderEventsAPI
from bitflyer.trading import BitflyerRestAPI
from build.lib.bitflyer.rpc_ticker import FastTickerAPI

SYMBOL = 'FX_BTC_JPY'
QUANTITY = 0.01

logger = logging.getLogger(__name__)


def sadly_close_order(order_passing_api, order_events_api, order_id, text, market_func):
    logger.info(f'CANCEL: {text}.')
    assert order_events_api.fetch_order_status(order_id).status != 'cancel'
    order_passing_api.cancel_order(order_id, 'FX_BTC_JPY')
    while True:
        order_to_delete_info = order_events_api.fetch_order_status(order_id).status
        if order_to_delete_info == order_events_api.FULLY_FILL:
            logger.info('Eventually got executed.')
            return
        if order_to_delete_info == order_events_api.CANCEL:
            break
        if order_to_delete_info == order_events_api.CANCEL_FAILED:
            break
        sleep(0.001)
    logger.info(f'MARKET: {text}.')
    order_id = market_func(SYMBOL, QUANTITY)
    while True:
        market_status = order_events_api.fetch_order_status(order_id['id'])
        if market_status is not None and market_status.status == 'full_fill':
            break
        sleep(0.001)


def main():
    logging.basicConfig(format='%(asctime)12s - %(levelname)s - %(message)s', level=logging.INFO, stream=sys.stdout)
    bitflyer_key = os.environ['BITFLYER_KEY']
    bitflyer_secret = os.environ['BITFLYER_SECRET']
    credentials = {'apiKey': bitflyer_key, 'secret': bitflyer_secret}
    order_passing_api = BitflyerRestAPI(credentials, timeout=5)
    logger.info(f'Collateral: {order_passing_api.getcollateral()["collateral"]} yen.')
    order_events_api = OrderEventsAPI(bitflyer_key, bitflyer_secret)
    market_data_api = FastTickerAPI()
    time_to_wait_before_closing_the_step = 5  # seconds.

    for i in range(1000):
        bid, ask = market_data_api.get_bbo()
        logger.info('_' * 30)
        bid_price = bid + 1
        ask_price = ask - 1
        logger.info(f'Limit BUY {QUANTITY}@{bid_price}.')
        logger.info(f'Limit SELL {QUANTITY}@{ask_price}.')
        order_ids = {}

        def buy():
            order_ids['buy'] = order_passing_api.create_limit_buy_order(SYMBOL, QUANTITY, bid_price)

        def sell():
            order_ids['sell'] = order_passing_api.create_limit_sell_order(SYMBOL, QUANTITY, ask_price)

        bt = threading.Thread(target=buy)
        st = threading.Thread(target=sell)
        bt.start()
        st.start()
        bt.join()
        st.join()

        buy_id = order_ids['buy']['id']
        sell_id = order_ids['sell']['id']
        start_ref = time()
        while True:
            buy_order_info = order_events_api.fetch_order_status(buy_id)
            sell_order_info = order_events_api.fetch_order_status(sell_id)
            if buy_order_info is None or sell_order_info is None:
                continue
            if (time() - start_ref) > time_to_wait_before_closing_the_step:

                if sell_order_info.status == order_events_api.FULLY_FILL and \
                        buy_order_info.status != order_events_api.FULLY_FILL:
                    sadly_close_order(order_passing_api, order_events_api, buy_order_info.order_id, 'Buy',
                                      order_passing_api.create_market_buy_order)
                    break

                if buy_order_info.status == order_events_api.FULLY_FILL and \
                        sell_order_info.status != order_events_api.FULLY_FILL:
                    sadly_close_order(order_passing_api, order_events_api, sell_order_info.order_id, 'Sell',
                                      order_passing_api.create_market_sell_order)
                    break

            if buy_order_info.status == order_events_api.FULLY_FILL and \
                    sell_order_info.status == order_events_api.FULLY_FILL:
                logger.info('All executed.')
                break


if __name__ == '__main__':
    main()
