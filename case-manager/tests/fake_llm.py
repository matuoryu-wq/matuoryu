"""テスト用の偽 AI。送信内容を記録し、資料から出典つきの応答を組み立てる(外部通信なし)。"""
import json
import re

from app.llm import LLMResult

SRC_RE = re.compile(r"^\[(S\d+)\] (.*?)\n(.*?)(?=^\[S\d+\] |^</資料>)", re.S | re.M)


def parse_sources(user: str) -> list[tuple[str, str, str]]:
    return [(m.group(1), m.group(2), m.group(3).strip()) for m in SRC_RE.finditer(user)]


def first_quote(text: str, n: int = 20) -> str:
    line = next((l for l in text.splitlines() if len(l.strip()) >= 6), text)
    line = re.sub(r"^\[\d\d:\d\d:\d\d [^\]]*\] ", "", line.strip())
    return line[:n]


class FakeLLM:
    model = "fake-model"

    def __init__(self):
        self.calls: list[dict] = []

    def complete(self, system, user, schema, max_tokens=16000):
        self.calls.append({"system": system, "user": user, "schema": schema})
        srcs = parse_sources(user)
        cite = lambda i: [{"source_id": srcs[i][0], "quote": first_quote(srcs[i][2])}] if srcs else []  # noqa: E731
        props = schema["properties"]
        if "answer" in props:
            items = [{"text": f"資料{s[0]}によれば、{first_quote(s[2], 30)}。", "citations": cite(i)}
                     for i, s in enumerate(srcs[:3])]
            # 実在しない引用(出典照合で「不一致」になるべきもの)と、存在しない出典番号
            items.append({"text": "相手方は全額を支払うと約束した。", "citations": [
                {"source_id": srcs[0][0] if srcs else "S1", "quote": "全額を必ず支払うと約束します"}]})
            items.append({"text": "架空の出典。", "citations": [{"source_id": "S999", "quote": "なし"}]})
            data = {"answer": items, "not_found": ["納品書の原本の内容"]}
        elif "sections" in props:
            heads = re.findall(r"^\d+\. (.+)$", user.split("<見出し>")[1].split("</見出し>")[0], re.M)
            people = ["【依頼者1】"] if "【依頼者1】" in user else sorted(set(re.findall(r"【[^【】]+】", user)))
            data = {"sections": [{"heading": h, "items": [
                {"text": f"{h}: {people[0] if people else ''}に関する事項({srcs[i % len(srcs)][0]})",
                 "citations": cite(i % len(srcs))}] if srcs else []} for i, h in enumerate(heads)],
                "caveats": ["初稿です"]}
        else:
            tl = []
            for i, (sid, label, text) in enumerate(srcs):
                for m in re.finditer(r"(\d{4})年(\d{1,2})月(\d{1,2})日", text):
                    tl.append({"date": f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}",
                               "date_precision": "日", "event": f"{label}の記載", "certainty": "確実", "note": "",
                               "citations": [{"source_id": sid, "quote": m.group(0)}]})
            tl.sort(key=lambda t: t["date"])
            data = {"timeline": tl,
                    "issues": [{"issue": "検収の有無", "our_position": "検収済み", "their_position": "不具合あり",
                                "status": "争いあり", "open_questions": ["検収書の有無"], "citations": cite(0)}],
                    "contradictions": [{"text": "納品日が3月か4月か食い違う", "citations": cite(0)}]}
        return LLMResult(json.dumps(data, ensure_ascii=False), self.model, len(user), 100)


class FakeTranscriber:
    def __init__(self, fixture: dict):
        self.fixture = fixture

    def transcribe(self, path, progress=None):
        from app.transcribe import TranscriptResult
        return TranscriptResult([dict(s) for s in self.fixture["segments"]], self.fixture["duration"], "fake")
