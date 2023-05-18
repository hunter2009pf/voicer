import os
import threading
import time

import PySimpleGUI as sg
import pyaudio
import wave

import whisper

from utils import i18n_util, file_util
from constants import constants

# international language configuration
i18n = i18n_util.I18nUtil()


class ASRPage:
    FORMAT = pyaudio.paInt16
    output_file_path = ""
    SAMPLE_RATE = 44100
    CHANNELS = 2
    CHUNK = 1024
    audio_stream = None
    audio = None
    output_file = None
    is_recording = False
    window = None
    loading_dialog = None
    is_transcribing = False

    @staticmethod
    def stop_recording_audio():
        # Stop audio recording
        ASRPage.audio_stream.stop_stream()
        ASRPage.audio_stream.close()
        ASRPage.audio.terminate()
        ASRPage.output_file.close()

    @staticmethod
    def write_data_to_file():
        # Start recording
        while ASRPage.is_recording:
            data = ASRPage.audio_stream.read(ASRPage.CHUNK)
            if len(data) > 0:
                ASRPage.output_file.writeframes(data)
            else:
                break
        ASRPage.stop_recording_audio()
        # update file path in input widget
        ASRPage.window["-ASR_FILE_PATH-"].update(value=ASRPage.output_file_path)

    @staticmethod
    def build_asr_gui():
        # radio buttons, offline or online work
        label_work_mode = sg.Text(i18n("工作模式"))
        radio_online = sg.Radio(i18n("在线"), "work_mode", key='-ONLINE-')
        radio_offline = sg.Radio(i18n("离线"), "work_mode", key='-OFFLINE-', default=True)
        # record audio from microphone then transcribe it
        label_record = sg.Text(i18n("录音"), font=("Helvetica", 20), justification="center")
        btn_record = sg.Button(i18n("录音"), key="-RECORD-", button_color=('black', 'white'))
        # load a local audio file and transcribe it
        label_choose_file = sg.Text(i18n("选择本地文件："))
        input_file_path = sg.Input(key="-ASR_FILE_PATH-", enable_events=True)
        browse_audio_file = sg.FileBrowse(file_types=(("Audio Files", "*.wav *.mp3 *.flac *.aac *.pcm"),))
        # language choices
        label_language = sg.Text(i18n("音频所讲的语言："))
        combo_language = sg.Combo(
            default_value="Chinese",
            values=["Chinese", "English", "German", "Japanese"],
            key='-AUDIO_LANGUAGE-', size=(30, 6))
        # start transcribing audio
        button_asr = sg.Button(i18n("语音转文本"), key="-AUDIO_TO_TEXT-", button_color=('black', 'white'))
        # text widget to show asr result
        label_text_result = sg.Multiline("", key="-TEXT_RESULT-", expand_y=True, expand_x=True, background_color="white", text_color="black")
        asr_layout = [[label_work_mode, radio_online, radio_offline],
                      [label_record, btn_record],
                      [label_choose_file, input_file_path, browse_audio_file],
                      [label_language, combo_language],
                      [button_asr],
                      [label_text_result]]
        return asr_layout

    @staticmethod
    def popup(message):
        sg.theme('DarkGrey')
        layout = [[sg.Text(message)]]
        win = sg.Window('Message', layout, no_titlebar=True, keep_on_top=True, finalize=True)
        return win

    @staticmethod
    def build_loading_dialog():
        # disable the window and exhibit loading icon
        ASRPage.window.Disable()  # Disable the entire window
        ASRPage.loading_dialog = ASRPage.popup(i18n("正在处理..."))

    @staticmethod
    def start_transcribing_audio_to_text():
        # model = whisper.load_model("base")
        model = whisper.load_model("small")
        result = model.transcribe(ASRPage.output_file_path)
        ASRPage.window["-TEXT_RESULT-"].update(value=result["text"])

        # # detect language and transcribe audio
        # model = whisper.load_model("base")
        #
        # # load audio and pad/trim it to fit 30 seconds
        # audio = whisper.load_audio(ASRPage.output_file_path)
        # audio = whisper.pad_or_trim(audio)
        #
        # # make log-Mel spectrogram and move to the same device as the model
        # mel = whisper.log_mel_spectrogram(audio).to(model.device)
        #
        # # detect the spoken language
        # _, probs = model.detect_language(mel)
        # print(f"Detected language: {max(probs, key=probs.get)}")
        #
        # # decode the audio
        # options = whisper.DecodingOptions()
        # result = whisper.decode(model, mel, options)
        #
        # # print the recognized text
        # print("TEXT: ", result.text)
        ASRPage.is_transcribing = False
        ASRPage.window.Enable()
        ASRPage.loading_dialog.close()
        ASRPage.loading_dialog = None

    @staticmethod
    def handle_event(window, event, values):
        ASRPage.window = window
        if event == "-RECORD-":
            # Start recording
            if ASRPage.is_recording:
                ASRPage.is_recording = False
                window["-RECORD-"].update(text=i18n("录音"), button_color=('black', 'white'))
                # sf.write(ASRPage.output_file_path, ASRPage.recording, ASRPage.SAMPLE_RATE)
            else:
                ASRPage.is_recording = True
                window["-RECORD-"].update(text=i18n("停止"), button_color=('white', 'red'))
                # Generate empty file for saving audio
                current_time_ms = int(time.time() * 1000)
                file_name = constants.ASR_AUDIO_RECORDING_PREFIX + str(
                    current_time_ms) + constants.ASR_AUDIO_RECORDING_EXTENSION
                ASRPage.output_file_path = os.path.join(file_util.FileUtil.get_asr_storage_dir(), file_name)
                # Start audio recording
                # Create PyAudio object
                ASRPage.audio = pyaudio.PyAudio()

                # Open audio stream
                ASRPage.audio_stream = ASRPage.audio.open(format=ASRPage.FORMAT,
                                                          channels=ASRPage.CHANNELS,
                                                          rate=ASRPage.SAMPLE_RATE,
                                                          input=True,
                                                          frames_per_buffer=ASRPage.CHUNK)

                # Open output file for writing
                ASRPage.output_file = wave.open(ASRPage.output_file_path, "wb")
                ASRPage.output_file.setnchannels(ASRPage.CHANNELS)
                ASRPage.output_file.setsampwidth(ASRPage.audio.get_sample_size(ASRPage.FORMAT))
                ASRPage.output_file.setframerate(ASRPage.SAMPLE_RATE)

                # create a new thread with the function as the target and a parameter
                t = threading.Thread(target=ASRPage.write_data_to_file)
                # start the thread
                t.start()
        elif event == "-ASR_FILE_PATH-":
            ASRPage.output_file_path = values["-ASR_FILE_PATH-"]
        elif event == "-AUDIO_TO_TEXT-":
            if ASRPage.is_transcribing:
                ASRPage.is_transcribing = False
            else:
                if ASRPage.output_file_path == "":
                    sg.popup_ok(i18n('请先录音或选择音频文件'))
                    return
                if not os.path.exists(ASRPage.output_file_path):
                    sg.popup_ok(i18n('音频文件不存在'))
                    return
                ASRPage.is_transcribing = True
                # create a new thread with the function as the target and a parameter
                t = threading.Thread(target=ASRPage.start_transcribing_audio_to_text)
                # start the thread
                t.start()
                ASRPage.build_loading_dialog()


