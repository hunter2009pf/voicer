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
conda config --set proxy_servers.http http://127.0.0.1:7890
conda config --set proxy_servers.https https://127.0.0.1:7890
conda config --remove-key proxy_servers.http
conda config --remove-key proxy_servers.https