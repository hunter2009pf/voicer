import os, sys

# 把当前文件夹路径写入环境变量
now_dir = os.getcwd()
sys.path.append(now_dir)
import PySimpleGUI as sg
import sounddevice as sd
import noisereduce as nr
import numpy as np
from fairseq import checkpoint_utils
import faiss, librosa, torch, parselmouth, time, threading
import torch.nn.functional as F
import torchaudio.transforms as tat

# import matplotlib.pyplot as plt
from rvc_tool.infer_pack.models import SynthesizerTrnMs256NSFsid, SynthesizerTrnMs256NSFsid_nono
from utils import i18n_util

# international language configuration
i18n = i18n_util.I18nUtil()
# 有GPU优先使用GPU，没有则使用CPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class RVC:
    def __init__(
            self, key, hubert_path, pth_path, index_path, npy_path, index_rate
    ) -> None:
        """
        初始化
        """
        self.f0_up_key = key
        self.time_step = 160 / 16000 * 1000
        # 基频的范围
        self.f0_min = 50
        self.f0_max = 1100
        # 频率上下限转梅尔频谱上下限，np.log默认对数底是e
        # 如果对数底换成10，则1127换成2595
        self.f0_mel_min = 1127 * np.log(1 + self.f0_min / 700)
        self.f0_mel_max = 1127 * np.log(1 + self.f0_max / 700)
        # 加载索引实现快速相似向量搜索
        self.index = faiss.read_index(index_path)
        self.index_rate = index_rate
        """NOT YET USED"""
        self.big_npy = np.load(npy_path)
        model_path = hubert_path
        print("load model(s) from {}".format(model_path))
        models, saved_cfg, task = checkpoint_utils.load_model_ensemble_and_task(
            [model_path],
            suffix="",
        )
        self.model = models[0]
        self.model = self.model.to(device)
        self.model = self.model.half()
        self.model.eval()
        cpt = torch.load(pth_path, map_location="cpu")
        tgt_sr = cpt["config"][-1]
        cpt["config"][-3] = cpt["weight"]["emb_g.weight"].shape[0]  # n_spk
        if_f0 = cpt.get("f0", 1)
        if if_f0 == 1:
            self.net_g = SynthesizerTrnMs256NSFsid(*cpt["config"], is_half=True)
        else:
            self.net_g = SynthesizerTrnMs256NSFsid_nono(*cpt["config"])
        del self.net_g.enc_q
        print(self.net_g.load_state_dict(cpt["weight"], strict=False))
        self.net_g.eval().to(device)
        self.net_g.half()

    def get_f0_coarse(self, f0):
        f0_mel = 1127 * np.log(1 + f0 / 700)
        f0_mel[f0_mel > 0] = (f0_mel[f0_mel > 0] - self.f0_mel_min) * 254 / (
                self.f0_mel_max - self.f0_mel_min
        ) + 1
        f0_mel[f0_mel <= 1] = 1
        f0_mel[f0_mel > 255] = 255
        # f0_mel[f0_mel > 188] = 188
        f0_coarse = np.rint(f0_mel).astype(np.int)
        return f0_coarse

    def get_f0(self, x, p_len, f0_up_key=0):
        f0 = (
            parselmouth.Sound(x, 16000)
            .to_pitch_ac(
                time_step=self.time_step / 1000,
                voicing_threshold=0.6,
                pitch_floor=self.f0_min,
                pitch_ceiling=self.f0_max,
            )
            .selected_array["frequency"]
        )

        pad_size = (p_len - len(f0) + 1) // 2
        if pad_size > 0 or p_len - len(f0) - pad_size > 0:
            f0 = np.pad(f0, [[pad_size, p_len - len(f0) - pad_size]], mode="constant")
        f0 *= pow(2, f0_up_key / 12)
        # f0=suofang(f0)
        f0bak = f0.copy()
        f0_coarse = self.get_f0_coarse(f0)
        return f0_coarse, f0bak

    def infer(self, feats: torch.Tensor) -> np.ndarray:
        """
        推理函数
        """
        audio = feats.clone().cpu().numpy()
        assert feats.dim() == 1, feats.dim()
        feats = feats.view(1, -1)
        padding_mask = torch.BoolTensor(feats.shape).fill_(False)
        inputs = {
            "source": feats.half().to(device),
            "padding_mask": padding_mask.to(device),
            "output_layer": 9,  # layer 9
        }
        torch.cuda.synchronize()
        with torch.no_grad():
            logits = self.model.extract_features(**inputs)
            feats = self.model.final_proj(logits[0])

        ####索引优化
        if (
                isinstance(self.index, type(None)) == False
                and isinstance(self.big_npy, type(None)) == False
                and self.index_rate != 0
        ):
            npy = feats[0].cpu().numpy().astype("float32")
            _, I = self.index.search(npy, 1)
            npy = self.big_npy[I.squeeze()].astype("float16")
            feats = (
                    torch.from_numpy(npy).unsqueeze(0).to(device) * self.index_rate
                    + (1 - self.index_rate) * feats
            )

        feats = F.interpolate(feats.permute(0, 2, 1), scale_factor=2).permute(0, 2, 1)
        torch.cuda.synchronize()
        # p_len = min(feats.shape[1],10000,pitch.shape[0])#太大了爆显存
        p_len = min(feats.shape[1], 12000)  #
        print(feats.shape)
        pitch, pitchf = self.get_f0(audio, p_len, self.f0_up_key)
        p_len = min(feats.shape[1], 12000, pitch.shape[0])  # 太大了爆显存
        torch.cuda.synchronize()
        # print(feats.shape,pitch.shape)
        feats = feats[:, :p_len, :]
        pitch = pitch[:p_len]
        pitchf = pitchf[:p_len]
        p_len = torch.LongTensor([p_len]).to(device)
        pitch = torch.LongTensor(pitch).unsqueeze(0).to(device)
        pitchf = torch.FloatTensor(pitchf).unsqueeze(0).to(device)
        ii = 0  # sid
        sid = torch.LongTensor([ii]).to(device)
        with torch.no_grad():
            infered_audio = (
                self.net_g.infer(feats, p_len, pitch, pitchf, sid)[0][0, 0]
                .data.cpu()
                .float()
            )  # nsf
        torch.cuda.synchronize()
        return infered_audio


