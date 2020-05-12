import time

from bitflyer import BitflyerRealtimeAPI


def main():
    api = BitflyerRealtimeAPI(channel='lightning_board_snapshot_FX_BTC_JPY', debug=False)
    api.start()
    while True:
        print('Hello')
        m = api.get()
        print(f'Received update {m["jst_time"]}.')
        time.sleep(0.01)


if __name__ == '__main__':
    main()
