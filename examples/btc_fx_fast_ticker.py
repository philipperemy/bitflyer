import logging
import sys
from time import sleep

from bitflyer.rpc_ticker import FastTickerAPI


def main():
    logging.basicConfig(format='%(asctime)12s - %(levelname)s - %(message)s', level=logging.INFO, stream=sys.stdout)
    FastTickerAPI()
    sleep(10000000)


if __name__ == '__main__':
    main()
