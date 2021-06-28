import pandas as pd
from datetime import datetime, timedelta
from requests import get
from json import loads
from bot.utils import unix_to_datetime, datetime_to_unix
import time
import numpy as np
from bot.config import RATIOS

# curl -X GET "https://api.binance.com/api/v1/klines?&symbol=BTCUSDT&interval=3m"
# https://binance-docs.github.io/apidocs/spot/en/#kline-candlestick-data

def update_ratio(ratio, filename, request_records=500):
    old_df = pd.read_csv(filename, nrows=None, skiprows=None, parse_dates=['date'], usecols=[0, 1, 2])
    old_df.set_index("date", inplace=True)
    last_record_dt = old_df.tail(1).index.item()  # get last record in old csv that is being updated
    last_record_unix = datetime_to_unix(str(last_record_dt), h=2)  # -2 because of timezones

    seconds_from_last_update = (datetime.utcnow() - last_record_dt).total_seconds()
    if seconds_from_last_update <= timedelta(hours=2).seconds:
        seconds_remaining = timedelta(hours=2).seconds - seconds_from_last_update
        raise Exception(f'Too early. Next update available in: {str(timedelta(seconds=seconds_remaining))}')

    response = get('https://api.binance.com/api/v1/klines',
                params={'symbol': ratio,
                        'interval': '1h',
                        'startTime': last_record_unix,
                        'limit': request_records})

    raw_data = loads(response.content)
    raw_data_df = pd.DataFrame(raw_data)

    new_df = pd.DataFrame(columns=['date', f'{ratio}_close', f'{ratio}_volume'])
    # we receive data in UTC+2 timezone, so need to set h=-2, so we pass list of [-2] as second argument
    hours_difference = -2
    new_df['date'] = list(map(unix_to_datetime, raw_data_df[0], [hours_difference] * len(raw_data_df[0])))
    new_df[f'{ratio}_close'] = list(map(float, raw_data_df[4]))  # df[4]  # Close
    new_df[f'{ratio}_volume'] = list(map(float, raw_data_df[7]))  # df[7]  # Quote asset volume (second assets unit, so in BTC/USDT its volume_USDT)  # noqa
    new_df.set_index("date", inplace=True)
    # if we send request at 15:27 (UTC-0 13:27) it will return data with last entry 13:00 which will change over time
    new_df = new_df[:-1]  # dropping that entry
    print(f'RATIO: {ratio}, New records: {len(new_df)}')
    # checking if most recent entry of old df is equal to oldest entry of new df
    old_newest = old_df[f'{ratio}_close'][-1]
    new_oldest = new_df[f'{ratio}_close'][0]
    if old_newest != new_oldest:
        pass
        # inp = input(f'old_df[-1] is not equal new_df[0]: {old_newest} != {new_oldest}. y - keep going, n - exit\n')
        # print(f'old_df[-1] is not equal new_df[0]: {old_newest} != {new_oldest}. auto keep going')
        # results in e.g.: old_df[-1] is not equal new_df[0]: 0.23510999999999999 != 0.23511. auto keep going

    # check for gaps in timestamps
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


    df_merged = old_df.append(new_df[1:])  # we drop new_df[0] because its the same as in old_df[-1]
    return df_merged

def update_all_data():
    for ratio in RATIOS:
        filename = f"data/Binance_{ratio}_1h.csv"
        time.sleep(0.3)
        df_merged = update_ratio(ratio, filename, request_records=500)
        df_merged.to_csv(filename)

def main():
    update_all_data()


if __name__ == "__main__":
    main()