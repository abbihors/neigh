import asyncio
import concurrent
import time
import random

from playsound import playsound
from tensorflow.keras.models import load_model
import librosa
import numpy as np

from recorder import Recorder
from vibrator import Vibrator
from vibrate_patterns import *
import settings

# Audio format settings
SAMPLE_RATE = 16000
FORMAT_WIDTH_IN_BYTES = 2
CHANNELS = 1

# Seconds of silence that indicate end of speech
MAX_SILENCE_S = 0.1

# Seconds of audio to save before recording (to avoid cutting the start)
PREV_AUDIO_S = 0.2

def predict_class(model, sample_bytes):
    # Keras model expects an array of floats
    sample_floats = librosa.util.buf_to_float(sample_bytes, FORMAT_WIDTH_IN_BYTES)

    mfccs = librosa.feature.mfcc(y=sample_floats, sr=SAMPLE_RATE, n_mfcc=40)
    mfccs = np.reshape(mfccs, (1, 40, 32, 1))

    prediction = (model.predict(mfccs) > 0.5).astype("int32")[0][0]

    labels = ['animal', 'other']
    return sorted(labels)[prediction]

async def vibrate_random(vibrator):
    weights = {
        pattern_basic: 7,
        pattern_burst: 1,
        pattern_burst_pulse: 1,
        pattern_burst_linger: 1
    }

    raffle = []
    for pattern, weight in weights.items():
        for i in range(weight):
            raffle.append(pattern)
    pattern = random.choice(raffle)

    await pattern(vibrator)

async def main():
    model = load_model(settings.model_path)
    vibrator = await Vibrator.create()
    recorder = Recorder(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype='int16')

    print('Neigh: Listening...')
    await vibrator.vibrate(0.2, 0.2) # Do a little vibration to confirm its working

    while True:
        # Run the recorder in a separate thread to prevent blocking everything while it runs
        loop = asyncio.get_running_loop()
        e = concurrent.futures.ThreadPoolExecutor()
        await loop.run_in_executor(e, recorder.listen_and_record, settings.record_vol, MAX_SILENCE_S, PREV_AUDIO_S)

        recorder.trim_or_pad(1.0)
        predicted_class = predict_class(model, recorder.get_bytes())
        
        if (predicted_class == 'animal'):
            await vibrate_random(vibrator)

            volume = recorder.get_rms_volume()
            print(f'Got animal sound, vol: {volume}')
            # playsound('~/dev/soundfx/quake_hitsound.mp3')
            
        # Save recordings to help improve model
        epoch_time = int(time.time())
        filename = f'{settings.recordings_path}/{predicted_class}/output_{epoch_time}.wav'
        recorder.write_wav(filename)

asyncio.run(main())
