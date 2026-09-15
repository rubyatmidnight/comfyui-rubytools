"""
Kokoro TTS, homebrew: runs the local Kokoro ONNX model, no cloud, no service.

Backend is the kokoro-onnx package on top of ONNX Runtime:
    pip install kokoro-onnx
(it pulls in onnxruntime, numpy and an espeak-ng loader for phonemes).

Model files (from the kokoro-onnx releases):
    kokoro-v1.0.onnx     the model
    voices-v1.0.bin      the voice styles (a numpy .npz)

Where they live, in order of precedence:
  1. the node's model_dir input, if not empty
  2. the KOKORO_MODEL_DIR environment variable
  3. "model_dir" in nodes/kokoro.json (copy kokoro.example.json and edit)
  4. ComfyUI/models/kokoro/

Output is a ComfyUI AUDIO (24 kHz mono), so it plugs straight into the core
Save Audio / Preview Audio nodes.
"""
import json
import os
from pathlib import Path

from .utils import resolve_path

CONFIG_FILE = Path(__file__).parent / "kokoro.json"
ENV_VAR = "KOKORO_MODEL_DIR"
DEFAULT_MODEL = "kokoro-v1.0.onnx"
DEFAULT_VOICES = "voices-v1.0.bin"
SAMPLE_RATE = 24000

LANGUAGES = ["en-us", "en-gb", "es", "fr-fr", "hi", "it", "ja", "pt-br", "cmn"]
PROVIDERS = ["auto", "cpu", "cuda", "dml"]

# Fallback voice list for when the voices file can't be read at load time.
FALLBACK_VOICES = [
    "af_heart", "af_alloy", "af_aoede", "af_bella", "af_jessica", "af_kore", "af_nicole",
    "af_nova", "af_river", "af_sarah", "af_sky",
    "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam", "am_michael", "am_onyx",
    "am_puck", "am_santa",
    "bf_alice", "bf_emma", "bf_isabella", "bf_lily",
    "bm_daniel", "bm_fable", "bm_george", "bm_lewis",
    "ef_dora", "em_alex", "em_santa", "ff_siwis",
    "hf_alpha", "hf_beta", "hm_omega", "hm_psi",
    "if_sara", "im_nicola",
    "jf_alpha", "jf_gongitsune", "jf_nezumi", "jf_tebukuro", "jm_kumo",
    "pf_dora", "pm_alex", "pm_santa",
    "zf_xiaobei", "zf_xiaoni", "zf_xiaoxiao", "zf_xiaoyi",
    "zm_yunjian", "zm_yunxi", "zm_yunxia", "zm_yunyang",
]

try:
    import folder_paths as comfy_paths
except Exception:
    comfy_paths = None


def _load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _model_files(override=""):
    """Return (model_path, voices_path) or raise with a helpful message."""
    config = _load_config()
    candidates = [
        (override or "").strip(),
        os.environ.get(ENV_VAR, "").strip(),
        config.get("model_dir", ""),
    ]
    if comfy_paths is not None:
        try:
            candidates.append(str(Path(comfy_paths.models_dir) / "kokoro"))
        except Exception:
            pass
    model_name = config.get("model", DEFAULT_MODEL)
    voices_name = config.get("voices", DEFAULT_VOICES)
    tried = []
    for candidate in candidates:
        if not candidate:
            continue
        folder = resolve_path(candidate)
        model, voices = folder / model_name, folder / voices_name
        if model.is_file() and voices.is_file():
            return model, voices
        tried.append(str(folder))
    raise RuntimeError(
        f"Kokoro model files not found ({model_name} + {voices_name}). Looked in: "
        + (", ".join(tried) or "nothing configured")
        + f". Set model_dir on the node, the {ENV_VAR} environment variable, "
        "or nodes/kokoro.json (see kokoro.example.json)."
    )


def _voice_names():
    """List voices from the voices file so the dropdown matches what's installed."""
    try:
        import numpy as np
        _, voices_path = _model_files()
        with np.load(str(voices_path)) as archive:
            names = sorted(archive.files)
        return names or FALLBACK_VOICES
    except Exception:
        return FALLBACK_VOICES


def _require_kokoro():
    try:
        import kokoro_onnx
    except ImportError as exc:
        raise RuntimeError(
            "kokoro-onnx is not installed. Install it into ComfyUI's python: pip install kokoro-onnx"
        ) from exc
    return kokoro_onnx


def _preload_cuda_dlls(ort):
    """Make CUDA and cuDNN DLLs findable. onnxruntime-gpu on Windows needs
    cudnn64_9.dll on the search path; torch ships one in torch/lib and
    onnxruntime.preload_dlls() knows to look there (and in the nvidia-* pip
    packages). Harmless when nothing is missing."""
    try:
        import torch  # noqa: F401  (loads torch/lib into the process first)
    except Exception:
        pass
    preload = getattr(ort, "preload_dlls", None)
    if preload is not None:
        try:
            preload()
        except Exception as exc:
            print(f"[Kokoro TTS] onnxruntime.preload_dlls failed: {exc}")


def _session_providers(choice):
    import onnxruntime as ort

    if choice in ("auto", "cuda"):
        _preload_cuda_dlls(ort)
    available = ort.get_available_providers()
    wanted = {
        "cpu": ["CPUExecutionProvider"],
        "cuda": ["CUDAExecutionProvider", "CPUExecutionProvider"],
        "dml": ["DmlExecutionProvider", "CPUExecutionProvider"],
        "auto": ["CUDAExecutionProvider", "DmlExecutionProvider", "CoreMLExecutionProvider", "CPUExecutionProvider"],
    }[choice]
    providers = [p for p in wanted if p in available]
    if choice in ("cuda", "dml") and providers[0] == "CPUExecutionProvider":
        print(f"[Kokoro TTS] {choice} provider not available in this onnxruntime build, using CPU. Available: {available}")
    return providers or ["CPUExecutionProvider"]


