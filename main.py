# This is a sample Python script.
import threading

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import PySimpleGUI as sg

from utils import i18n_util, tts_util, file_util, audio_util

# international language configuration
i18n = i18n_util.I18nUtil()
print(i18n.language_map)

# Define the window's contents
# tts subview
tts_subview = [[sg.Checkbox("", key="-CHECKBOX_TEXT-", default=True, enable_events=True), sg.Multiline('VITS is Awesome!', key="-INPUT-", expand_x=True, expand_y=True, justification='left', enable_events=True)],
               [sg.Checkbox("", key="-CHECKBOX_FILE-", default=False, enable_events=True), sg.Text("Choose a file: "), sg.Input(key="-FILE_PATH-", enable_events=True), sg.FileBrowse(file_types=(("Text Files", "*.txt"),))],
               [sg.Button(i18n("朗读"), key="-READ-", pad=(40, 0))]]

tts_layout = [[sg.Frame('Text to Speech', tts_subview, size=(750, 400), font='Any 12', title_color='blue')]]

asr_layout = [[sg.T('This is asr')]]

vc_layout = [[sg.T('This is vc')]]

main_layout = [[sg.TabGroup([[sg.Tab('tts', tts_layout), sg.Tab('asr', asr_layout), sg.Tab('vc', vc_layout)]])]]


def generate_audio_and_read(content):
    # Generate audio
    audio, sr = tts_util.TTSUtil.generate_audio_from_text(content)
    # Play audio
    audio_util.AudioUtil.play_audio(audio, sr)


def readTextFromInputField(content):
    if content == '':
        sg.popup_ok(i18n('请先输入文本'))
        return
    print("text to be read is ", content)
    # create a new thread with the function as the target and a parameter
    t = threading.Thread(target=generate_audio_and_read, args=(content,))
    # start the thread
    t.start()


def readTextFromLocalFile(file_path):
    if file_path == "" or not file_path.endswith(".txt"):
        sg.popup_ok(i18n("请先选择txt文件"))
        return
    content = file_util.FileUtil.get_text_from_file(file_path)
    if content == '':
        sg.popup_ok(i18n('请先输入文本'))
        return
    # create a new thread with the function as the target and a parameter
    t = threading.Thread(target=generate_audio_and_read, args=(content,))
    # start the thread
    t.start()


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    # Create the window
    window = sg.Window('Voicer', main_layout, size=(800, 450), resizable=True)

    # Display and interact with the Window using an Event Loop
    while True:
        event, values = window.read()
        # See if user wants to quit or window was closed
        if event == sg.WINDOW_CLOSED or event == 'Quit':
            break
        if event == "-READ-":
            if values["-CHECKBOX_TEXT-"]:
                readTextFromInputField(values["-INPUT-"])
            else:
                readTextFromLocalFile(values["-FILE_PATH-"])
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

    # Finish up by removing from the screen
    window.close()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