class Config:
    def __init__(self) -> None:
        # 希尔伯特模型路径
        self.hubert_path: str = ""
        # 自训练模型路径
        self.pth_path: str = ""
        self.index_path: str = ""
        self.npy_path: str = ""
        # 音高
        self.pitch: int = 12
        # 音频采样率
        self.samplerate: int = 48000
        self.block_time: float = 1.0  # s
        self.buffer_num: int = 1
        self.threshold: int = -30
        self.crossfade_time: float = 0.08
        self.extra_time: float = 0.04
        # 输入降噪
        self.I_noise_reduce = False
        # 输出降噪
        self.O_noise_reduce = False
        self.index_rate = 0.3


def get_devices(update: bool = True):
    """获取设备列表"""
    if update:
        sd._terminate()
        sd._initialize()
    devices = sd.query_devices()
    hostapis = sd.query_hostapis()
    for hostapi in hostapis:
        for device_idx in hostapi["devices"]:
            devices[device_idx]["hostapi_name"] = hostapi["name"]
    input_devices = [
        f"{d['name']} ({d['hostapi_name']})"
        for d in devices
        if d["max_input_channels"] > 0
    ]
    output_devices = [
        f"{d['name']} ({d['hostapi_name']})"
        for d in devices
        if d["max_output_channels"] > 0
    ]
    input_devices_indices = [
        d["index"] for d in devices if d["max_input_channels"] > 0
    ]
    output_devices_indices = [
        d["index"] for d in devices if d["max_output_channels"] > 0
    ]
    return (
        input_devices,
        output_devices,
        input_devices_indices,
        output_devices_indices,
    )


def set_devices(input_device, output_device):
    """设置输出设备"""
    (
        input_devices,
        output_devices,
        input_device_indices,
        output_device_indices,
    ) = get_devices()
    sd.default.device[0] = input_device_indices[input_devices.index(input_device)]
    sd.default.device[1] = output_device_indices[
        output_devices.index(output_device)
    ]
    print("input device:" + str(sd.default.device[0]) + ":" + str(input_device))
    print("output device:" + str(sd.default.device[1]) + ":" + str(output_device))


