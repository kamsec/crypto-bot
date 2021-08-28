# this file is not used by the bot or app

import numpy as np
import pandas as pd
from sklearn import preprocessing
from collections import deque
from src.config import RATIOS, RATIO_TO_PREDICT, SEQ_LEN, MODEL_PATH_ABS, DATA_PATH_ABS, logger
import tflite_runtime.interpreter as tflite
# windows: C:\Users\Admin\Desktop\python37\Scripts>pip3 install --index-url https://google-coral.gith
# rpi: tflite_runtime-2.3.1-cp37-cp37m-linux_armv6l.whl

pd.set_option('display.max_columns', None)
pd.set_option('display.expand_frame_repr', False)

# simulation removes the latest record from data,
# because in this case its not possible to verify real price and "target"

NUM_OF_PREDS = 1000  # tu inaczej niz w single prediction
FUTURE_PERIOD_PREDICT = 1

def construct_df_for_multiple_pred(ratios):
    main_df = pd.DataFrame()
    # 'unix,date,symbol,open,high,low,close,Volume LTC,Volume USDT,tradecount'
    for ratio in ratios:
        # drive_path = 'drive/MyDrive/Colab Notebooks/crypto_prediction/model3/data/'
        dataset = f"{DATA_PATH_ABS}Binance_{ratio}_1h.csv"
        df = pd.read_csv(dataset, nrows=None, skiprows=None, parse_dates=['date'], usecols=[0, 1, 2])
        df.set_index("date", inplace=True)

        # later we use pct_change so we lose 1 row and need 1 more (-49 for single pred)
        # "+ 1" is because the newest row is removed cause target would be NAN, so
        # "+ 1" has to be here for training, and cant be here for prediction
        # but "+ 1" has to be here for simulation of multiple predictions
        short_df = df[-(SEQ_LEN + 1) - NUM_OF_PREDS:]

        if len(main_df) == 0:
            main_df = short_df
        else:
            main_df = main_df.join(short_df)

    # in this case it reduces main_df length to the length of pair with the smallest data
    main_df.dropna(how='any', inplace=True)

    def classify(current, future):
        if float(future) > float(current):
            return 1
        else:
            return 0
    # we determine targets by making ['future'] column with shifted rows,
    # and then if its price is higher than current day setting ['target'] to 1, and 0 otherwise
    main_df['future'] = main_df[f"{RATIO_TO_PREDICT}_close"].shift(-FUTURE_PERIOD_PREDICT)
    main_df.dropna(how='any', inplace=True)  # todo check if it shouldnt be replaced everywhere
    main_df['target'] = list(map(classify, main_df[f"{RATIO_TO_PREDICT}_close"], main_df["future"]))
    main_df.drop('future', 1, inplace=True)  # future column is no longer needed, used only to determine target column
    # rows with future = NaN also are dropped here

    return main_df


# percentage change and scaling
def preprocess_data_for_pred(df):
    df = df.copy()  # fixes random SettingWithCopyWarning appearing with pct_change and preprocessing.scale
    for col in df.columns:
        # todo here we lose 1 row
        df[col] = df[col].pct_change()  # converted to percentage change
        # example:
        # hour 1:00 close = 93.13, hour 2:00 close = 92.41, so
        # 93.13 + 93.13 * x = 92.41, x = -0.007731
        # so percentage change of 1.0 means doubling the price
        # first row (the oldest values) is being filled with NaN percentage, but we don't want to drop whole row yet
        # so we wait until loop ends (we will have whole row filled with nans)
    df.dropna(inplace=True)
    # print('b', df.shape, df.isnull().values.any())
    for col in df.columns:
        if col != "target":
            # scaling should be used after splitting to training and test set - leaks data from test set to training
            df[col] = preprocessing.scale(df[col].values)  # normalizes to [-1, +1]
            # df[col] = preprocessing.StandardScaler().fit_transform(df[col].values.reshape(-1, 1)) # it does the same
            # scales the data so it has mean = 0, standard deviation = 1, variance = 1
            # it can be checked before and after with e.g. print(df['BTCUSDT_close'].mean())  .std()  .var()

    prev_days = deque(maxlen=SEQ_LEN)  # list of SEQ_LEN items, we append to it, as it exceed, it pops old values
    sequential_data = []
    for i in df.values:
        prev_days.append([n for n in i])  # set of price and volume features added (-1 so without target)
        if len(prev_days) == SEQ_LEN:
            sequential_data.append(np.array([prev_days]))
    # print(len(sequential_data))
    # ok so the sequences are like this ([a, b, 1] is single prev_days) (* and ^ just to point where it goes):
    # [([[a, b] [c, d], [e, f]], 1*)   ([[c, d] [e, f] [g, h]], 1) ... ([[g, h], [i, j], [k, l]], 0^)]

    return sequential_data


