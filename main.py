# This is a sample Python script.
import threading

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import PySimpleGUI as sg

from utils import i18n_util, tts_util, file_util, audio_util
from enumeration import language_type

# international language configuration
i18n = i18n_util.I18nUtil()
# print(i18n.language_map)

# TTS is working or not
is_reading = False


def build_gui():
    tts_text_in_English = 'VITS is Awesome!'
    tts_text_in_Chinese = '遥望星空作文独自坐在乡间的小丘上，看着阳光渐渐变暗，听着鸟鸣渐渐变弱，触着清风渐渐变凉。'

    # Define the window's contents
    # tts subview
    tts_subview = [[sg.Checkbox("", key="-CHECKBOX_TEXT-", default=True, enable_events=True),
                    sg.Multiline(tts_text_in_Chinese, key="-INPUT-", expand_x=True, expand_y=True, justification='left',
                                 enable_events=True)],
                   [sg.Checkbox("", key="-CHECKBOX_FILE-", default=False, enable_events=True),
                    sg.Text("Choose a file: "), sg.Input(key="-FILE_PATH-", enable_events=True),
                    sg.FileBrowse(file_types=(("Text Files", "*.txt"),))],
                   [sg.Button(i18n("朗读"), key="-READ-", pad=(40, 0), button_color=('black', 'white')),
                    sg.Checkbox(i18n("英语"), key="-CHECKBOX_ENGLISH-", default=True, enable_events=True, pad=(40, 0)),
                    sg.Checkbox(i18n("中文"), key="-CHECKBOX_CHINESE-", default=False, enable_events=True)]]

    tts_layout = [[sg.Frame('Text to Speech', tts_subview, size=(750, 400), font='Any 12', title_color='blue')]]

    asr_layout = [[sg.T('This is asr')]]

    vc_layout = [[sg.T('This is vc')]]

    main_layout = [[sg.TabGroup([[sg.Tab('tts', tts_layout), sg.Tab('asr', asr_layout), sg.Tab('vc', vc_layout)]])]]
    return main_layout


def change_gui_when_starting_reading():
    global is_reading
    is_reading = True
    # update UI of read button
    window["-READ-"].update(text=i18n("停止"), button_color=('white', 'red'))


def change_gui_when_finishing_reading():
    global is_reading
    is_reading = False
    # update UI of read button
    window["-READ-"].update(text=i18n("朗读"), button_color=('black', 'white'))


def generate_English_audio_and_read(content):
    global is_reading
    # Generate audio
    audio, sr = tts_util.TTSUtil.generate_audio_from_text(content)
    if not is_reading:
        return
    # Play audio
    audio_util.AudioUtil.play_audio(audio, sr)
    # reset UI of read button
    change_gui_when_finishing_reading()


def generate_Chinese_audio_and_read(content):
    global is_reading
    # Generate audio
    audio, sr = tts_util.TTSUtil.generate_Chinese_audio_from_text(content)
    if not is_reading:
        return
    # Play audio
    audio_util.AudioUtil.play_audio(audio, sr)
    # reset UI of read button
    change_gui_when_finishing_reading()


def readTextFromInputField(content, language):
    if content == '':
        sg.popup_ok(i18n('请先输入文本'))
        return
    change_gui_when_starting_reading()
    print(language == language_type.LanguageType.ENGLISH)
    print("text to be read is ", content)
    if language == language_type.LanguageType.ENGLISH:
        # create a new thread with the function as the target and a parameter
        t = threading.Thread(target=generate_English_audio_and_read, args=(content,))
        # start the thread
        t.start()
    elif language == language_type.LanguageType.CHINESE:
        # create a new thread with the function as the target and a parameter
        t = threading.Thread(target=generate_Chinese_audio_and_read, args=(content,))
        # start the thread
        t.start()
    else:
        change_gui_when_finishing_reading()


def readTextFromLocalFile(file_path, language):
    if file_path == "" or not file_path.endswith(".txt"):
        sg.popup_ok(i18n("请先选择txt文件"))
        return
    content = file_util.FileUtil.get_text_from_file(file_path)
    if content == '':
        sg.popup_ok(i18n('请先输入文本'))
        return
    change_gui_when_starting_reading()
    if language == language_type.LanguageType.ENGLISH:
        # create a new thread with the function as the target and a parameter
        t = threading.Thread(target=generate_English_audio_and_read, args=(content,))
        # start the thread
        t.start()
    elif language == language_type.LanguageType.CHINESE:
        # create a new thread with the function as the target and a parameter
        t = threading.Thread(target=generate_Chinese_audio_and_read, args=(content,))
        # start the thread
        t.start()
    else:
        change_gui_when_finishing_reading()


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    # Create the window
    window = sg.Window('Voicer', build_gui(), size=(800, 450), resizable=True)

    # Display and interact with the Window using an Event Loop
    while True:
        event, values = window.read()
        # See if user wants to quit or window was closed
        if event == sg.WINDOW_CLOSED or event == 'Quit':
            break
        if event == "-READ-":
            if is_reading:
                # stop playing audio if audio is being played now
                audio_util.AudioUtil.stop_playing_audio()
                # reset UI of read button
                change_gui_when_finishing_reading()
            else:
                # text in English to speech
                lang = None
                if values["-CHECKBOX_ENGLISH-"]:
                    lang = language_type.LanguageType.ENGLISH
                elif values["-CHECKBOX_CHINESE-"]:
                    lang = language_type.LanguageType.CHINESE
                if lang is None:
                    continue
                if values["-CHECKBOX_TEXT-"]:
                    readTextFromInputField(values["-INPUT-"], lang)
                else:
                    readTextFromLocalFile(values["-FILE_PATH-"], lang)
        elif event == "-CHECKBOX_TEXT-":
            if values["-CHECKBOX_TEXT-"]:
                window["-CHECKBOX_FILE-"].update(value=False)
            else:
                window["-CHECKBOX_FILE-"].update(value=True)
        elif event == "-CHECKBOX_FILE-":
            if values["-CHECKBOX_FILE-"]:
                window["-CHECKBOX_TEXT-"].update(value=False)
            else:
                window["-CHECKBOX_TEXT-"].update(value=True)
        elif event == "-INPUT-":
            # after operation on MULTILINE widget, if the content of MULTILINE is not empty and CHECKBOX_TEXT is not
            # ticked, just tick it
            if values["-INPUT-"] != "" and not values["-CHECKBOX_TEXT-"]:
                window["-CHECKBOX_TEXT-"].update(value=True)
                window["-CHECKBOX_FILE-"].update(value=False)
        elif event == "-FILE_PATH-":
            print("file path is ", values["-FILE_PATH-"])
            if values["-FILE_PATH-"] != "" and not values["-CHECKBOX_FILE-"]:
                window["-CHECKBOX_FILE-"].update(value=True)
                window["-CHECKBOX_TEXT-"].update(value=False)
        elif event == "-CHECKBOX_ENGLISH-":
            window["-CHECKBOX_ENGLISH-"].update(value=True)
            window["-CHECKBOX_CHINESE-"].update(value=False)
        elif event == "-CHECKBOX_CHINESE-":
            window["-CHECKBOX_ENGLISH-"].update(value=False)
            window["-CHECKBOX_CHINESE-"].update(value=True)

    # Finish up by removing from the screen
    window.close()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
