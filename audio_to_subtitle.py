# -*- coding: utf-8 -*-
"""
audio_to_subtitle.py

Convert any audio/video file (30s to 3h) into precise subtitles (SRT) in Persian (fa) or English (en), with GPU acceleration if available. Uses faster-whisper for fast ASR and whisperx for word-level forced alignment.

This file provides the transcribe_pipeline(input_path, lang) function used by the bot.
"""

import argparse
import os
import sys
import tempfile
import uuid
import math
import shutil
from typing import List, Dict, Optional, Tuple
import subprocess

from tqdm import tqdm
import shutil as _shutil

try:
    import torch
except Exception:
    torch = None  # type: ignore

try:
    from faster_whisper import WhisperModel
except Exception:
    WhisperModel = None  # type: ignore

try:
    import whisperx
except Exception:
    whisperx = None  # type: ignore

# Optional online translator
try:
    from googletrans import Translator  # type: ignore
except Exception:
    Translator = None  # type: ignore

SUPPORTED_LANGS = {"fa", "en"}
DEFAULT_MODEL = os.environ.get("A2S_MODEL", "large-v3")
MODEL_FA = os.environ.get("A2S_MODEL_FA")  # مدل اختصاصی فارسی (در صورت تنظیم)
MODEL_EN = os.environ.get("A2S_MODEL_EN")  # مدل اختصاصی انگلیسی (در صورت تنظیم)
STRICT_LANG = os.environ.get("A2S_STRICT_LANG", "1") == "1"
ENABLE_FA_RULES = os.environ.get("A2S_FA_RULES", "0") == "1"
ENV_BEAM = os.environ.get("A2S_BEAM")
ENV_TEMP = os.environ.get("A2S_TEMP")
COND_PREV = os.environ.get("A2S_CONDITION_PREV", "0") == "1"
VAD_MIN_MS = int(os.environ.get("A2S_VAD_MIN_MS", "600"))
MAX_SUBTITLE_DURATION = 3.0
MAX_WORDS_PER_LINE = 8
DEBUG = os.environ.get("A2S_DEBUG", "0") == "1"
FAST_NO_VAD = os.environ.get("A2S_FAST_NO_VAD", "0") == "1"

_MODEL_CACHE: Dict[Tuple[str, str, str, int, int], "WhisperModel"] = {}


def check_dependencies() -> None:
    missing = []
    if WhisperModel is None:
        missing.append("faster-whisper")
    if missing:
        raise RuntimeError(
            "Missing dependencies: " + ", ".join(missing) + ".\n"
            "Install with: pip install " + " ".join(missing)
        )
    if whisperx is None:
        # Optional, alignment disabled
        pass


def _find_binary(binary_name: str) -> Optional[str]:
    path = _shutil.which(binary_name)
    if path:
        return path
    candidate = os.path.join(
        os.environ.get("LOCALAPPDATA", ""),
        "Microsoft",
        "WinGet",
        "Packages",
    )
    if os.path.isdir(candidate):
        for root, _, files in os.walk(candidate):
            if binary_name.lower() in [f.lower() for f in files]:
                return os.path.join(root, binary_name)
    return None


