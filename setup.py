
import configparser
import os
from datetime import datetime

from src.utils import shift_hour_trunc


SECRETS_FILE = 'secrets.ini'
CONFIG_NAME = 'config.ini'
LOG_FILE = 'logfile.log'

MODEL_NAME = 'LSTM-2021-08-23.tflite'
PROJECT_PATH_ABS = os.path.abspath(os.path.join(os.path.dirname(__file__)))

def setup():
    # SECRETS
    cfg_secrets = configparser.ConfigParser()
    if not os.path.exists(SECRETS_FILE):
        cfg_secrets['DEFAULT'] = {'TESTNET_API_KEY': '***',
                                  'TESTNET_API_SECRET': '***',
                                  'MAINNET_API_KEY': '***',
                                  'MAINNET_API_SECRET': '***',
                                  }
        with open(SECRETS_FILE, 'w') as secretsfile:
            cfg_secrets.write(secretsfile)
            print('Created secrets.ini.')

    # CONFIG
    cfg = configparser.ConfigParser()
    if not os.path.exists(CONFIG_NAME):
        current_utc_timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        cfg['DEFAULT'] = {'SEQ_LEN': '48',
                          'RATIOS': '["BTCUSDT", "LTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "BTTUSDT", "DASHUSDT",'
                                    '"XMRUSDT", "NANOUSDT", "DOGEUSDT", "XLMUSDT", "BCHUSDT"]',
                          'RATIO_TO_PREDICT': 'BTCUSDT',
                          'MODEL_PATH': f'models/model/{MODEL_NAME}',
                          'DATA_PATH': 'data/',
                          'STATUS_ACTIVE': True,
                          'ORDERS_ALLOWED': False,
                          'BACKUPS_ALLOWED  ': False,
                          'ENVIROMENT': 'testnet',
                          'STARTING_BALANCE_USD': 0,
                          'STARTING_BALANCE_BTC': 0,
                          'STARTING_TIMESTAMP': shift_hour_trunc(current_utc_timestamp, h=0),  # ..17:03:58 ->..17:00:00
                          'CURRENT_BALANCE_USD': 0,
                          'CURRENT_BALANCE_BTC': 0
                          }
        with open(CONFIG_NAME, 'w') as configfile:
            cfg.write(configfile)
            print('Created config.ini')

    # LOGGING
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w') as f:
            f.write('')
            print('Created logfile.log')


if __name__ == "__main__":
    setup()

