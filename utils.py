from datetime import datetime, timedelta



def unix_to_datetime(x, h=0):
    return (datetime.fromtimestamp(int(x) / 1000) + timedelta(hours=h)).strftime('%Y-%m-%d %H:%M:%S')

def datetime_to_unix(x, h=0):
    return int(datetime.timestamp(datetime.strptime(x, '%Y-%m-%d %H:%M:%S') + timedelta(hours=h))) * 1000
