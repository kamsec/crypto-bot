
# this file is for testing functions manually and executing tools from tools/ that are not used by the bot
# it is not used by the bot.py or app.py

def test_simulation():
    from tools.simulate import simulation
    simulation()
# test_simulation()


def test_prediction():
    # watch out because executing it will print output to logfile.log and might have unexpected behaviour for app.py
    from src.predict import predict_next
    predict_next()
# test_prediction()


def my_test_orders():
    from binance.client import Client
    import configparser

    cfg_secrets = configparser.ConfigParser()
    cfg_secrets.read('secrets.ini')
    TESTNET_API_KEY = cfg_secrets['DEFAULT']['TESTNET_API_KEY']
    TESTNET_API_SECRET = cfg_secrets['DEFAULT']['TESTNET_API_SECRET']

    client = Client(TESTNET_API_KEY, TESTNET_API_SECRET, testnet=True)

    BTC = client.get_asset_balance(asset='BTC')['free']
    USDT = client.get_asset_balance(asset='USDT')['free']
    ETH = client.get_asset_balance(asset='ETH')['free']
    print(f'BTC: {BTC}, USDT: {USDT}, ETH: {ETH}')

    # https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md#lot_size
    # quantity= or quoteOrderQty=
    # order = client.create_order(side='SELL', quantity=round(49.963952), symbol='BTCUSDT', type='MARKET')
    # order = client.create_order(side='BUY', quoteOrderQty=round(50, 6), symbol='ETHUSDT', type='MARKET')
    # print(order)

    BTC = client.get_asset_balance(asset='BTC')['free']
    USDT = client.get_asset_balance(asset='USDT')['free']
    ETH = client.get_asset_balance(asset='ETH')['free']
    print(f'BTC: {BTC}, USDT: {USDT}, ETH: {ETH}')
    # exit()

    # request:
    # BTC = client.get_asset_balance(asset='BTC')['free']
    # resulted in:
    # binance.exceptions.BinanceAPIException: APIError(code=-1021): Timestamp for this request was 1000ms ahead of the server's time.
    # windows fix:
    # from control panel > date and time > internet time
    # change the server to >>>> time.nist.gov
# my_test_orders()

