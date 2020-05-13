import logging
import sys
from time import sleep

from bitflyer.ticker_from_order_book import FastTicker


def main():
    logging.basicConfig(format='%(asctime)12s - %(levelname)s - %(message)s', level=logging.INFO, stream=sys.stdout)
    ft = FastTicker()
    # ft.get_bbo()
    sleep(10000000)


if __name__ == '__main__':
    main()
