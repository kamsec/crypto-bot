import importlib
import logging
import csv
from json import dumps
from flask import Flask, render_template
from datetime import datetime, timedelta

import src.config  # also reloaded with every page refresh
from src.data_backup import get_last_commit_time
from src.utils import shift_hour_exact, UTC_OFFSET

# disabling Flask werkzeug logger because in config we use basicConfig for loggers, which is propagated to werkzeug,
# and we don't want app.run() logs in logfile.log
flask_logger = logging.getLogger("werkzeug")
flask_logger.disabled = True

app = Flask(__name__)

@app.route("/")
def generate_page():
    # all hours are given in UTC+0. Times are adjusted in process_logfile.py -> logfile.csv
    # logfile.log timestamps also are in UTC+0

    # config needs to be reloaded on every page refresh, so importing constants here
    importlib.reload(src.config)
    from src.config import CONFIG_NAME, cfg, STATUS_ACTIVE, ORDERS_ALLOWED, ENVIROMENT, LOG_FILE_ABS, MODEL_PATH, \
        STARTING_TIMESTAMP, STARTING_BALANCE_USD, STARTING_BALANCE_BTC, CURRENT_BALANCE_USD, CURRENT_BALANCE_BTC, \
        BACKUPS_ALLOWED

    # for Log textarea
    with open(LOG_FILE_ABS, 'rt') as f:
        logs_data = f.read()
        if logs_data[-1] == '\n':
            logs_data = logs_data[:-1]   # stripping ending blank line, if it's there

    # time from line '2021-08-12 16:40:49 [INFO] Bot started.'
    exact_starting_timestamp = logs_data[:19]  # '2021-08-12 16:40:49'

    def interpret_string_from_csv(x):
        if x == 'True':
            return True
        elif x == 'False':
            return False
        elif x == '':
            return None
        else:
            return x

    columns = {'date': [], 'BTCUSDT_close': [], 'future': [], 'target': [],
               'predictions_shifted': [], 'accurate_prediction': [], 'orders_shifted': [],
               'balance_USD': [], 'balance_BTC': []}
    with open('logfile.csv', 'r') as file:
        reader = csv.reader(file, delimiter=',')
        next(reader)  # skipping header
        for row in reader:
            for item, key in zip(row, columns):
                columns[key].append(interpret_string_from_csv(item))

    # accuracy from start
    accuracy_from_start = 50  # default value if no predictions were made
    num_of_true_preds = columns['accurate_prediction'].count(True)
    num_of_false_preds = columns['accurate_prediction'].count(False)  # None predictions are not counted
    if num_of_true_preds + num_of_false_preds > 0:  # prevents zero division
        accuracy_from_start = f'{(num_of_true_preds / (num_of_true_preds + num_of_false_preds) * 100):.1f}'

    # slicing last 72 hours for chart
    columns_72h = {}
    for key in columns:
        columns_72h[key] = columns[key][-72:]

    # accuracy from last 72h
    accuracy_72h = 50  # default value if no predictions were made
    num_of_true_preds_72h = columns_72h['accurate_prediction'].count(True)
    num_of_false_preds_72h = columns_72h['accurate_prediction'].count(False)  # None predictions are not counted
    if num_of_true_preds_72h + num_of_false_preds_72h > 0:  # prevents zero division
        accuracy_72h = f'{(num_of_true_preds_72h / (num_of_true_preds_72h + num_of_false_preds_72h) * 100):.1f}'

    # values directly used to plot graph
    data_values_72h = columns_72h['BTCUSDT_close']
    data_index_72h = [x[:-6] for x in columns_72h['date']]  # [:-6] makes time in format "%Y-%m-%d %H"
    predictions_72h = dumps(columns_72h['predictions_shifted'])  # also converts python None to js null
    orders_72h = dumps(columns_72h['orders_shifted'])  # also converts python None to js null

    # lifetime profit string
    profit_from_start_text = '+0 USD (0.00%)'  # default text
    # [71] because at process_logfile for current timestamp we get df with 72 hours from past
    starting_total_value_USD = STARTING_BALANCE_USD + STARTING_BALANCE_BTC * float(columns['BTCUSDT_close'][71])
    if columns['BTCUSDT_close'][-1] is not None:
        current_total_value_USD = CURRENT_BALANCE_USD + CURRENT_BALANCE_BTC * float(columns['BTCUSDT_close'][-1])
        # these are TOTAL values (USD + BTC * BTCUSD_close)
        # Profit from start. Displayed string: Runtime accuracy: 	52.8%, +1.62 USD (+1.6%)
        profit_from_start = current_total_value_USD - starting_total_value_USD
        profit_from_start_pct = ((current_total_value_USD / starting_total_value_USD) - 1) * 100
        if profit_from_start > 0:
            profit_from_start_text = f'+{profit_from_start:.2f} USD (+{profit_from_start_pct:.2f}%)'
        elif profit_from_start < 0:
            profit_from_start_text = f'{profit_from_start:.2f} USD ({profit_from_start_pct:.2f}%)'

    # 72h profit string
    _72h_profit_text = '+0 USD (0.00%)'  # default text
    # these are TOTAL values (USD + BTC * BTCUSD_close)
    # if we just started bot, all balances in columns_72h['balance_USD'] will be None, we want to avoid that
    if (columns_72h['balance_USD'][0] is not None) and (columns_72h['balance_BTC'][0] is not None):
        starting_timestamp_dt = datetime.strptime(STARTING_TIMESTAMP, '%Y-%m-%d %H:%M:%S')
        seconds_from_starting_timestamp = (datetime.utcnow() - starting_timestamp_dt).total_seconds()
        # if 72h havent passed, the profits are the same
        # +5 minutes just to be sure
        if seconds_from_starting_timestamp < timedelta(hours=72, minutes=5).total_seconds():
            _72h_profit_text = profit_from_start_text  # if 72h have not passed yet, both strings are the same
        else:
            _72h_total_value_USD = float(columns_72h['balance_USD'][0]) + float(columns_72h['balance_BTC'][0]) * float(columns_72h['BTCUSDT_close'][0])
            _72h_profit = current_total_value_USD - _72h_total_value_USD
            _72h_profit_pct = ((current_total_value_USD / _72h_total_value_USD) - 1) * 100
            if _72h_profit > 0:
                _72h_profit_text = f'+{_72h_profit:.2f} USD (+{_72h_profit_pct:.2f}%)'
            elif _72h_profit < 0:
                _72h_profit_text = f'{_72h_profit:.2f} USD ({_72h_profit_pct:.2f}%)'

    runtime_price_change_text = f'0.00% , +0.00 USD/BTC'
    runtime_price_change = float(columns['BTCUSDT_close'][-1]) - float(columns['BTCUSDT_close'][71])
    runtime_price_change_pct = (float(columns['BTCUSDT_close'][-1]) / float(columns['BTCUSDT_close'][71]) - 1) * 100
    if runtime_price_change > 0:
        runtime_price_change_text = f'+{runtime_price_change_pct:.2f}% (+{runtime_price_change:.2f} USD/BTC)'
    elif runtime_price_change < 0:
        runtime_price_change_text = f'{runtime_price_change_pct:.2f}% ({runtime_price_change:.2f} USD/BTC)'

    # conversion from booleans to displayed strings
    if STATUS_ACTIVE is True:
        STATUS_ACTIVE_text = 'Active'
    else:
        STATUS_ACTIVE_text = 'Disabled'
    if ORDERS_ALLOWED is True:
        ORDERS_ALLOWED_text = 'Allowed'
    else:
        ORDERS_ALLOWED_text = 'Disallowed'
    if BACKUPS_ALLOWED is True:
        BACKUPS_ALLOWED_text = 'Allowed'
    else:
        BACKUPS_ALLOWED_text = 'Disallowed'

    # Github backup time, shifted to UTC+0. Offset sometimes is -1 and sometimes -2, but it is returned by that command
    last_commit_time = shift_hour_exact(*get_last_commit_time())  # unpacking string timestamp and integer offset

    return render_template('index.html',
                           data_values=data_values_72h, data_index=data_index_72h,
                           predictions=predictions_72h, orders=orders_72h,
                           logs_data=logs_data,
                           exact_starting_timestamp=exact_starting_timestamp,
                           STATUS_ACTIVE_text=STATUS_ACTIVE_text,
                           ORDERS_ALLOWED_text=ORDERS_ALLOWED_text,
                           BACKUPS_ALLOWED_text=BACKUPS_ALLOWED_text,
                           ENVIROMENT=ENVIROMENT,
                           MODEL_PATH=MODEL_PATH,  # relative, just name
                           STARTING_BALANCE_USD=f'{STARTING_BALANCE_USD:.2f}',
                           STARTING_BALANCE_BTC=f'{STARTING_BALANCE_BTC:.7f}',
                           starting_total_value_USD=f'{starting_total_value_USD:.2f}',
                           CURRENT_BALANCE_USD=f'{CURRENT_BALANCE_USD:.2f}',
                           CURRENT_BALANCE_BTC=f'{CURRENT_BALANCE_BTC:.7f}',
                           current_total_value_USD=f'{current_total_value_USD:.2f}',
                           accuracy_from_start=accuracy_from_start,
                           profit_from_start_text=profit_from_start_text,
                           accuracy_72h=accuracy_72h,
                           _72h_profit_text=_72h_profit_text,
                           runtime_price_change_text=runtime_price_change_text,
                           last_commit_time=last_commit_time
                           )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)  # on RPi it's set by gunicorn, which gets app from wsgi.py
