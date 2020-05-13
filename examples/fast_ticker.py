import logging
import sys
from time import sleep

from bitflyer.ticker_from_order_book import FastTicker


def main():
    logging.basicConfig(format='%(asctime)12s - %(levelname)s - %(message)s', level=logging.INFO, stream=sys.stdout)
    FastTicker()
    # ft.get_bbo()
    sleep(10000)
    # while True:


# print('FT', ft.get_bbo(block=True))
# sleep(0.1)


if __name__ == '__main__':
    main()
