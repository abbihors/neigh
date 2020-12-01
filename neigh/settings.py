model_path = '/Users/abbi/dev/jupyter/neigh-ml/saved_models/horse_2020.09.10-10.19.10.hdf5'
recordings_path = '/Users/abbi/dev/jupyter/neigh-ml/unprocessed_recordings'

# Minimum record volume
record_vol = 160

# Max expected volume (used to determine relative loudness)
max_expected_vol = 1600

# Seconds of silence that indicate end of speech
max_silence_s = 0.1

# Seconds of audio to save before recording (to avoid cutting the start)
prev_audio_s = 0.2

# Factor applied to all vibrate commands, use to limit max vibration strength
vibrate_factor = 0.7