class VCPage:
    window = None

    def __init__(self) -> None:
        self.config = Config()
        self.flag_vc = False

    def build_vc_gui(self):
        input_devices, output_devices, _, _ = get_devices()
        layout = [
            [
                sg.Frame(
                    title=i18n("加载模型"),
                    layout=[
                        [
                            sg.Input(
                                default_text="E:/vits/voicer/models/rvc_models/hubert_base.pt", key="hubert_path"
                            ),
                            sg.FileBrowse(i18n("Hubert模型")),
                        ],
                        [
                            sg.Input(default_text="E:/vits/audio_models/keli_ali/tiko.pth", key="pth_path"),
                            sg.FileBrowse(i18n("选择.pth文件")),
                        ],
                        [
                            sg.Input(
                                default_text="E:/vits/audio_models/keli_ali/added_IVF927_Flat_nprobe_7.index",
                                key="index_path",
                            ),
                            sg.FileBrowse(i18n("选择.index文件")),
                        ],
                        [
                            sg.Input(
                                default_text="E:/vits/audio_models/keli_ali/total_fea.npy",
                                key="npy_path",
                            ),
                            sg.FileBrowse(i18n("选择.npy文件")),
                        ],
                    ],
                )
            ],
            [
                sg.Frame(
                    layout=[
                        [
                            sg.Text(i18n("输入设备")),
                            sg.Combo(
                                input_devices,
                                key="sg_input_device",
                                default_value=input_devices[sd.default.device[0]],
                            ),
                        ],
                        [
                            sg.Text(i18n("输出设备")),
                            sg.Combo(
                                output_devices,
                                key="sg_output_device",
                                default_value=output_devices[sd.default.device[1]],
                            ),
                        ],
                    ],
                    title=i18n("音频设备(请使用同种类驱动)"),
                )
            ],
            [
                sg.Frame(
                    layout=[
                        [
                            sg.Text(i18n("响应阈值")),
                            sg.Slider(
                                range=(-60, 0),
                                key="threshold",
                                resolution=1,
                                orientation="h",
                                default_value=-30,
                            ),
                        ],
                        [
                            sg.Text(i18n("音调设置")),
                            sg.Slider(
                                range=(-24, 24),
                                key="pitch",
                                resolution=1,
                                orientation="h",
                                default_value=12,
                            ),
                        ],
                        [
                            sg.Text(i18n("Index Rate")),
                            sg.Slider(
                                range=(0.0, 1.0),
                                key="index_rate",
                                resolution=0.01,
                                orientation="h",
                                default_value=0.5,
                            ),
                        ],
                    ],
                    title=i18n("常规设置"),
                ),
                sg.Frame(
                    layout=[
                        [
                            sg.Text(i18n("采样长度")),
                            sg.Slider(
                                range=(0.1, 3.0),
                                key="block_time",
                                resolution=0.1,
                                orientation="h",
                                default_value=1.0,
                            ),
                        ],
                        [
                            sg.Text(i18n("淡入淡出长度")),
                            sg.Slider(
                                range=(0.01, 0.15),
                                key="crossfade_length",
                                resolution=0.01,
                                orientation="h",
                                default_value=0.08,
                            ),
                        ],
                        [
                            sg.Text(i18n("额外推理时长")),
                            sg.Slider(
                                range=(0.05, 3.00),
                                key="extra_time",
                                resolution=0.01,
                                orientation="h",
                                default_value=0.05,
                            ),
                        ],
                        [
                            sg.Checkbox(i18n("输入降噪"), key="I_noise_reduce"),
                            sg.Checkbox(i18n("输出降噪"), key="O_noise_reduce"),
                        ],
                    ],
                    title=i18n("性能设置"),
                ),
            ],
            [
                sg.Button(i18n("开始音频转换"), key="start_vc"),
                sg.Button(i18n("停止音频转换"), key="stop_vc"),
                sg.Text(i18n("推理时间(ms):")),
                sg.Text("0", key="infer_time"),
            ],
        ]
        return layout

    def handle_event(self, window, event, values):
        VCPage.window = window
        if event == "start_vc" and not self.flag_vc:
            self.set_values(values)
            print(str(self.config.__dict__))
            print("using_cuda:" + str(torch.cuda.is_available()))
            self.start_vc()
        if event == "stop_vc" and self.flag_vc:
            self.flag_vc = False

    def set_values(self, values):
        set_devices(values["sg_input_device"], values["sg_output_device"])
        self.config.hubert_path = values["hubert_path"]
        self.config.pth_path = values["pth_path"]
        self.config.index_path = values["index_path"]
        self.config.npy_path = values["npy_path"]
        self.config.threshold = values["threshold"]
        self.config.pitch = values["pitch"]
        self.config.block_time = values["block_time"]
        self.config.crossfade_time = values["crossfade_length"]
        self.config.extra_time = values["extra_time"]
        self.config.I_noise_reduce = values["I_noise_reduce"]
        self.config.O_noise_reduce = values["O_noise_reduce"]
        self.config.index_rate = values["index_rate"]

    def start_vc(self):
        torch.cuda.empty_cache()
        self.flag_vc = True
        self.block_frame = int(self.config.block_time * self.config.samplerate)
        self.crossfade_frame = int(self.config.crossfade_time * self.config.samplerate)
        self.sola_search_frame = int(0.012 * self.config.samplerate)
        self.delay_frame = int(0.02 * self.config.samplerate)  # 往前预留0.02s
        self.extra_frame = int(
            self.config.extra_time * self.config.samplerate
        )  # 往后预留0.04s
        self.rvc = None
        self.rvc = RVC(
            self.config.pitch,
            self.config.hubert_path,
            self.config.pth_path,
            self.config.index_path,
            self.config.npy_path,
            self.config.index_rate,
        )
        self.input_wav: np.ndarray = np.zeros(
            self.extra_frame
            + self.crossfade_frame
            + self.sola_search_frame
            + self.block_frame,
            dtype="float32",
        )
        self.output_wav: torch.Tensor = torch.zeros(
            self.block_frame, device=device, dtype=torch.float32
        )
        self.sola_buffer: torch.Tensor = torch.zeros(
            self.crossfade_frame, device=device, dtype=torch.float32
        )
        self.fade_in_window: torch.Tensor = torch.linspace(
            0.0, 1.0, steps=self.crossfade_frame, device=device, dtype=torch.float32
        )
        self.fade_out_window: torch.Tensor = 1 - self.fade_in_window
        self.resampler1 = tat.Resample(
            orig_freq=self.config.samplerate, new_freq=16000, dtype=torch.float32
        )
        self.resampler2 = tat.Resample(
            orig_freq=40000, new_freq=self.config.samplerate, dtype=torch.float32
        )
        thread_vc = threading.Thread(target=self.sound_input)
        thread_vc.start()

    def sound_input(self):
        """
        接受音频输入
        """
        with sd.Stream(
                callback=self.audio_callback,
                blocksize=self.block_frame,
                samplerate=self.config.samplerate,
                dtype="float32",
        ):
            while self.flag_vc:
                time.sleep(self.config.block_time)
                print("Audio block passed.")
        print("ENDing VC")

    def audio_callback(
            self, indata: np.ndarray, outdata: np.ndarray, frames, times, status
    ):
        """
        音频处理
        """
        start_time = time.perf_counter()
        indata = librosa.to_mono(indata.T)
        if self.config.I_noise_reduce:
            indata[:] = nr.reduce_noise(y=indata, sr=self.config.samplerate)

        """noise gate"""
        frame_length = 2048
        hop_length = 1024
        rms = librosa.feature.rms(
            y=indata, frame_length=frame_length, hop_length=hop_length
        )
        db_threshold = librosa.amplitude_to_db(rms, ref=1.0)[0] < self.config.threshold
        # print(rms.shape,db.shape,db)
        for i in range(db_threshold.shape[0]):
            if db_threshold[i]:
                indata[i * hop_length: (i + 1) * hop_length] = 0
        self.input_wav[:] = np.append(self.input_wav[self.block_frame:], indata)

        # infer
        print("input_wav:" + str(self.input_wav.shape))
        # print('infered_wav:'+str(infer_wav.shape))
        infer_wav: torch.Tensor = self.resampler2(
            self.rvc.infer(self.resampler1(torch.from_numpy(self.input_wav)))
        )[-self.crossfade_frame - self.sola_search_frame - self.block_frame:].to(
            device
        )
        print("infer_wav:" + str(infer_wav.shape))

        # SOLA algorithm from https://github.com/yxlllc/DDSP-SVC
        cor_nom = F.conv1d(
            infer_wav[None, None, : self.crossfade_frame + self.sola_search_frame],
            self.sola_buffer[None, None, :],
        )
        cor_den = torch.sqrt(
            F.conv1d(
                infer_wav[None, None, : self.crossfade_frame + self.sola_search_frame]
                ** 2,
                torch.ones(1, 1, self.crossfade_frame, device=device),
            )
            + 1e-8
        )
        sola_offset = torch.argmax(cor_nom[0, 0] / cor_den[0, 0])
        print("sola offset: " + str(int(sola_offset)))

        # crossfade
        self.output_wav[:] = infer_wav[sola_offset: sola_offset + self.block_frame]
        self.output_wav[: self.crossfade_frame] *= self.fade_in_window
        self.output_wav[: self.crossfade_frame] += self.sola_buffer[:]
        if sola_offset < self.sola_search_frame:
            self.sola_buffer[:] = (
                    infer_wav[
                    -self.sola_search_frame
                    - self.crossfade_frame
                    + sola_offset: -self.sola_search_frame
                                   + sola_offset
                    ]
                    * self.fade_out_window
            )
        else:
            self.sola_buffer[:] = (
                    infer_wav[-self.crossfade_frame:] * self.fade_out_window
            )

        if self.config.O_noise_reduce:
            outdata[:] = np.tile(
                nr.reduce_noise(
                    y=self.output_wav[:].cpu().numpy(), sr=self.config.samplerate
                ),
                (2, 1),
            ).T
        else:
            outdata[:] = self.output_wav[:].repeat(2, 1).t().cpu().numpy()
        total_time = time.perf_counter() - start_time
        print("infer time:" + str(total_time))
        VCPage.window["infer_time"].update(int(total_time * 1000))
