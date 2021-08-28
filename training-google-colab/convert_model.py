# this file is not used by the bot or app
# it shows how to convert tensorflow model to TFlite to be suitable for Raspberry Pi
# it can be done on Google Colab and downloaded

import tensorflow as tf
from config import MODEL_PATH

# Convert the model
converter = tf.lite.TFLiteConverter.from_saved_model(MODEL_PATH)  # path to the SavedModel directory
tflite_model = converter.convert()

# Save it
with open('model2.tflite', 'wb') as f:
    print("Started writing")
    f.write(tflite_model)
    print("Finished")