def _probe_duration_seconds(input_path: str) -> float:
    ffprobe_path = _find_binary("ffprobe.exe") or _find_binary("ffprobe") or "ffprobe"
    result = subprocess.run(
        [ffprobe_path, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", input_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
        text=True,
    )
    return float(result.stdout.strip())


def has_cuda() -> bool:
    try:
        return bool(torch is not None and torch.cuda.is_available())
    except Exception:
        return False


def get_device_and_compute_type() -> Tuple[str, str]:
    if has_cuda():
        return "cuda", "float16"
    return "cpu", "int8"


def get_cpu_threads_and_workers() -> Tuple[int, int]:
    cpu_threads = max(1, (os.cpu_count() or 4) - 1)
    num_workers = 2 if has_cuda() else 1
    return cpu_threads, num_workers


def get_whisper_model(model_name: str, device: str, compute_type: str) -> "WhisperModel":
    cpu_threads, num_workers = get_cpu_threads_and_workers()
    key = (model_name, device, compute_type, cpu_threads, num_workers)
    if key in _MODEL_CACHE:
        return _MODEL_CACHE[key]
    model = WhisperModel(
        model_name,
        device=device,
        compute_type=compute_type,
        cpu_threads=cpu_threads,
        num_workers=num_workers,
    )
    _MODEL_CACHE[key] = model
    return model


def select_model_by_lang(lang: Optional[str]) -> str:
    """بر اساس زبان، بهترین مدل رایگان و آفلاین را انتخاب می‌کند (قابل override با ENV)."""
    # اولویت با ENV اختصاصی هر زبان
    if lang == "fa" and MODEL_FA:
        return MODEL_FA
    if lang == "en" and MODEL_EN:
        return MODEL_EN
    # انتخاب‌های پیشنهادی
    # برای انگلیسی: مدل‌های "*.en" دقیق‌تر و سریع‌تر می‌شوند
    if lang == "en":
        # اگر سخت‌افزار قوی نیست، medium.en تعادل خوبی دارد
        return "medium.en"
    # برای فارسی: بهترین کیفیت، مدل‌های چندزبانه بزرگ‌تر
    if lang == "fa":
        return "large-v3"
    # پیش‌فرض
    return DEFAULT_MODEL


def translate_texts_google(texts: List[str], src: str, dest: str) -> List[str]:
    """Translate a list of texts using googletrans. Falls back to originals on failure."""
    if not texts:
        return texts
    if Translator is None:
        return texts
    try:
        translator = Translator()
        out: List[str] = []
        chunk: List[str] = []
        max_chunk = 20
        for t in texts:
            chunk.append(t)
            if len(chunk) >= max_chunk:
                res = translator.translate(chunk, src=src, dest=dest)
                out.extend([r.text for r in res])
                chunk = []
        if chunk:
            res = translator.translate(chunk, src=src, dest=dest)
            out.extend([r.text for r in res])
        return out
    except Exception:
        return texts


essential_bins_checked = False


def load_audio_to_mono16k_wav(input_path: str, tmp_dir: str) -> Tuple[str, float]:
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input not found: {input_path}")
    duration_s = _probe_duration_seconds(input_path)
    out_wav = os.path.join(tmp_dir, f"{uuid.uuid4().hex}.wav")
    ffmpeg_bin = _find_binary("ffmpeg.exe") or _find_binary("ffmpeg") or "ffmpeg"
    subprocess.run([ffmpeg_bin, "-y", "-i", input_path, "-ac", "1", "-ar", "16000", out_wav], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return out_wav, duration_s


def _normalize_fa_text(text: str) -> str:
    # ساده‌سازی فارسی: یکسان‌سازی حروف عربی/فارسی، حذف کشیده و فاصله‌های تکراری
    if not text:
        return text
    replaces = {
        "ي": "ی",
        "ى": "ی",
        "ئ": "ی",
        "ك": "ک",
        "أ": "ا",
        "إ": "ا",
        "ؤ": "و",
        "ٱ": "ا",
        "ـ": "",  # کشیده
    }
    for k, v in replaces.items():
        text = text.replace(k, v)
    # فاصله‌های متعدد به یک فاصله
    text = " ".join(text.split())
    return text

def _fa_common_corrections(text: str) -> str:
    # غیرفعال پیش‌فرض؛ در صورت نیاز با A2S_FA_RULES=1 فعال می‌شود
    return text


def transcribe_with_faster_whisper(
    wav_path: str,
    lang: Optional[str],
    model_name: str,
    device: str,
    compute_type: str,
    progress_total_s: float,
) -> Tuple[List[Dict], str]:
    model = get_whisper_model(model_name, device, compute_type)
    # افزایش/کنترل beam از طریق ENV یا بر اساس مدل
    if ENV_BEAM is not None:
        try:
            beam_size = max(1, int(ENV_BEAM))
        except Exception:
            beam_size = 2
    else:
        if "large" in model_name:
            beam_size = 3
        elif "medium" in model_name:
            beam_size = 2
        else:
            beam_size = 2
    kwargs = {
        "beam_size": beam_size,
        "vad_filter": False if FAST_NO_VAD else True,
        "vad_parameters": {"min_silence_duration_ms": VAD_MIN_MS},
        "no_speech_threshold": 0.5,
        "log_prob_threshold": -1.2,
        "compression_ratio_threshold": 2.6,
        "condition_on_previous_text": COND_PREV,
    }
    # کنترل دما
    if ENV_TEMP:
        try:
            kwargs["temperature"] = float(ENV_TEMP)
        except Exception:
            kwargs["temperature"] = 0.0
    else:
        kwargs["temperature"] = 0.0
    # قفل زبان در صورت انتخاب کاربر
    if STRICT_LANG and lang:
        kwargs["language"] = lang
        # prompt راهنمایی سبک نوشتار فارسی
        if lang == "fa":
            kwargs["initial_prompt"] = "«متن فارسی، کلمات صحیح و بدون کشیده و محاوره رایج.»"

    seg_iter, info = model.transcribe(wav_path, **kwargs)
    detected_lang = getattr(info, "language", None) or (lang or "en")
    segments: List[Dict] = []
    last_end = 0.0
    for s in seg_iter:
        text = s.text.strip()
        if (lang or detected_lang) == "fa":
            text = _normalize_fa_text(text)
            if ENABLE_FA_RULES:
                text = _fa_common_corrections(text)
        seg = {"start": float(s.start), "end": float(s.end), "text": text}
        segments.append(seg)
        last_end = float(s.end)
    # Progress bar removed for bot usage
    return segments, detected_lang


def align_with_whisperx(
    wav_path: str,
    segments: List[Dict],
    language: str,
    device: str,
) -> List[Dict]:
    if not segments:
        return []
    if whisperx is None:
        return segments
    audio = whisperx.load_audio(wav_path)
    align_model, metadata = whisperx.load_align_model(language_code=language, device=device)
    aligned = whisperx.align({"segments": segments, "language": language}, align_model, metadata, audio, device, return_char_alignments=False)
    return aligned["segments"]


def format_timestamp_srt(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def chunk_words_to_subs(words: List[Dict], max_duration: float, max_words: int) -> List[Dict]:
    subs: List[Dict] = []
    cur_words: List[str] = []
    cur_start: Optional[float] = None
    cur_end: Optional[float] = None
    for w in words:
        if "start" not in w or w["start"] is None or "end" not in w or w["end"] is None:
            continue
        w_start = float(w["start"])  # type: ignore
        w_end = float(w["end"])  # type: ignore
        token = str(w.get("word", "")).strip()
        if not token:
            continue
        if cur_start is None:
            cur_start = w_start
            cur_end = w_end
            cur_words = [token]
            continue
        next_end = w_end
        next_count = len(cur_words) + 1
        next_duration = next_end - cur_start
        if next_duration > MAX_SUBTITLE_DURATION or next_count > MAX_WORDS_PER_LINE:
            if cur_words and cur_start is not None and cur_end is not None:
                subs.append({"start": cur_start, "end": cur_end, "text": " ".join(cur_words)})
            cur_words = [token]
            cur_start = w_start
            cur_end = w_end
        else:
            cur_words.append(token)
            cur_end = next_end
    if cur_words and cur_start is not None and cur_end is not None:
        subs.append({"start": cur_start, "end": cur_end, "text": " ".join(cur_words)})
    return subs


def fallback_chunk_segments(segments: List[Dict]) -> List[Dict]:
    subs: List[Dict] = []
    for seg in segments:
        start = float(seg.get("start", 0.0))
        end = float(seg.get("end", start + 2.0))
        text = str(seg.get("text", "")).strip()
        if not text:
            continue
        duration = max(0.0, end - start)
        if duration <= MAX_SUBTITLE_DURATION:
            subs.append({"start": start, "end": end, "text": text})
            continue
        parts = max(1, int(math.ceil(duration / MAX_SUBTITLE_DURATION)))
        words = text.split()
        words_per_part = max(1, int(math.ceil(len(words) / parts)))
        current = 0
        for i in range(parts):
            chunk_words = words[current: current + words_per_part]
            if not chunk_words:
                break
            chunk_start = start + i * (duration / parts)
            chunk_end = start + (i + 1) * (duration / parts)
            subs.append({"start": chunk_start, "end": chunk_end, "text": " ".join(chunk_words)})
            current += words_per_part
    return subs


def build_subtitles(aligned_segments: List[Dict]) -> List[Dict]:
    all_words: List[Dict] = []
    for seg in aligned_segments:
        for w in seg.get("words", []) or []:
            if w.get("start") is None or w.get("end") is None:
                continue
            token = str(w.get("word", "")).strip()
            if token:
                all_words.append({"word": token, "start": float(w["start"]), "end": float(w["end"])} )
    if all_words:
        return chunk_words_to_subs(all_words, MAX_SUBTITLE_DURATION, MAX_WORDS_PER_LINE)
    return fallback_chunk_segments(aligned_segments)


def _merge_short_subs(subs: List[Dict], min_duration: float = 0.8) -> List[Dict]:
    if not subs:
        return subs
    merged: List[Dict] = []
    i = 0
    while i < len(subs):
        cur = subs[i]
        duration = float(cur["end"]) - float(cur["start"])
        if duration < min_duration and i + 1 < len(subs):
            nxt = subs[i + 1]
            combined_text = (str(cur.get("text", "")).strip() + " " + str(nxt.get("text", "")).strip()).strip()
            combined_duration = float(nxt["end"]) - float(cur["start"])
            if combined_duration <= MAX_SUBTITLE_DURATION:
                merged.append({"start": float(cur["start"]), "end": float(nxt["end"]), "text": combined_text})
                i += 2
                continue
        merged.append(cur)
        i += 1
    return merged


def write_srt(subs: List[Dict], out_path: str) -> None:
    lines: List[str] = []
    for idx, item in enumerate(subs, start=1):
        start = format_timestamp_srt(float(item["start"]))
        end = format_timestamp_srt(float(item["end"]))
        text = str(item.get("text", "")).strip()
        lines.append(str(idx))
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def transcribe_pipeline(input_path: str, lang: str, model_name: str = DEFAULT_MODEL) -> str:
    check_dependencies()
    # انتخاب مدل بر اساس زبان در صورتیکه کاربر model_name را override نکرده باشد
    if model_name == DEFAULT_MODEL:
        model_name = select_model_by_lang(lang)
    device, compute_type = get_device_and_compute_type()
    tmp_dir = tempfile.mkdtemp(prefix="a2s_")
    srt_path = None
    try:
        wav_path, duration_s = load_audio_to_mono16k_wav(input_path, tmp_dir)
        # اگر فارسی و ترجمه آنلاین فعال: اول انگلیسی STT بگیریم
        stt_lang = lang
        used_model = model_name
        if lang == "fa" and os.environ.get("A2S_TRANSLATE_FA_VIA_EN", "0") == "1":
            stt_lang = "en"
            used_model = select_model_by_lang("en")
        segments, det_lang = transcribe_with_faster_whisper(wav_path, stt_lang, used_model, device, compute_type, duration_s)
        detected_language = stt_lang if stt_lang in SUPPORTED_LANGS else (det_lang or "en")
        # ترجمه در صورت نیاز
        if lang == "fa" and stt_lang == "en":
            original_texts = [seg.get("text", "") for seg in segments]
            translated = translate_texts_google(original_texts, src="en", dest="fa")
            for i, seg in enumerate(segments):
                seg["text"] = translated[i] if i < len(translated) else seg.get("text", "")
            detected_language = "fa"
        align_lang = detected_language if detected_language in SUPPORTED_LANGS else (lang if lang in SUPPORTED_LANGS else "en")
        aligned_segments = align_with_whisperx(wav_path, segments, align_lang, device)
        subs = build_subtitles(aligned_segments)
        subs = _merge_short_subs(subs)
        if not subs:
            subs = fallback_chunk_segments(segments)
        base_out = os.path.splitext(os.path.basename(input_path))[0] + ".srt"
        if not base_out.lower().endswith('.srt'):
            base_out = os.path.splitext(base_out)[0] + '.srt'
        srt_path = os.path.abspath(base_out)
        write_srt(subs, srt_path)
        return srt_path
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    print("Use transcribe_pipeline from this module in the bot.")
