# Bitflyer Realtime Feed (python)

- https://lightning.bitflyer.com/docs?lang=en

## Installation
```
pip install bitflyer-rt
```

## Tickers

Available channels:

- lightning_ticker_BTC_JPY
- lightning_ticker_FX_BTC_JPY
- lightning_ticker_ETH_BTC

## Example

```
> python examples/btc_fx.py

887158.0 0.010 887231.0 0.05152   <--- best bid, best bid size, best ask, best ask size
887163.0 0.010 887204.0 0.01200
887163.0 0.010 887204.0 0.01200
887234.0 0.428 887237.0 0.00000
887234.0 0.428 887237.0 0.00000
887234.0 0.377 887244.0 0.01000
887234.0 0.377 887244.0 0.01000
887235.0 0.010 887399.0 0.28054
```

```python
api = CcxtLikeAPI(api_key=API_KEY, api_secret=API_SECRET)
order_id = api.create_limit_sell_order(ticker=SYMBOL, quantity=0.01, price=950_000)['child_order_acceptance_id']
for i in range(10):
    print(api.fetch_order_status(order_id, symbol=SYMBOL))
    sleep(0.1)
print(api.cancel_order(order_id, symbol=SYMBOL))
for i in range(10):
    print(api.fetch_order_status(order_id, symbol=SYMBOL))
    sleep(0.1)
```
