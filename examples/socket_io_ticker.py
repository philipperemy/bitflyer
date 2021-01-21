import time

from bitflyer.ticker import SocketIOFastTickerAPI


def main():
    s = SocketIOFastTickerAPI()
    while True:
        print(s.get_bbo(), s.updater)
        time.sleep(0.1)


if __name__ == '__main__':
    main()
