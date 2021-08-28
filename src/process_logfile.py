
import numpy as np
import pandas as pd
from src.utils import datetime_to_unix, unix_to_datetime, shift_hour_trunc
from src.config import LOG_FILE_ABS, DATA_PATH_ABS, STARTING_TIMESTAMP, STARTING_BALANCE_USD, STARTING_BALANCE_BTC


def process_logfile():
    def classifier(current, future):
        if current < future:
            return 'UP'
        elif current == future:
            return np.nan
        elif current > future:
            return 'DOWN'

    df = pd.read_csv(f'{DATA_PATH_ABS}Binance_BTCUSDT_1h.csv', parse_dates=['date'], usecols=[0, 1])  # volume not required
    df.set_index("date", inplace=True)
    # shifted by 72h for 72h chart, so if we pass current date as STARTING_TIMESTAMP, it will still plot full chart
    df = df.truncate(before=shift_hour_trunc(STARTING_TIMESTAMP, h=-72))
    df['future'] = df[f"BTCUSDT_close"].shift(-1)
    df['target'] = list(map(classifier, df[f"BTCUSDT_close"], df["future"]))
    # df.drop('future', 1, inplace=True)  # future is not necessary from now but no need to drop it

    df['predictions_shifted'] = None
    df['accurate_prediction'] = None
    df['orders_shifted'] = None
    df['balance_USD'] = np.nan  # np.nan instead of None so we can use interpolate (fill nans with nearest vals) later
    df['balance_BTC'] = np.nan

    balance_USD = STARTING_BALANCE_USD
    balance_BTC = STARTING_BALANCE_BTC
    with open(LOG_FILE_ABS, 'rt') as f:
        logs_data_lines = [line for line in f.readlines() if line.strip()]  # strips empty lines
        for line in logs_data_lines:
            if line[-1] == '\n':
                line = line[:-1]  # [:-1] removes /n
            timestamp = line[:19]
            # using "at" vs "loc" should be faster, but for some reason here it isn't
            if '[PREDICTION]' in line:
                if 'UP: ' in line:  # should be more optimized than with "and"
                    up_percentage = int(line.partition(f'UP: ')[2][:-1])  # 2 bcs ('.', 'UP: ', '52%) and -1 to remove %
                    if up_percentage > 50:
                        df.at[shift_hour_trunc(timestamp, h=-1), 'predictions_shifted'] = 'UP'
                    elif up_percentage < 50:
                        df.at[shift_hour_trunc(timestamp, h=-1), 'predictions_shifted'] = 'DOWN'
            elif '[ORDER]' in line:
                if 'BUY' in line:
                    df.at[shift_hour_trunc(timestamp, h=-1), 'orders_shifted'] = 'BUY'
                elif 'SELL' in line:
                    df.at[shift_hour_trunc(timestamp, h=-1), 'orders_shifted'] = 'SELL'
            elif '[BALANCE]' in line:  # balance is not shifted
                balance_USD = float(line.split(' ')[4])
                balance_BTC = float(line.split(' ')[6])
            # h=0, h=1 because it's current balance (e.g. 14:00) and last index on chart BTC_sclose will be (13:00)
            # df.index doesnt need trunc, but it needs added h=1
            # we want to omit last balance record, because we don't have BTC_close price for it yet
            if shift_hour_trunc(timestamp, h=0) != shift_hour_trunc(str(df.index[-1]), h=1):
                df.at[shift_hour_trunc(timestamp, h=0), 'balance_USD'] = balance_USD
                df.at[shift_hour_trunc(timestamp, h=0), 'balance_BTC'] = balance_BTC

    # [None, 1, 2, None, None, 3, None, None, 2, None, 1, 2, None, 1] -> [1, 1, 2, 2, 2, 3, 3, 3, 2, 2, 1, 2, 2, 1]
    # here there are values like 0.002341 or 94,82 instead of 1 2 3, but it shows the idea
    # firstly forward fill
    df['balance_USD'].interpolate(method='ffill', inplace=True)
    # now assume that before starting timestamp balance was the same that last entry
    df['balance_USD'].interpolate(method='bfill', inplace=True)

    df['balance_BTC'].interpolate(method='ffill', inplace=True)  # doing the same for BTC
    df['balance_BTC'].interpolate(method='bfill', inplace=True)

    def check_prediction(x):
        # target, predictions_shifted -> accurate_prediction
        # UP, UP -> True
        # UP, DOWN -> False
        # UP, NONE -> None
        # np.nan, None -> None
        # None, None -> None
        if type(x['target']) == str and type(x['predictions_shifted']) == str:
            if x['target'] == x['predictions_shifted']:
                return True
            else:
                return False
        else:
            return None

    df['accurate_prediction'] = df.apply(check_prediction, axis=1)
    df.to_csv(f'{LOG_FILE_ABS[:-4]}.csv', header=True)  # truncating extension .log and saving as .csv
    # logfile.log is still nedeed, it will be displayed in Log textarea


if __name__ == "__main__":
    process_logfile()