balance_USD = float(100)
balance_BTC = float(0)
order_counter = 0
fee = 0.001
def simulation():
    main_df = construct_df_for_multiple_pred(RATIOS)
    real_y = main_df['target'][SEQ_LEN:]
    main_df.drop('target', 1, inplace=True)
    print(main_df.shape)

    predict_x = preprocess_data_for_pred(main_df)
    print(predict_x[0].shape)

    def classifier(prob):
        return 1 if prob > 0.5 else 0

    predictions = []
    interpreter = tflite.Interpreter(model_path=MODEL_PATH_ABS)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    for x, y in zip(predict_x, real_y.values):
        data_for_tflite = np.array(x, dtype=np.float32)
        interpreter.set_tensor(input_details[0]['index'], data_for_tflite)
        interpreter.invoke()
        predict_y = interpreter.get_tensor(output_details[0]['index'])
        predictions.append(classifier(predict_y[0][1]))

    predictions = np.array(predictions)
    real_y = np.array(real_y.values)
    print(f'pred 0s: {(predictions == 0).sum()}, 1s: {(predictions == 1).sum()}')
    print(f'real 0s: {(real_y == 0).sum()}, 1s: {(real_y == 1).sum()}')
    print(f'accuracy: {np.mean(predictions == real_y)}')

    # zakres [Number
    real_BTC_prices = main_df['BTCUSDT_close'][SEQ_LEN:].values.tolist()
    predictions = predictions.tolist()
    global balance_USD
    global balance_BTC
    global order_counter

    def buy_BTC(money, USD_BTC_price):
        global balance_USD
        global order_counter
        balance_USD = 0
        order_counter += 1
        print(f'ORDER: {order_counter} | HOUR {i}: Bought {money / USD_BTC_price}BTC for {money}USD at the price of {USD_BTC_price}USD/BTC')
        return money / USD_BTC_price - fee * (money / USD_BTC_price)

    def sell_BTC(money, USD_BTC_price):
        global balance_BTC
        global order_counter
        balance_BTC = 0
        order_counter += 1
        print(f'ORDER: {order_counter} | HOUR {i}: Sold {money}BTC for {money * USD_BTC_price}USD at the price of {USD_BTC_price}USD/BTC')
        return money * USD_BTC_price - fee * (money * USD_BTC_price)

    last_buy_price = 0
    print(f'Start balance_BTC: {balance_BTC}')
    print(f'Start balance_USD: {balance_USD}')
    for i in range(1, len(real_BTC_prices)):  # todo removed -2 here, check again if everything is correct
        if (balance_USD > 0) and (predictions[i] == 1):
            balance_BTC = buy_BTC(balance_USD, real_BTC_prices[i])
            continue
        # if (balance_BTC > 0) and (real_BTC_prices[i] > real_BTC_prices[i - 1]) and predictions[i] == 0:
        if (balance_BTC > 0) and (predictions[i] == 0):
            balance_USD = sell_BTC(balance_BTC, real_BTC_prices[i])
        # elif (balance_BTC > 0) and (real_BTC_prices[i] > real_BTC_prices[i - 1]) and predictions[i] == 1:
        elif (balance_BTC > 0) and predictions[i] == 1:
            continue

    if balance_BTC > 0:
        balance_USD = sell_BTC(balance_BTC, real_BTC_prices[-1])
    print(f'Final balance_BTC: {balance_BTC}')
    print(f'Final balance_USD: {balance_USD}')


if __name__ == "__main__":
    simulation()