# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import PySimpleGUI as sg
import torch
import pyaudio
import numpy as np

from utils import i18n_util, tts_util, utils
from models import models
from text.symbols import symbols
import IPython.display as ipd

# international language configuration
i18n = i18n_util.I18nUtil()
print(i18n.language_map)

# Define the window's contents
# tts subview
frame_layout = [[sg.InputText('VITS is Awesome!', key="-INPUT-", size=(750, 200), expand_y=True)],
                [sg.Button(i18n("朗读"), key="-READ-")]]
tts_layout = [[sg.Frame('My Frame Title', frame_layout, size=(750, 400), font='Any 12', title_color='blue')]]

asr_layout = [[sg.T('This is asr')]]

vc_layout = [[sg.T('This is vc')]]

main_layout = [[sg.TabGroup([[sg.Tab('tts', tts_layout), sg.Tab('asr', asr_layout), sg.Tab('vc', vc_layout)]])]]


def readTextFromInputField(content):
    if content == '':
        return
    print("text to be read is ", content)
    hps = utils.get_hparams_from_file("./configs/ljs_base.json")
    net_g = models.SynthesizerTrn(
        len(symbols),
        hps.data.filter_length // 2 + 1,
        hps.train.segment_size // hps.data.hop_length,
        **hps.model).cuda()
    _ = net_g.eval()
    _ = utils.load_checkpoint("./models/pretrained_ljs.pth", net_g, None)
    stn_tst = tts_util.get_text(content, hps)
    with torch.no_grad():
        x_tst = stn_tst.cuda().unsqueeze(0)
        x_tst_lengths = torch.LongTensor([stn_tst.size(0)]).cuda()
        audio = net_g.infer(x_tst, x_tst_lengths, noise_scale=.667, noise_scale_w=0.8, length_scale=1)[0][
            0, 0].data.cpu().float().numpy()
    # todo: how to play audio
    # ipd.display(ipd.Audio(audio, rate=hps.data.sampling_rate, normalize=False))
    # Initialize PyAudio
    p = pyaudio.PyAudio()

    # Open stream for playing audio
    stream = p.open(format=pyaudio.paFloat32, channels=1, rate=hps.data.sampling_rate, output=True)

    # Play audio
    stream.write(audio.astype(np.float32).tobytes())

    # Close stream and PyAudio
    stream.stop_stream()
    stream.close()
    p.terminate()


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
            readTextFromInputField(values["-INPUT-"])

    # Finish up by removing from the screen
    window.close()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
