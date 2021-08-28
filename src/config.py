
import time
import json
import logging
import configparser
import os

from setup import CONFIG_NAME, LOG_FILE, SECRETS_FILE, PROJECT_PATH_ABS

# assumed config.py in crypto-bot/src, config.ini in crypto-bot/, setup.py in crypto-bot/
CONFIG_PATH_ABS = os.path.abspath(os.path.join(PROJECT_PATH_ABS, CONFIG_NAME))

cfg = configparser.ConfigParser()

cfg.read(CONFIG_PATH_ABS)

SEQ_LEN = cfg['DEFAULT'].getint('SEQ_LEN')
RATIOS = json.loads(cfg['DEFAULT']['RATIOS'])
RATIO_TO_PREDICT = cfg['DEFAULT']['RATIO_TO_PREDICT']

# for tensorflow 2.5 'models/model', for TFLite you need to specify 'models/model/model.tflite'
MODEL_PATH = cfg['DEFAULT']['MODEL_PATH']
MODEL_PATH_ABS = os.path.abspath(os.path.join(PROJECT_PATH_ABS, MODEL_PATH))

DATA_PATH = cfg['DEFAULT']['DATA_PATH']
DATA_PATH_ABS = os.path.abspath(os.path.join(PROJECT_PATH_ABS, DATA_PATH)) + os.path.sep  # ending with /

STATUS_ACTIVE = cfg['DEFAULT'].getboolean('STATUS_ACTIVE')
ORDERS_ALLOWED = cfg['DEFAULT'].getboolean('ORDERS_ALLOWED')
BACKUPS_ALLOWED = cfg['DEFAULT'].getboolean('BACKUPS_ALLOWED')
ENVIROMENT = cfg['DEFAULT']['ENVIROMENT']  # testnet or mainnet

# logging
# Level Numeric value
# CRITICAL 50
# ERROR 40
# WARNING 30
# INFO 20
# DEBUG 10
# NOTSET 0
LOG_FILE_ABS = os.path.abspath(os.path.join(PROJECT_PATH_ABS, LOG_FILE))

logging.basicConfig(filename=LOG_FILE_ABS,
                    level=logging.INFO,  # DEBUG is the lowest - the most information
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt='%Y-%m-%d %H:%M:%S')
logging.Formatter.converter = time.gmtime  # logs will be in gmt (UTC+0)
logger = logging.getLogger(__name__)

STARTING_BALANCE_USD = cfg['DEFAULT'].getfloat('starting_balance_USD')
STARTING_BALANCE_BTC = cfg['DEFAULT'].getfloat('starting_balance_BTC')
STARTING_TIMESTAMP = cfg['DEFAULT']['starting_timestamp']

CURRENT_BALANCE_USD = cfg['DEFAULT'].getfloat('current_balance_USD')
CURRENT_BALANCE_BTC = cfg['DEFAULT'].getfloat('current_balance_BTC')

def set_bot_config(**kwargs):  # e.g. set_bot_config(STATUS_ACTIVE=False)
    for key, value in kwargs.items():
        if key in cfg['DEFAULT']:
            cfg.set('DEFAULT', key, str(value))
            if (key == 'STATUS_ACTIVE') or (key == 'ORDERS_ALLOWED') or (key == 'BACKUPS_ALLOWED'):
                logger.info(f'[CONFIG] {key} set to {value}')
        else:
            raise Exception(f'Config has no {key} setting')
    with open(CONFIG_PATH_ABS, 'w') as configfile:
        cfg.write(configfile)
