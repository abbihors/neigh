from collections import deque
from datetime import datetime
import asyncio
import audioop
import json
import math
import os
import concurrent
import subprocess
import sys
import time
import wave

from buttplug.client import ButtplugClient
from buttplug.client import ButtplugClientWebsocketConnector
from playsound import playsound
from tensorflow.keras.models import load_model
import librosa
import numpy as np

from recorder import Recorder
import settings

# --------------------------------- Constants -------------------------------- #

# Audio format settings
SAMPLE_RATE = 16000
FORMAT_WIDTH_IN_BYTES = 2
CHANNELS = 1

# Seconds of silence that indicate end of speech
MAX_SILENCE_S = 0.1

# Seconds of audio to save before recording (to avoid cutting the start)
PREV_AUDIO_S = 0.2

# The time period over which to measure frequency, in seconds
# TODO: Clean this up, this makes no sense
SPEECH_FREQUENCY_SAMPLING_INTERVAL = 60

# --------------------------------- Vibration -------------------------------- #

def calculate_vibration_strength(curve, volume, recent_speech_count):
    return curve(volume, recent_speech_count)
    
def curve_linear(volume, recent_speech_count):
    return min(1.0, round(volume / settings.max_expected_vol, 2))

def curve_evil(volume, recent_speech_count):
    buildup_count = settings.buildup_count
    max_expected_vol = settings.max_expected_vol

    # Sigmoid function to make it extra evil
    vibration_strength = 1 / (1 + (math.e ** ((-volume / (max_expected_vol / 10)) + 5)))

    speech_frequency = recent_speech_count / SPEECH_FREQUENCY_SAMPLING_INTERVAL

    # 20 caws per minute to get max effect = freq = 0.333
    frequency_multiplier = min(1.0,
        speech_frequency /
            (buildup_count / SPEECH_FREQUENCY_SAMPLING_INTERVAL))

    vibration_strength = vibration_strength * (0.5 + (0.5 * frequency_multiplier))
    vibration_strength = round(vibration_strength, 2) # 2 decimal places = 100 values between 0 and 1

    return vibration_strength

# ------------------------------ Buttplug stuff ------------------------------ #

async def start_buttplug_server():
    await asyncio.create_subprocess_exec(settings.server_path, "--wsinsecureport", "12345")
    await asyncio.sleep(1) # Wait for the server to start up
    print('Buttplug server started')

async def init_buttplug_client():
    client = ButtplugClient("Neigh")
    connector = ButtplugClientWebsocketConnector("ws://127.0.0.1:12345")

    await client.connect(connector)
    await client.start_scanning()

    # Wait until we get a device
    while client.devices == {}:
        await asyncio.sleep(1)

    await client.stop_scanning()

    return client

# ----------------------------------- Misc ----------------------------------- #

def predict_class(model, sample_bytes):
    # Keras model expects an array of floats
    sample_floats = librosa.util.buf_to_float(sample_bytes, FORMAT_WIDTH_IN_BYTES)

    mfccs = librosa.feature.mfcc(y=sample_floats, sr=SAMPLE_RATE, n_mfcc=40)
    mfccs = np.reshape(mfccs, (1, 40, 32, 1))

    prediction = (model.predict(mfccs) > 0.5).astype("int32")[0][0]

    labels = ['animal', 'other']
    return sorted(labels)[prediction]

# This runs in the background and waits for things to be put in the queue
async def vibrate_worker(queue, bp_device):
    while True:
        vibration_strength = await queue.get()

        vibration_strength = max(0.1, vibration_strength)
        await bp_device.send_vibrate_cmd(vibration_strength)
        queue.task_done()
        await asyncio.sleep(1)
        await bp_device.send_stop_device_cmd()

# ------------------------------- Main function ------------------------------ #

async def main():
    await start_buttplug_server()

    bp_client = await init_buttplug_client()
    bp_device = bp_client.devices[0] # Just get the first device

    queue = asyncio.Queue()
    asyncio.create_task(vibrate_worker(queue, bp_device))

    model = load_model(settings.model_path)
    speech_timestamps = []

    recorder = Recorder(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype='int16')

    print('Neigh: Listening...')

    while True:
        # Run the recorder in a separate thread to prevent blocking everything while it runs
        loop = asyncio.get_running_loop()
        e = concurrent.futures.ThreadPoolExecutor()
        await loop.run_in_executor(e, recorder.listen_and_record, settings.record_vol, MAX_SILENCE_S, PREV_AUDIO_S)

        recorder.trim_or_pad(1.0)
        predicted_class = predict_class(model, recorder.get_bytes())

        if (predicted_class == 'animal'):
            volume = recorder.get_rms_volume()
            
            # Add timestamp
            speech_timestamps.append(datetime.now())
            
            # Remove old timestamps
            speech_timestamps = [ts for ts in speech_timestamps
                if (datetime.now() - ts).seconds < SPEECH_FREQUENCY_SAMPLING_INTERVAL]

            # Do fun stuff!
            vibration_strength = calculate_vibration_strength(curve_evil, volume, len(speech_timestamps))
            await queue.put(vibration_strength)
            
            print(f'Got animal sound, vol: {volume}, vibe: {vibration_strength}')
            # playsound('~/dev/soundfx/quake_hitsound.mp3')
            
        # Save recordings to help improve model
        epoch_time = int(time.time())
        filename = f'{settings.recordings_path}/{predicted_class}/output_{epoch_time}.wav'
        recorder.write_wav(filename)

# Start program
asyncio.run(main())
