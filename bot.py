
from src.config import STATUS_ACTIVE, ORDERS_ALLOWED, BACKUPS_ALLOWED, set_bot_config, logger, LOG_FILE_ABS,\
                        STARTING_BALANCE_USD, STARTING_BALANCE_BTC
from src.data_update import update_all_data
from src.predict import predict_next
from src.data_backup import backup_data_from_RPi, pull_changes_from_remote
from src.orders import place_order, get_account_balances, convert_balances_to_USD
from src.process_logfile import process_logfile
from src.utils import shift_hour_trunc
from datetime import datetime


# bot.py is independent from app.py, however app.py requires processed logfile (done by bot.py) to draw the chart
def main():
    # Performed on PC:
    # training and evaluation of the model
    # simulation

    # Performed on RPi:
    if STATUS_ACTIVE is True:

        # Runs once at start (when logfile.log is empty), writes first entries in logfile.log from config.ini
        with open(LOG_FILE_ABS, 'rt') as f:
            logfile_content = f.read().strip('\n').strip(' ')
            if logfile_content == '':
                logger.info(f'Bot started')
                starting_balances = get_account_balances()  # this has try except inside when sending requests
                current_utc_timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                if starting_balances is not False:
                    set_bot_config(STARTING_BALANCE_USD=starting_balances['USD'],
                                   STARTING_BALANCE_BTC=starting_balances['BTC'],
                                   CURRENT_BALANCE_USD=starting_balances['USD'],
                                   CURRENT_BALANCE_BTC=starting_balances['BTC'],
                                   STARTING_TIMESTAMP=shift_hour_trunc(current_utc_timestamp, h=0)  # ..17:03:58 -> ..17:00:00
                                   )
                    logger.info(f'[BALANCE] {starting_balances["USD"]:.2f} USD, {starting_balances["BTC"]:.7f} BTC')
                else:
                    print('Cannot load starting balances. Check the provided API keys in secrets.ini')
                    return

        # missing values happens once per few months, it's better to check manually, so fill_missing=False
        # if missing values appear, error will be raised and logged, and bot will be set inactive
        update_successful = update_all_data(fill_missing=True)
        prediction_result = 'EVEN'  # default value if no prediction is made
        if update_successful is True:  # False in case if no new records available
            prediction_result = predict_next()  # 'UP' 'DOWN' 'EVEN'

        if ORDERS_ALLOWED is True:
            balances = get_account_balances()  # returns a dict with balances or False
            if balances is not False:
                # bot buys and sells alternately, and side depends from if he has more BTC or USD - checking that here
                balances_in_USD = convert_balances_to_USD(balances)
                if (balances_in_USD['USD'] > balances_in_USD['BTC']) and (prediction_result == 'UP'):
                    quantity = round(balances['USD'] * 0.995, 6)  # fixes "no sufficient amount", "precision err"
                    order_filled = place_order(side='BUY', quantity=quantity, symbol='BTCUSDT', order_type='MARKET')
                    if order_filled is not False:
                        balances = get_account_balances()
                        logger.info(f'[BALANCE] {balances["USD"]:.2f} USD, {balances["BTC"]:.7f} BTC')
                        set_bot_config(CURRENT_BALANCE_USD=balances['USD'], CURRENT_BALANCE_BTC=balances['BTC'])

                elif (balances_in_USD['USD'] <= balances_in_USD['BTC']) and (prediction_result == 'DOWN'):
                    quantity = round(balances['BTC'] * 0.995, 6)
                    order_filled = place_order(side='SELL', quantity=quantity, symbol='BTCUSDT', order_type='MARKET')
                    if order_filled is not False:
                        balances = get_account_balances()
                        logger.info(f'[BALANCE] {balances["USD"]:.2f} USD, {balances["BTC"]:.7f} BTC')
                        set_bot_config(CURRENT_BALANCE_USD=balances['USD'], CURRENT_BALANCE_BTC=balances['BTC'])
                else:
                    pass  # bot alternates between BUY/SELL state so no need more orders conditions

        process_logfile()  # process logfile to get accuracies and information for chart and save data as logfile.csv

        if (update_successful is True) and (BACKUPS_ALLOWED is True):  # False in case if no new records available
            pull_changes_from_remote()
            backup_data_from_RPi()  # use with ssh key for github in default location without passphrase

    else:  # when STATUS_ACTIVE is False, bot does nothing
        pass


if __name__ == "__main__":
    main()

