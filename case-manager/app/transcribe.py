"""録音の文字起こし(PC内で処理。音声を外部に送信しない)。

- 文字起こし: faster-whisper(初回のみモデルをダウンロード。WHISPER_MODEL にローカルパスも指定可)
- 話者分離: pyannote.audio(任意。DIARIZATION=pyannote のとき)。未設定なら話者は「話者不明」とし、
  画面で話者名を付け替える。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger("case_manager")


@dataclass
class TranscriptResult:
    segments: list[dict]        # {start, end, speaker, text}
    duration: float
    engine: str
    message: str = ""


class TranscribeError(Exception):
    pass


class WhisperTranscriber:
    def __init__(self, model: str = "small", device: str = "cpu", diarization: str = "off",
                 pyannote_model: str = "", hf_token: str = ""):
        self.model_name, self.device = model, device
        self.diarization, self.pyannote_model, self.hf_token = diarization, pyannote_model, hf_token
        self._model = None

    def _load(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as e:
                raise TranscribeError("faster-whisper が未インストールです(pip install faster-whisper)") from e
            compute = "int8" if self.device == "cpu" else "float16"
            self._model = WhisperModel(self.model_name, device=self.device, compute_type=compute)
        return self._model

    def transcribe(self, path: Path, progress=None) -> TranscriptResult:
        model = self._load()
        segs, info = model.transcribe(str(path), language="ja", vad_filter=True, beam_size=5)
        out = []
        for s in segs:
            out.append({"start": round(s.start, 2), "end": round(s.end, 2), "speaker": "", "text": s.text.strip()})
            if progress and info.duration:
                progress(f"{int(s.end / info.duration * 100)}%")
        engine = f"faster-whisper:{self.model_name}"
        message = ""
        if self.diarization == "pyannote":
            try:
                assign_speakers(out, self._diarize(path))
                engine += "+pyannote"
            except Exception as e:  # noqa: BLE001  話者分離に失敗しても文字起こしは保存する
                log.warning("話者分離に失敗: %s", e)
                message = f"話者分離に失敗しました: {type(e).__name__}"
        return TranscriptResult(out, float(info.duration or 0), engine, message)

    def _diarize(self, path: Path) -> list[tuple[float, float, str]]:
        from pyannote.audio import Pipeline

        kw = {"use_auth_token": self.hf_token} if self.hf_token else {}
        pipe = Pipeline.from_pretrained(self.pyannote_model, **kw)
        ann = pipe(str(path))
        return [(turn.start, turn.end, spk) for turn, _, spk in ann.itertracks(yield_label=True)]


def assign_speakers(segments: list[dict], turns: list[tuple[float, float, str]]) -> None:
    """各セグメントに、時間の重なりが最大の話者を割り当てる。話者名は 話者A, 話者B… に付け直す。"""
    names: dict[str, str] = {}
    for s in segments:
        best, best_ov = "", 0.0
        for t0, t1, spk in turns:
            ov = min(s["end"], t1) - max(s["start"], t0)
            if ov > best_ov:
                best, best_ov = spk, ov
        if best:
            if best not in names:
                names[best] = f"話者{chr(ord('A') + len(names))}"
            s["speaker"] = names[best]


def get_transcriber(settings):
    if settings.transcriber_factory:
        return settings.transcriber_factory()
    return WhisperTranscriber(settings.whisper_model, settings.whisper_device, settings.diarization,
                              settings.pyannote_model, settings.hf_token)
