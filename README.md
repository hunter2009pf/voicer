# voicer
A tool integrated with TTS, ASR and VC.  
## Supported languages
Chinese, English, German, Japanese
## monotonic_align compilation steps
```commandline
cd monotonic_align
mkdir monotonic_align
python setup.py build_ext --inplace
```
## where is downloaded model used by whisper?
Running the script the first time for a model will download that specific model; it stores (on windows) the model at C:\Users\<username>\. cache\whisper\<model> . Once downloaded, the model doesn't need to be downloaded again.
## whisper commands
```commandline
whisper japanese.wav --language Japanese
whisper japanese.wav --language Japanese --task translate
```
# whisper model local storage path
C:\Users\<user>\.cache\whisper

# check sample rate of microphone on windows10
1. Open Control Panel.
2. Select Hardware and Sound.
3. Manage Audio Devices.
4. Playback (headphones) tab.
5. Select the device to be used.
6. Click Properties.
7. Select the Advanced tab.

# set up proxy for conda
```commandline
conda config --set proxy_servers.http http://127.0.0.1:7890
conda config --set proxy_servers.https https://127.0.0.1:7890
conda config --remove-key proxy_servers.http
conda config --remove-key proxy_servers.https
```

# quickVC FAQ
1.UserWarning: stft will soon require the return_complex parameter be given for real inputs, and will further require that return_complex=True in a future PyTorch release. (Triggered internally at ..\aten\src\ATen\native\SpectralOps.cpp:639.)

solution:
Set the last parameter of stft method as False
```commandline
spec = torch.stft(y, n_fft, hop_length=hop_size, win_length=win_size, window=hann_window[str(y.device)], center=center, pad_mode='reflect', normalized=False, onesided=True,return_complex=False)
```

2.title1|test_data/3752-4944-0027.wav|test_data/p225_001.wav  
First part is the converted result, the second part is the text source and the third part is the utterance tone.

