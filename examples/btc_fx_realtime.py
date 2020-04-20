from datetime import datetime
import numpy as np
from bitflyer import BitflyerRealtimeAPI


def get_bbo(api: BitflyerRealtimeAPI):
    return [api.get_best_bid(), api.get_best_bid_size(), api.get_best_ask(), api.get_best_ask_size()]


def main():
    api = BitflyerRealtimeAPI(channel='lightning_ticker_FX_BTC_JPY', debug=False)
    api.start()
    last_bbo = None
    last_arrival = None
    avg_arrival_times = []
    while True:
        bbo = get_bbo(api)
        if bbo != last_bbo:
            now = datetime.now()
            if last_arrival is not None:
                avg_arrival_times.append((now - last_arrival).total_seconds())
            last_bbo = bbo
            last_arrival = now
            print('[{0}] {1} {2:.3f} {3} {4:.5f}'.format(last_arrival, bbo[0], bbo[1], bbo[2], bbo[3]))
            if len(avg_arrival_times) > 0 and len(avg_arrival_times) % 100 == 0:
                print(f'Average arrival time: {np.mean(avg_arrival_times):.4f} '
                      f'seconds on {len(avg_arrival_times)} values.')


if __name__ == '__main__':
    main()

