from collections import deque
import audioop
import os
import wave

import sounddevice as sd

class Recorder():

    def __init__(self, samplerate=16000, channels=1, blocksize=1000, dtype='int16'):
        # sounddevice has the option for non-raw Numpy streams, but I found these to be too slow
        self._stream = sd.RawInputStream(
            samplerate=samplerate,
            blocksize=blocksize,
            channels=channels,
            dtype=dtype
        )
        self._data = b''
    
    def get_rms_volume(self):
        """Return the RMS volume of the current recording."""
        return audioop.rms(self._data, self._stream.samplesize)

    def get_bytes(self):
        """Return recording as bytes."""
        return self._data

    def write_wav(self, path):
        """Write the current recording to path as a wave file."""
        f = wave.open(path, 'wb')

        f.setframerate(self._stream.samplerate)
        f.setnchannels(self._stream.channels)
        f.setsampwidth(self._stream.samplesize)

        f.writeframes(self._data)
        f.close()
        return

    def listen_and_record(self, record_vol, max_silence_s, prev_audio_s):
        """Listen for audio and record

        Parameters
        ----------
        record_vol : int
            Volume threshold to start recording

        max_silence_s : float
            How many seconds of silence before recording stops

        prev_audio_s : float
            Seconds of previous audio to include to avoid cutting off the start
        """

        # How many blocks represent 1 second
        blocks_per_second = self._stream.samplerate / self._stream.blocksize

        # This holds the volume averages for the last max_silence_s blocks
        volume_log = deque(maxlen=round(blocks_per_second * max_silence_s))

        # Blocks of previous audio to add to the start of recording, to avoid cutting off the start
        prev_audio_blocks = deque(maxlen=round(prev_audio_s * blocks_per_second))

        active_recording = b''
        recording_started = False

        self._stream.start()

        while True:
            current_block, overflowed = self._stream.read(frames=self._stream.blocksize)
            if(overflowed):
                print('PortAudio overflowed! Input was discarded')

            # RMS is used as a measure of "average" loudness
            rms = audioop.rms(current_block, self._stream.samplesize)
            volume_log.append(rms)

            # At least one sample in window was above recording threshold, add to active recording
            if (any([volume > record_vol for volume in volume_log])):
                if (not recording_started):
                    recording_started = True
                active_recording += current_block
            # No samples above threshold and recording_started, stop recording
            elif (recording_started == True):
                self._stream.stop()
                self._data = b''.join(prev_audio_blocks) + active_recording
                return
            # No samples above threshold and not recording_started, add previous sound
            else:
                prev_audio_blocks.append(current_block)

    def print_volume_loop(self, record_vol):
        """Monitor and print the current volume, useful for tuning recording parameters.
        
        args:
        record_vol -- whether or not to indicate when record threshold was met
        """

        self._stream.start()

        while True:
            current_data, overflowed = self._stream.read(frames=self._stream.blocksize)
            print(int(audioop.rms(current_data)))
            if (rms > record_vol):
                print('Threshold met!')

    def trim_or_pad(self, length_s):
        """Trim or pad recording to the desired length in seconds."""

        desired_length_bytes = int(length_s
            * self._stream.samplerate
            * self._stream.samplesize
            * self._stream.channels
        )

        # Pad with zero bytes
        if len(self._data) < desired_length_bytes:
            difference = desired_length_bytes - len(self._data)
            self._data += bytes(difference)

        # Trim
        self._data = self._data[:desired_length_bytes]
