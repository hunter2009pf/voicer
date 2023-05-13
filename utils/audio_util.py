import pyaudio
import numpy as np


class AudioUtil:
    stream = None
    is_running = False

    @staticmethod
    def play_audio(audio, sample_rate):
        AudioUtil.is_running = True
        p = pyaudio.PyAudio()
        # Open stream for playing audio
        AudioUtil.stream = p.open(format=pyaudio.paFloat32, channels=1, rate=sample_rate, output=True)
        print("type of audio is ", type(audio))
        audio_bytes = audio.astype(np.float32).tobytes()
        audio_length = len(audio_bytes)
        chunk_size = 1024
        # Track the position in the byte array
        position = 0
        # Play audio
        while AudioUtil.is_running and position < audio_length:
            # Calculate the remaining bytes to read
            remaining_bytes = audio_length - position

            # Determine the number of bytes to read in this iteration
            bytes_to_read = min(chunk_size, remaining_bytes)

            # Read a chunk of data from the byte array
            data = audio_bytes[position:position + bytes_to_read]

            # Write the chunk to the audio stream
            AudioUtil.stream.write(data)

            # Update the position in the byte array
            position += bytes_to_read

        # Close stream and PyAudio
        AudioUtil.stream.stop_stream()
        AudioUtil.stream.close()
        p.terminate()

    @staticmethod
    def is_playing():
        if AudioUtil.stream is None:
            return False
        else:
            return AudioUtil.stream.is_active()

    @staticmethod
    def stop_playing_audio():
        AudioUtil.is_running = False

