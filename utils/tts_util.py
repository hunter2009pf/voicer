import torch
from vits_tool import commons
from text import text_to_sequence, symbols, _symbol_to_id
from text_chinese import symbols_chinese, cleaned_text_to_sequence
from utils import vits_util
from models import models
from vits_chinese_tool.vits_pinyin import VITS_PinYin

# device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
# device = torch.device("cpu")


class TTSUtil:
    @staticmethod
    # this function is from vits project
    def get_text(text, hps):
        text_norm = text_to_sequence(text, hps.data.text_cleaners)
        if hps.data.add_blank:
            text_norm = commons.intersperse(text_norm, 0)
        text_norm = torch.LongTensor(text_norm)
        return text_norm

    @staticmethod
    def generate_audio_from_text(content):
        hps = vits_util.get_hparams_from_file("./configs/ljs_base.json")
        net_g = models.SynthesizerTrn(
            len(symbols),
            hps.data.filter_length // 2 + 1,
            hps.train.segment_size // hps.data.hop_length,
            **hps.model).cuda()
        _ = net_g.eval()
        _ = vits_util.load_checkpoint("./models/pretrained_ljs.pth", net_g, None)
        stn_tst = TTSUtil.get_text(content, hps)
        with torch.no_grad():
            x_tst = stn_tst.cuda().unsqueeze(0)
            x_tst_lengths = torch.LongTensor([stn_tst.size(0)]).cuda()
            audio = net_g.infer(x_tst, x_tst_lengths, noise_scale=.667, noise_scale_w=0.8, length_scale=1)[0][
                0, 0].data.cpu().float().numpy()
        return audio, hps.data.sampling_rate

    @staticmethod
    def generate_Chinese_audio_from_text(content):
        # pinyin
        tts_front = VITS_PinYin("./bert", device)

        # config
        hps = vits_util.get_hparams_from_file("./configs/bert_vits.json")

        # model
        net_g = vits_util.load_class(hps.train.eval_class)(
            len(symbols_chinese),
            hps.data.filter_length // 2 + 1,
            hps.train.segment_size // hps.data.hop_length,
            **hps.model)

        vits_util.load_model("./models/vits_bert_model.pth", net_g)
        net_g.eval()
        net_g.to(device)

        phonemes, char_embeds = tts_front.chinese_to_phonemes(content)
        input_ids = cleaned_text_to_sequence(phonemes)
        with torch.no_grad():
            x_tst = torch.LongTensor(input_ids).unsqueeze(0).to(device)
            x_tst_lengths = torch.LongTensor([len(input_ids)]).to(device)
            x_tst_prosody = torch.FloatTensor(char_embeds).unsqueeze(0).to(device)
            audio = net_g.infer(x_tst, x_tst_lengths, x_tst_prosody, noise_scale=0.5,
                                length_scale=1)[0][0, 0].data.cpu().float().numpy()
        return audio, hps.data.sampling_rate
