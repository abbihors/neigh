#!/usr/bin/env python3

# ---------------------------------------------------------------------------- #
#                                   neigh.py                                   #
# ---------------------------------------------------------------------------- #

# TODO: refactor to use cleaner sound lib

from datetime import datetime
from collections import deque
import subprocess
import concurrent
from datetime import datetime
import audioop
import time
import math
import wave
import os
import sys

from tensorflow.keras.models import load_model
from playsound import playsound
import numpy as np
import librosa
import pyaudio

import asyncio
import websockets

from buttplug.client import (ButtplugClientWebsocketConnector, ButtplugClient, ButtplugClientDevice, ButtplugClientConnectorError)
from buttplug.core import ButtplugLogLevel

# --------------------------------- Constants -------------------------------- #

# Audio settings
SAMPLE_RATE = 16000
FORMAT = pyaudio.paInt16
FORMAT_WIDTH_IN_BYTES = 2
CHANNELS = 1

# Amount of frames (samples) to get each time we read data
CHUNK = 1024

# Volume threshold to begin recording
RECORD_VOL = 200

# Seconds of silence that indicate end of speech
MAX_SILENCE_S = 0.1

# Seconds of audio to save before recording (to avoid cutting the start)
PREV_AUDIO_S = 0.2

# Highest expected volume
MAX_EXPECTED_VOL = 2000

# The time period over which to measure frequency, in seconds
SPEECH_FREQUENCY_TIME_PERIOD = 60

# --------------------------------- Recording -------------------------------- #

# Returns samples of speech
def listen_and_record_speech():
    p = pyaudio.PyAudio()

    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK)

    out_speech_samples = b''
    current_data = b''
    recording_started = False

    # One second can be represented by this many chunks
    CHUNKS_PER_SECOND = SAMPLE_RATE / CHUNK

    # This sliding window will hold the average volumes of each chunk up
    # to MAX_SILENCE_S seconds in total
    sliding_window = deque(maxlen=round(MAX_SILENCE_S * CHUNKS_PER_SECOND))
    
    # Holds the chunks of previous audio
    prev_audio = deque(maxlen=round(PREV_AUDIO_S * CHUNKS_PER_SECOND))

    # While no phrase has been detected/recorded
    while True:
        current_data = stream.read(CHUNK)

        volume = audioop.rms(current_data, FORMAT_WIDTH_IN_BYTES)
        sliding_window.append(volume)

        # At least one sample in window was above recording threshold
        if (any([volume > RECORD_VOL for volume in sliding_window])):
            if (not recording_started):
                recording_started = True
            out_speech_samples = out_speech_samples + current_data
        # No samples above threshold and recording_started, stop recording
        elif (recording_started == True):
            stream.close()
            p.terminate()
            return b''.join(list(prev_audio)) + out_speech_samples
        # No samples above threshold and not recording_started, add previous sound
        else:
            prev_audio.append(current_data)

# Can be used to calibrate recording settings
def print_volume_loop():
    p = pyaudio.PyAudio()

    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK)

    while True:
        audio_data = stream.read(CHUNK)
        volume = audioop.rms(audio_data, FORMAT_WIDTH_IN_BYTES)

        if (volume > RECORD_VOL):
            print('Threshold met: ', volume)
        else:
            # print(volume)
            pass

    stream.close()
    p.terminate()

# TODO: See if there's a cleaner way to write a WAV file
def save_bytes_to_wav(data_bytes, folder):
    epoch_time = int(time.time())
    filename = f'output_{epoch_time}'

    # Make sure folder exists
    os.makedirs(folder, exist_ok=True)
    f = wave.open(f'{folder}/{filename}.wav', 'wb')
    f.setnchannels(CHANNELS)
    f.setsampwidth(FORMAT_WIDTH_IN_BYTES)
    f.setframerate(SAMPLE_RATE)
    f.writeframes(data_bytes)

    f.close()

def trim_and_pad_bytes(data_bytes, seconds):
    desired_length = int(seconds * SAMPLE_RATE * FORMAT_WIDTH_IN_BYTES * CHANNELS)

    # Pad with zero bytes
    if len(data_bytes) < desired_length:
        difference = desired_length - len(data_bytes)
        data_bytes += bytes(difference)

    # Trim
    data_bytes = data_bytes[:desired_length]

    return data_bytes

