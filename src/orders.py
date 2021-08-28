
import configparser
import os
import time
from json import loads
from requests import get
from binance.client import Client

from src.config import RATIOS, logger, set_bot_config, ENVIROMENT, PROJECT_PATH_ABS, DATA_PATH_ABS, SECRETS_FILE

# doing it here since only functions in this file use authentication on Binance. E.g. Flask doesnt need that
cfg_secrets = configparser.ConfigParser()
SECRETS_FILE_ABS = os.path.abspath(os.path.join(PROJECT_PATH_ABS, SECRETS_FILE))
cfg_secrets.read(SECRETS_FILE_ABS)

if ENVIROMENT == 'testnet':
    TESTNET_API_KEY = cfg_secrets['DEFAULT']['TESTNET_API_KEY']
    TESTNET_API_SECRET = cfg_secrets['DEFAULT']['TESTNET_API_SECRET']
    client = Client(TESTNET_API_KEY, TESTNET_API_SECRET, testnet=True)
elif ENVIROMENT == 'mainnet':
    MAINNET_API_KEY = cfg_secrets['DEFAULT']['MAINNET_API_KEY']
    MAINNET_API_SECRET = cfg_secrets['DEFAULT']['MAINNET_API_SECRET']
    client = Client(MAINNET_API_KEY, MAINNET_API_SECRET, testnet=False)

def get_account_balances():
    try:
        BTC = client.get_asset_balance(asset='BTC')['free']
        USD = client.get_asset_balance(asset='USDT')['free']  # assumed 1:1 USD/USDT ratio, using 'USD' name
    except Exception as e:
        logger.error(f'[get_account_balances] {e}')
        return False
    # print(f'{USD} USD, {BTC} BTC')
    return {'BTC': float(BTC), 'USD': float(USD)}


def get_last_price():
    try:
        # 'https://testnet.binance.vision/api/v3/ticker/price?symbol=BTCUSDT'  # for testnet
        # 'https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT'  # for mainnet
        if ENVIROMENT == 'testnet':
            url = 'https://testnet.binance.vision/api/v3/ticker/price'
        elif ENVIROMENT == 'mainnet':
            url = 'https://api.binance.com/api/v3/ticker/price'
        response = get(url, params={'symbol': 'BTCUSDT'})
    except Exception as e:
        logger.error(f'[get_last_price] {e}')
        return False
    return float(loads(response.text)['price'])


def get_last_data_price():
    with open(f"{DATA_PATH_ABS}Binance_BTCUSDT_1h.csv", 'r') as file:
        last_data_price = float(file.readlines()[-1].split(',')[1])  # -1 bcs last line and 1 bcs (date, close, volume)
    return last_data_price


def convert_balances_to_USD(balances_dict):
    new_balances_dict = balances_dict.copy()
    last_data_price = get_last_data_price()
    new_balances_dict['BTC'] = balances_dict['BTC'] * last_data_price
    new_balances_dict['USD'] = balances_dict['USD']
    return new_balances_dict  # {'BTC': BTC, 'USD': USD} and USD is not changed


# quantity is translated to quantity or quoteOrderQty. quantity is always known, so no additional calculations needed
def place_order(side, quantity, symbol, order_type):  # side='SELL', quantity=0.1, symbol='BTCUSDT', order_type='MARKET'

    # checking actual price, to prevent error (if no enough liquidity in the market, etc)
    last_data_price = get_last_data_price()  # last price from data/ folder
    max_diff = last_data_price * 0.02  # for 45000 it is 900, very unlikely to make 2% change in few minutes
    price_confirmed = False
    for i in range(0, 10):
        last_price = get_last_price()  # last price from the exchange ticker
        if abs(last_data_price - last_price) > max_diff:
            time.sleep(5)  # sleep 5 seconds, wait for price change
            continue
        else:
            price_confirmed = True
            break
    if price_confirmed is False:  # function returns False in this case
        logger.warning(f'[ORDER CANCELLED] Market price changed too much, {last_data_price:.7f} -> {last_price:.7f}')
        return False

    # placing order
    if side == 'BUY':  # e.g buy x BTC for 80 USD so quoteOrderQty=80
        try:
            order = client.create_order(side=side, quoteOrderQty=quantity, symbol=symbol, type=order_type)
        except Exception as e:
            set_bot_config(ORDERS_ALLOWED=False)
            logger.error(f'[place_order] side={side}, quoteOrderQty={quantity} {e}')
            return False
    elif side == 'SELL':  # e.g sell 0.0003BTC for 80 USD so quantity=0.0003
        try:
            order = client.create_order(side=side, quantity=quantity, symbol=symbol, type=order_type)
        except Exception as e:
            set_bot_config(ORDERS_ALLOWED=False)
            logger.error(f'[place_order] side={side}, quantity={quantity} {e}')
            return False

    # e.g. in BTCUSDT, BTC is base asset and USDT is quote asset
    quote_amount = float(order["cummulativeQuoteQty"])  # USD (USDT but we assume 1:1)
    base_amount = float(order['executedQty'])  # BTC
    fills = order["fills"]
    status = order["status"]
    # fee = 0.001  # not dealing with fees, we check the balances later from the exchange anyway

    # order that is partially filled is still in order book and waiting for filling so no need to renew it
    if len(fills) > 0:  # its better than status == 'FILLED': because EXPIRED can also be partially filled :/
        avg_price = quote_amount / base_amount
        # format of logs e.g.:
        # 2021-07-27 05:05:51 [INFO] [ORDER] [FILLED] BUY 0.0003523 BTC for 23.12 USD at 33123.12 USD/BTC in 1 FILL
        # 2021-07-27 09:05:53 [INFO] [ORDER] [FILLED] SELL 0.0003523 BTC for 23.89 USD at 33242.43 USD/BTC in 2 FILLS
        if side == 'BUY':
            logger.info(f'[ORDER] [{status}] {side} {base_amount:.7f} BTC for {quote_amount:.2f} USD'
                        f' at {avg_price:.2f} USD/BTC in {len(fills)} FILL{"S" if len(fills) > 1 else ""}')
        elif side == 'SELL':
            logger.info(f'[ORDER] [{status}] {side} {base_amount:.7f} BTC for {quote_amount:.2f} USD'
                        f' at {avg_price:.2f} USD/BTC in {len(fills)} FILL{"S" if len(fills) > 1 else ""}')
    else:
        logger.warning(f'[ORDER] [{status}] Response: {order}')
        set_bot_config(ORDERS_ALLOWED=False)
        return False
    return True
