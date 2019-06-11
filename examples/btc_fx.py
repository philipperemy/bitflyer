import time

from bitflyer import BitflyerRealtimeAPI


def main():
    api = BitflyerRealtimeAPI(channel='lightning_ticker_FX_BTC_JPY',
                              debug=False)
    api.start()
    while True:
        print('{0} {1:.3f} {2} {3:.5f}'.format(api.get_best_bid(), api.get_best_bid_size(),
                                               api.get_best_ask(), api.get_best_ask_size()))
        time.sleep(0.5)


if __name__ == '__main__':
    main()
