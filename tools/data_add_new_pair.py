# this file is not used by the bot or app

import pandas as pd
import numpy as np
import time
from datetime import datetime
from requests import get
from json import loads

from src.utils import unix_to_datetime, datetime_to_unix, UTC_OFFSET
from src.data_update import update_ratio
from src.config import DATA_PATH_ABS

def download_data(starting_time, ratio, filename):
    try:
        open(filename, "r")
        raise Exception('File already exists, you can only update it.')
    except FileNotFoundError:
        pass
    last_record_unix = datetime_to_unix(str(starting_time), h=-UTC_OFFSET)  # -2 because of timezones

    response = get('https://api.binance.com/api/v1/klines',
                params={'symbol': ratio,
                        'interval': '1h',
                        'startTime': last_record_unix,
                        'limit': 1000})
    raw_data = loads(response.content)
    raw_data_df = pd.DataFrame(raw_data)

    new_df = pd.DataFrame(columns=['date', f'{ratio}_close', f'{ratio}_volume'])
    # we receive data in UTC+2 timezone, so need to set h=-2, so we pass list of [-2] as second argument
    new_df['date'] = list(map(unix_to_datetime, raw_data_df[0], [UTC_OFFSET] * len(raw_data_df[0])))
    new_df[f'{ratio}_close'] = list(map(float, raw_data_df[4]))  # df[4]  # Close
    new_df[f'{ratio}_volume'] = list(map(float, raw_data_df[7]))  # df[7]  # Quote asset volume (second assets unit, so in BTC/USDT its volume_USDT)  # noqa
    new_df.set_index("date", inplace=True)
    # if we send request at 15:27 (UTC-0 13:27) it will return data with last entry 13:00 which will change over time
    new_df = new_df[:-1]  # dropping that entry

    new_df.index = pd.to_datetime(new_df.index)
    expected_range = pd.date_range(start=new_df.index.min(), end=new_df.index.max(), freq='H')
    missing_ts = list(expected_range.difference(new_df.index))
    if missing_ts:
        # inp = input(f'Missing timestamps: {missing_ts}.\n'
        #             f'{len(expected_range) - len(new_df.index)} missing timestamps. y - interpolate, n - exit\n')
        new_df = new_df.resample('60min').mean()
        new_df.replace(to_replace=0, value=np.nan, inplace=True)  # converting 0s to NaNs
        new_df.interpolate(method='linear', inplace=True)  # interpolating missing nan values
        print(f'Missing timestamps: {missing_ts}.\n'
              f'{len(missing_ts)} missing timestamps. auto interpolate')

    return new_df


def data_add_new_pair():
    ratio = ['XRPUSDT']  # ["BCHUSDT"]
    starting_time = datetime.strptime('2017-01-01 00:00:00', '%Y-%m-%d %H:%M:%S')
    # it only downloads first 500 records, to get all data use update_data() on new pair .csv file
    filename = f"{DATA_PATH_ABS}Binance_{ratio}_1h.csv"
    df_first = download_data(starting_time, ratio, filename)
    df_first.to_csv(filename)
    while True:  # added data_update from src.data_update.py
        filename = f"{DATA_PATH_ABS}Binance_{ratio}_1h.csv"
        time.sleep(0.3)
        new_df = update_ratio(ratio, filename, request_records=1000, fill_missing=True)
        new_df.to_csv(filename, mode='a', header=False)


if __name__ == "__main__":
    data_add_new_pair()
