import json
import logging

import pandas as pd

logger = logging.getLogger(__name__)

def fast_apply_updates(order_book, updates):
    pass

def apply_updates(order_book, updates):
    def single_update(ob, update, side):
        logger.debug(f'UPDATE: {update}, {side}')
        for ob_entry in ob[side]:
            if ob_entry['price'] == update['price']:
                ob_entry['size'] = update['size']
                return

        ob[side].append(update)  # new entry.
        asc = True if side == 'asks' else False
        ob[side] = json.loads(pd.DataFrame(ob[side]).sort_values(by='price', ascending=asc).to_json(orient='records'))

    def clean_zero(ob):
        new_bids = []
        new_asks = []
        for bids_ in ob['bids']:
            if bids_['size'] != 0:
                new_bids.append(bids_)
            else:
                logger.debug(f'Clear bid level {bids_["price"]}')
        for asks in ob['asks']:
            if asks['size'] != 0:
                new_asks.append(asks)
            else:
                logger.debug(f'Clear ask level {asks["price"]}')
        ob['bids'] = new_bids
        ob['asks'] = new_asks

    snap_u = dict(order_book)
    for u in updates:
        try:
            bids = u['params']['message']['bids']
        except:
            bids = u['bids']
        for bid in bids:
            single_update(snap_u, bid, 'bids')
        try:
            asks = u['params']['message']['asks']
        except:
            asks = u['asks']
        for ask in asks:
            single_update(snap_u, ask, 'asks')
        clean_zero(snap_u)
    return snap_u


def compare_ob(first, second):
    first_bid = set([json.dumps(u) for u in first['bids']])
    second_bid = set([json.dumps(u) for u in second['bids']])
    first_ask = set([json.dumps(u) for u in first['asks']])
    second_ask = set([json.dumps(u) for u in second['asks']])

    diff_bid = list(first_bid - second_bid) + list(second_bid - first_bid)
    diff_ask = list(first_ask - second_ask) + list(second_ask - first_ask)
    logger.debug(f'DIFF BID ({len(diff_bid)}): {diff_bid}')
    logger.debug(f'DIFF ASK ({len(diff_ask)}): {diff_ask}')