def predict_class(model, samples):
    labels = ['animal', 'other']

    mfccs = librosa.feature.mfcc(y=samples, sr=SAMPLE_RATE, n_mfcc=40)
    mfccs = np.reshape(mfccs, (1, 40, 32, 1))
    prediction_index = model.predict_classes(mfccs)[0]

    return sorted(labels)[prediction_index]

# --------------------------------- Vibration -------------------------------- #

def calculate_vibration_strength(curve, volume, recent_speech_count):
    return curve(volume, recent_speech_count)
    
def curve_linear(volume, recent_speech_count):
    return min(1.0, round(volume / MAX_EXPECTED_VOL, 2))

def curve_evil(volume, recent_speech_count):
    # Sigmoid function to make it extra evil
    vibration_strength = 1 / (1 + (math.e ** ((-volume / (MAX_EXPECTED_VOL / 10)) + 5)))

    speech_frequency = recent_speech_count / SPEECH_FREQUENCY_TIME_PERIOD

    # 20 caws per minute to get max effect = freq = 0.333
    frequency_multiplier = min(1.0, speech_frequency / (20 / SPEECH_FREQUENCY_TIME_PERIOD))

    vibration_strength = vibration_strength * (0.5 + (0.5 * frequency_multiplier))
    vibration_strength = round(vibration_strength, 2) # 2 decimal places = 100 values between 0 and 1

    return vibration_strength

# ------------------------------ Buttplug stuff ------------------------------ #

async def start_buttplug_server():
    await asyncio.create_subprocess_exec("/Users/abbi/dev/intiface-cli-rs/target/release/intiface-cli", "--wsinsecureport", "12345")
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

# ------------------------------- Main function ------------------------------ #

async def vibrate_worker(queue, bp_device):
    print('Starting vibrate worker')

    while True:
        # print(f'queue: {queue}, qsize: {queue.qsize()}')
        if queue.qsize() == 0:
            # print(f'# Stopped vibing at: {datetime.now()}')
            await bp_device.send_stop_device_cmd()
            
        vibration_strength = await queue.get()
        # print(f'# Started vibing at: {datetime.now()}')
        await bp_device.send_vibrate_cmd(vibration_strength)
        queue.task_done()
        await asyncio.sleep(1)

async def main():
    await start_buttplug_server()

    bp_client = await init_buttplug_client()
    bp_device = bp_client.devices[0] # Just get the first device

    queue = asyncio.Queue()
    asyncio.create_task(vibrate_worker(queue, bp_device))

    model = load_model('models/' + sys.argv[1])
    speech_timestamps = []

    print('Listening...')
        
    while True:
        loop = asyncio.get_running_loop()
        speech_bytes = await loop.run_in_executor(concurrent.futures.ThreadPoolExecutor(), listen_and_record_speech)
        speech_bytes = trim_and_pad_bytes(speech_bytes, 1.0) # Trim to 1 second long

        # Keras model expects an array of floats
        speech_floats = librosa.util.buf_to_float(speech_bytes, FORMAT_WIDTH_IN_BYTES)
        prediction = predict_class(model, speech_floats)

        if (prediction == 'animal'):
            volume = audioop.rms(speech_bytes, FORMAT_WIDTH_IN_BYTES)
            
            # Add timestamp
            speech_timestamps.append(datetime.now())
            
            # Remove old timestamps
            speech_timestamps = [ts for ts in speech_timestamps if (datetime.now() - ts).seconds < SPEECH_FREQUENCY_TIME_PERIOD]

            # Do fun stuff!
            vibration_strength = calculate_vibration_strength(curve_evil, volume, len(speech_timestamps))
            await queue.put(vibration_strength)
            
            print('Got caw: ', volume, vibration_strength)
            # playsound('alert_sounds/quake_hitsound.mp3')
            
        # Save every recording to help improve model
        if prediction == 'animal':
            save_bytes_to_wav(speech_bytes, './recordings/animal')
        else:
            save_bytes_to_wav(speech_bytes, './recordings/other')

# Start program
asyncio.run(main())
