import pyaudio
import numpy as np


class AudioUtil:
    @staticmethod
    def play_audio(audio, sample_rate):
        # Initialize PyAudio
        p = pyaudio.PyAudio()

        # Open stream for playing audio
        stream = p.open(format=pyaudio.paFloat32, channels=1, rate=sample_rate, output=True)

        # Play audio
        stream.write(audio.astype(np.float32).tobytes())

        # Close stream and PyAudio
        stream.stop_stream()
        stream.close()
        p.terminate()
