import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from requests import get
from json import loads

from src.utils import UTC_OFFSET, unix_to_datetime, datetime_to_unix
from src.config import RATIOS, logger, DATA_PATH_ABS, set_bot_config


def update_ratio(ratio, filename, request_records=500, fill_missing=False):
    old_df = pd.read_csv(filename, nrows=None, skiprows=None, parse_dates=['date'], usecols=[0, 1, 2])
    old_df.set_index("date", inplace=True)
    last_record_dt = old_df.tail(1).index.item()  # get last record (1 element of tail) in old csv that is being updated
    last_record_unix = datetime_to_unix(str(last_record_dt), h=-UTC_OFFSET)  # -UTC_OFFSET because of timezones

    '''
    logger.debug(f'Existing records: {len(old_df)}   |   '
                 f'Last close: {old_df.tail(1).index.item()} {old_df[f"{ratio}_close"][-1]}')
    '''
    seconds_from_last_update = (datetime.utcnow() - last_record_dt).total_seconds()
    # e.g. 18:00 close is like 18:59:59 so we can get 18:00 close price (UTC+0) at 18:59:59 so 19:01
    # so we can request new price after constant 2 hours passed from last record (+ few seconds just to be sure)
    # also thats why cron job is set to 1 * * * *
    seconds_remaining = timedelta(hours=2, seconds=10).seconds - seconds_from_last_update
    if seconds_remaining > 0:
        logger.warning(f'[UPDATE] No new records available yet. Try again in: {str(timedelta(seconds=seconds_remaining))}')
        return False

    # example:
    # curl -X GET "https://api.binance.com/api/v1/klines?&symbol=BTCUSDT&interval=3m"
    # https://binance-docs.github.io/apidocs/spot/en/#kline-candlestick-data
    times_repeat_download = int((-seconds_remaining // (request_records * 3600))) + 1
    new_df = pd.DataFrame(columns=[f'{ratio}_close', f'{ratio}_volume'])
    for i in range(0, times_repeat_download):
        temp_df = pd.DataFrame(columns=['date', f'{ratio}_close', f'{ratio}_volume'])
        response = get('https://api.binance.com/api/v1/klines',
                       params={'symbol': ratio,
                               'interval': '1h',
                               'startTime': last_record_unix + (i * request_records * 3600 * 1000),
                               'limit': request_records})  # last_record_unix also limits number of records, if it's recent
        raw_data = loads(response.content)
        raw_data_df = pd.DataFrame(raw_data)

        # we receive data in UTC+2 timezone, so need to set h=-2, so we pass list of [-2] as second argument
        temp_df['date'] = list(map(unix_to_datetime, raw_data_df[0], [UTC_OFFSET] * len(raw_data_df[0])))
        temp_df[f'{ratio}_close'] = list(map(float, raw_data_df[4]))  # df[4]  # Close
        temp_df[f'{ratio}_volume'] = list(map(float, raw_data_df[7]))  # df[7]  # Quote asset volume (second assets unit, so in BTC/USDT its volume_USDT)  # noqa
        temp_df.set_index("date", inplace=True)
        if i == 0:  # in first iteration we drop temp_df[0] because its the same as in old_df[-1]
            temp_df = temp_df[1:]
        new_df = pd.concat([new_df, temp_df])
    # if we send request at 15:27 (UTC-0 13:27) it will return data with last entry 13:00 which will change over time
    new_df = new_df[:-1]  # dropping that entry

    '''
    logger.debug(f'Received {len(new_df)} records.   |   '
                 f'Last: {new_df.head(1).index.item()} {new_df[f"{ratio}_close"][0]}   |   '
                 f'First: {new_df.tail(1).index.item()} {new_df[f"{ratio}_close"][-1]}')
    # python floats (and interpolation) might cause that old_df[-1] is not equal new_df[0] but thats ok,
    # e.g.: old_df[-1] is not equal new_df[0]: 0.23510999999999999 != 0.23511 but this won't be a problem
    '''

    # check for gaps in timestamps and interpolate if found
    new_df.index = pd.to_datetime(new_df.index)
    expected_range = pd.date_range(start=new_df.index.min(), end=new_df.index.max(), freq='H')

    missing_ts = list(expected_range.difference(new_df.index))
    if missing_ts and (fill_missing is True):
        new_df = new_df.resample('60min').mean()
        new_df.replace(to_replace=0, value=np.nan, inplace=True)  # converting 0s to NaNs
        new_df.interpolate(method='linear', inplace=True)  # interpolating missing NaNs

        logger.warning(f'[UPDATE] Missing {len(missing_ts)} timestamps in {ratio} pair. Performed interpolation.')

        logger.debug(f'{ratio} updated succesfully. All new records: {len(new_df)}   |   '
                     f'First: {new_df.tail(1).index.item()} {new_df[f"{ratio}_close"][-1]}\n')
        return new_df
    elif missing_ts and (fill_missing is False):
        logger.error(f'[UPDATE] Missing {len(missing_ts)} timestamps. Update skipped, check manually.')
        set_bot_config(STATUS_ACTIVE=False)
        raise Exception(f'Missing {len(missing_ts)} timestamps. Update skipped, bot set inactive.')
    else:
        return new_df


def update_all_data(fill_missing=False):
    dict_name_ratio_df = {}
    for ratio in RATIOS:
        filename = f"{DATA_PATH_ABS}Binance_{ratio}_1h.csv"
        time.sleep(0.2)  # to not spam the exchange
        # 336 hourly records = 14 days, if files havent been updated for longer time,
        # just update them again until "No new records available yet." encountered
        new_df = update_ratio(ratio, filename, request_records=336, fill_missing=fill_missing)
        dict_name_ratio_df[f'{filename}'] = new_df
        if new_df is False:  # some new_df will be False if not enough time have passed from last update
            return False

    for filename, _df in dict_name_ratio_df.items():
        _df.to_csv(filename, mode='a', header=False)
    return True


if __name__ == "__main__":
    update_all_data()
