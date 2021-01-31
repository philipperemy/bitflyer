import time

from bitflyer.ticker import SocketIOFastTickerAPI


def main():
    s = SocketIOFastTickerAPI()
    while True:
        print(s.get_bbo(), s.updater, s.order_book.qos, int(s.order_book.ups.rate), s.order_book.liquidity_for(1))
        time.sleep(0.1)


if __name__ == '__main__':
    main()
