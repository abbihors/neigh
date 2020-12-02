import asyncio
import concurrent
import time
import random

from tensorflow.keras.models import load_model
import librosa
import numpy as np

from recorder import Recorder
from vibrator import Vibrator
from vibrate_patterns import *
import settings

def predict_class(model, sample_bytes):
    # Keras model expects an array of floats
    sample_floats = librosa.util.buf_to_float(sample_bytes, settings.format_width_in_bytes)

    mfccs = librosa.feature.mfcc(y=sample_floats, sr=settings.sample_rate, n_mfcc=40)
    mfccs = np.reshape(mfccs, (1, 40, 32, 1))

    prediction = (model.predict(mfccs) > 0.5).astype("int32")[0][0]

    labels = ['animal', 'other']
    return sorted(labels)[prediction]

# TODO: clean
saved_level = 0.0
denied = False

denial_probability = 1/40 # TODO: Put this in settings.py?
restore_probability = 1/4

async def base_vibration_task(vibrator):
    global saved_level
    global denied

    while True:
        # Don't touch vibration level while it's working
        await vibrator._vibrate_queue.join()

        # print(f'[DEBUG] vib level: {vibrator._vibration_level}, saved level: {saved_level}') # debug

        # Pleasure denial, set it to 0 randomly (u can bring it back >:)
        if not denied and saved_level > 0 and random.random() < denial_probability:
            # print('[DEBUG] denied!')
            denied = True
            await vibrator.set_level(0.0)
        elif not denied:
            old_level = saved_level
            saved_level = round(max(0, saved_level - 0.005), 3)
            if old_level != 0 and (saved_level % 0.05 == 0):
                # print('[DEBUG] decrementing vibrate')
                await vibrator.set_level(saved_level)

        await asyncio.sleep(1)

async def main():
    global saved_level
    global denied

    model = load_model(settings.model_path)
    vibrator = await Vibrator.create()
    recorder = Recorder(samplerate=settings.sample_rate, channels=settings.channels, dtype=settings.data_type)

    await vibrator.enqueue(0.2, 0.3) # Do a little vibration to confirm its working
    print('Neigh: Listening...')

    asyncio.create_task(base_vibration_task(vibrator))

    while True:
        # Run the recorder in a separate thread to prevent blocking everything while it runs
        loop = asyncio.get_running_loop()
        e = concurrent.futures.ThreadPoolExecutor()
        await loop.run_in_executor(
            e, recorder.listen_and_record, settings.record_vol, settings.max_silence_s, settings.prev_audio_s)

        recorder.trim_or_pad(1.0)
        predicted_class = predict_class(model, recorder.get_bytes())

        if (predicted_class == 'animal'):
            if denied and random.random() < restore_probability:
                # print('[DEBUG] restoring')
                denied = False
                await vibrate_random(vibrator)
                await vibrator.set_level(saved_level)
            elif not denied:
                # print('[DEBUG] normal vibrate')
                await vibrate_random(vibrator)

                saved_level = round(min(0.2, saved_level + 0.05), 3)
                await vibrator.set_level(saved_level)

        # Save recordings to help improve model
        epoch_time = int(time.time())
        filename = f'{settings.recordings_path}/{predicted_class}/output_{epoch_time}.wav'
        recorder.write_wav(filename)

asyncio.run(main())
