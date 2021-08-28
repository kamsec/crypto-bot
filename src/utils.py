
import time
from datetime import datetime, timedelta

# dealing with timezones and summer time
IS_DST = time.daylight and (time.localtime().tm_isdst > 0)  # daylight saving time
UTC_OFFSET = int((time.altzone if IS_DST else time.timezone) / 3600)  # PC=-2 RPi=-1, Warsaw time in summer

def unix_to_datetime(x: int, h: int = 0) -> str:  # use with h=UTC_OFFSET
    return (datetime.fromtimestamp(int(x) / 1000) + timedelta(hours=h)).strftime('%Y-%m-%d %H:%M:%S')

def datetime_to_unix(x: str, h: int = 0) -> int:  # use with h=-UTC_OFFSET
    return int(datetime.timestamp(datetime.strptime(x, '%Y-%m-%d %H:%M:%S') + timedelta(hours=h))) * 1000


def shift_hour_exact(timestamp, h):  # '2021-07-31 13:13:23', h=-1 -> '2021-07-31 12:13:23'
    return unix_to_datetime(datetime_to_unix(timestamp), h=h)

def shift_hour_trunc(timestamp, h):  # '2021-07-31 13:13:23', h=-1 -> '2021-07-31 12:00:00'
    return unix_to_datetime(datetime_to_unix(timestamp), h=h)[:-6] + ':00:00'

def shift_hour_trunc_short(timestamp, h):  # '2021-07-31 13:13:23', h=-1 -> '2021-07-31 12'
    return unix_to_datetime(datetime_to_unix(timestamp), h=h)[:-6]

