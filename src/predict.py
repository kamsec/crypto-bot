
import numpy as np
import pandas as pd
import tflite_runtime.interpreter as tflite
from sklearn import preprocessing
from collections import deque
from src.config import RATIOS, RATIO_TO_PREDICT, SEQ_LEN, MODEL_PATH_ABS, DATA_PATH_ABS, logger

# windows: C:\Users\Admin\Desktop\python37\Scripts>pip3 install --index-url https://google-coral.gith
# rpi: tflite_runtime-2.3.1-cp37-cp37m-linux_armv6l.whl


def construct_df_for_pred(ratios):
    main_df = pd.DataFrame()
    # 'unix,date,symbol,open,high,low,close,Volume LTC,Volume USDT,tradecount'
    for ratio in ratios:
        dataset = f"{DATA_PATH_ABS}Binance_{ratio}_1h.csv"
        df = pd.read_csv(dataset, nrows=None, skiprows=None, parse_dates=['date'], usecols=[0, 1, 2])
        df.set_index("date", inplace=True)

        # later we use pct_change so we lose 1 row and need 1 more (-49 for single pred)
        # but there is no future and target column, so we dont waste one last row, so removing "+1"
        num_of_preds = 1
        short_df = df[-SEQ_LEN - num_of_preds:]

        if len(main_df) == 0:
            main_df = short_df
        else:
            main_df = main_df.join(short_df)

    # in this case it reduces main_df length to the length of pair with the smallest data
    main_df.dropna(how='any', inplace=True)
    return main_df


# percentage change and scaling
def preprocess_data_for_pred(df):
    df = df.copy()  # fixes random SettingWithCopyWarning appearing with pct_change and preprocessing.scale
    for col in df.columns:
        # here we lose 1 row
        df[col] = df[col].pct_change()  # converted to percentage change
        # example:
        # hour 1:00 close = 93.13, hour 2:00 close = 92.41, so
        # 93.13 + 93.13 * x = 92.41, x = -0.007731
        # so percentage change of 1.0 means doubling the price
        # first row (the oldest values) is being filled with NaN percentage, but we don't want to drop whole row yet
        # so we wait until loop ends (we will have whole row filled with nans)
    df.dropna(inplace=True)

    for col in df.columns:
        if col != "target":
            # scaling should be used after splitting to training and test set - leaks data from test set to training
            df[col] = preprocessing.scale(df[col].values)  # normalizes to [-1, +1]
            # df[col] = preprocessing.StandardScaler().fit_transform(df[col].values.reshape(-1, 1)) # it does the same
            # scales the data so it has mean = 0, standard deviation = 1, variance = 1
            # it can be checked before and after with e.g. print(df['BTCUSDT_close'].mean())  .std()  .var()

    # here we always will have sequential_data with one array 1x48x24
    prev_days = deque(maxlen=SEQ_LEN)  # list of SEQ_LEN items, we append to it, as it exceed, it pops old values
    sequential_data = []
    for i in df.values:
        prev_days.append([n for n in i])  # set of price and volume features added (-1 so without target)
        if len(prev_days) == SEQ_LEN:
            sequential_data.append(np.array([prev_days]))  # [] is necessary to be compatible with model input
    # the sequences are like this ([a, b, 1] is single prev_days):
    # [([[a, b] [c, d], [e, f]], 1)   ([[c, d] [e, f] [g, h]], 1) ... ([[g, h], [i, j], [k, l]], 0)]
    return sequential_data


def predict_next():
    main_df = construct_df_for_pred(RATIOS)
    preprocessed_sequences = preprocess_data_for_pred(main_df)

    interpreter = tflite.Interpreter(model_path=MODEL_PATH_ABS)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    data_for_tflite = np.array(preprocessed_sequences[0], dtype=np.float32)  # doesnt work without dtype=np.float32
    interpreter.set_tensor(input_details[0]['index'], data_for_tflite)
    interpreter.invoke()

    predictions = interpreter.get_tensor(output_details[0]['index'])
    probabilities = predictions[0]

    def classifier(prob):
        if round(prob, 2) > 0.50:
            return 'UP'
        elif round(prob, 2) == 0.50:
            # when bot is inactive it can be treated as 'EVEN' prediction as well, because it has no influence on orders
            return 'EVEN'
        elif round(prob, 2) < 0.50:
            return 'DOWN'

    prediction = classifier(probabilities[1])
    logger.info(f'[PREDICTION] DOWN: {probabilities[0]*100:.0f}%, UP: {probabilities[1]*100:.0f}%')
    return prediction


if __name__ == "__main__":
    predict_next()