_CACHE = {}


def _get_engine(model_path, voices_path, provider):
    """One loaded model per (files, provider); ~300 MB, so keep it around."""
    key = (str(model_path), str(voices_path), provider)
    engine = _CACHE.get(key)
    if engine is None:
        kokoro_onnx = _require_kokoro()
        import onnxruntime as ort

        session = ort.InferenceSession(str(model_path), providers=_session_providers(provider))
        engine = kokoro_onnx.Kokoro.from_session(session, str(voices_path))
        _CACHE.clear()
        _CACHE[key] = engine
    return engine


def _to_audio(samples, sample_rate):
    import numpy as np
    import torch

    waveform = torch.from_numpy(np.asarray(samples, dtype=np.float32)).reshape(1, 1, -1)
    return {"waveform": waveform, "sample_rate": int(sample_rate)}


class KokoroTTS:
    RETURN_TYPES = ("AUDIO", "STRING")
    RETURN_NAMES = ("audio", "info")
    FUNCTION = "speak"
    CATEGORY = "Ruby's Nodes/Audio"

    @classmethod
    def INPUT_TYPES(cls):
        voices = _voice_names()
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": "", "tooltip": "Text to speak"}),
                "voice": (voices, {"default": "af_heart" if "af_heart" in voices else voices[0], "tooltip": "Voice style"}),
                "speed": ("FLOAT", {"default": 1.0, "min": 0.5, "max": 2.0, "step": 0.05, "tooltip": "Speaking rate"}),
                "language": (LANGUAGES, {"default": "en-us", "tooltip": "Language used for phonemization"}),
                "provider": (PROVIDERS, {"default": "auto", "tooltip": "ONNX Runtime execution provider"}),
            },
            "optional": {
                "blend_voice": (["(none)"] + voices, {"default": "(none)", "tooltip": "Second voice to mix with the first"}),
                "blend_amount": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.05, "tooltip": "How much of the blend voice to mix in. 0 is all first voice, 1 is all blend voice."}),
                "text_is_phonemes": ("BOOLEAN", {"default": False, "tooltip": "Treat the text as IPA phonemes instead of plain words"}),
                "trim_silence": ("BOOLEAN", {"default": True, "tooltip": "Trim leading and trailing silence from the result"}),
                "sentence_pause": ("FLOAT", {"default": 0.25, "min": 0.0, "max": 2.0, "step": 0.05, "tooltip": "Seconds of silence inserted between sentences"}),
                "clause_pause": ("FLOAT", {"default": 0.1, "min": 0.0, "max": 2.0, "step": 0.05, "tooltip": "Seconds of silence inserted at commas and other clause breaks"}),
                "model_dir": ("STRING", {"default": "", "tooltip": "Folder holding the .onnx model and voices .bin. Leave empty to use the environment variable, kokoro.json, or ComfyUI/models/kokoro."}),
            },
        }

    def speak(self, text, voice, speed, language, provider, blend_voice="(none)", blend_amount=0.5,
              text_is_phonemes=False, trim_silence=True, sentence_pause=0.25, clause_pause=0.1, model_dir=""):
        if not text.strip():
            raise ValueError("Kokoro TTS: text is empty.")
        model_path, voices_path = _model_files(model_dir)
        engine = _get_engine(model_path, voices_path, provider)

        style = voice
        blended = blend_voice != "(none)" and blend_voice != voice and blend_amount > 0.0
        if blended:
            import numpy as np

            first = engine.get_voice_style(voice)
            second = engine.get_voice_style(blend_voice)
            style = np.add(first * (1.0 - blend_amount), second * blend_amount)

        samples, sample_rate = engine.create(
            text, voice=style, speed=speed, lang=language, is_phonemes=text_is_phonemes, trim=trim_silence,
            sentence_pause=sentence_pause, clause_pause=clause_pause,
        )
        audio = _to_audio(samples, sample_rate)
        seconds = audio["waveform"].shape[-1] / audio["sample_rate"]
        mix = f" + {blend_voice} @ {blend_amount:.2f}" if blended else ""
        info = f"{voice}{mix}, {language}, x{speed:.2f}, {seconds:.2f}s @ {sample_rate} Hz, {engine.sess.get_providers()[0]}"
        return (audio, info)


class KokoroVoiceList:
    """Emit the installed voice names, one per line, for building menus or loops."""

    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("voices", "count")
    FUNCTION = "list_voices"
    CATEGORY = "Ruby's Nodes/Audio"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prefix": ("STRING", {"default": "", "tooltip": "Only list voices starting with this, e.g. af_ or bm_"}),
            },
            "optional": {
                "model_dir": ("STRING", {"default": "", "tooltip": "Folder holding the voices .bin. Leave empty to use the configured location."}),
            },
        }

    def list_voices(self, prefix, model_dir=""):
        import numpy as np

        _, voices_path = _model_files(model_dir)
        with np.load(str(voices_path)) as archive:
            names = sorted(n for n in archive.files if n.startswith(prefix))
        return ("\n".join(names), len(names))


NODE_CLASS_MAPPINGS = {
    "RubyKokoroTTS": KokoroTTS,
    "RubyKokoroVoiceList": KokoroVoiceList,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RubyKokoroTTS": "Kokoro TTS (local)",
    "RubyKokoroVoiceList": "Kokoro Voice List",
}
