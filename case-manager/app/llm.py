"""外部 AI(Claude API)への送信口。案件データの外部送信はこのモジュールの send() だけが行う。

send() は必ず:
1. 匿名化済みテキストを受け取り、置換漏れ検査を行う(漏れがあれば送信しない)
2. 送信内容(匿名化済み)を ai_runs に保存し、監査ログに記録する
3. 応答(匿名化済み)を保存する
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Protocol

from . import db
from .anonymize import Anonymizer, AnonymizationLeak

log = logging.getLogger("case_manager")
DEFAULT_MODEL = "claude-opus-5-5"


@dataclass
class LLMResult:
    text: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class LLMClient(Protocol):
    model: str

    def complete(self, system: str, user: str, schema: dict, max_tokens: int = 16000) -> LLMResult: ...


class LLMError(Exception):
    pass


class AnthropicClient:
    """Anthropic 公式 SDK による実装。APIキーは .env の ANTHROPIC_API_KEY。"""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL, effort: str = "high"):
        import anthropic  # 遅延 import(未インストールでも v1 機能は動く)

        self._anthropic = anthropic
        self.client = anthropic.Anthropic(api_key=api_key, max_retries=2, timeout=600)
        self.model = model
        self.effort = effort

    def complete(self, system: str, user: str, schema: dict, max_tokens: int = 32000) -> LLMResult:
        a = self._anthropic
        try:
            with self.client.beta.messages.stream(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_config={"effort": self.effort,
                               "format": {"type": "json_schema", "schema": schema}},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            ) as stream:
                msg = stream.get_final_message()
        except a.AuthenticationError as e:
            raise LLMError("APIキーが無効です(.env の ANTHROPIC_API_KEY を確認)") from e
        except a.RateLimitError as e:
            raise LLMError("API の利用制限に達しました。しばらくして再試行してください") from e
        except a.BadRequestError as e:
            raise LLMError(f"API がリクエストを拒否しました: {e.message}") from e
        except a.APIStatusError as e:
            raise LLMError(f"API エラー({e.status_code})") from e
        except a.APIConnectionError as e:
            raise LLMError("API に接続できません(ネットワークを確認)") from e
        if msg.stop_reason == "refusal":
            raise LLMError("AI が応答を拒否しました")
        if msg.stop_reason == "max_tokens":
            raise LLMError("応答が長すぎて途中で切れました。資料を絞って再実行してください")
        text = next((b.text for b in msg.content if b.type == "text"), "")
        return LLMResult(text, msg.model, msg.usage.input_tokens, msg.usage.output_tokens)


def get_client(settings) -> LLMClient | None:
    factory = getattr(settings, "llm_factory", None)
    if factory:
        return factory()
    key = settings.anthropic_api_key
    if not key:
        return None
    return AnthropicClient(key, settings.ai_model or DEFAULT_MODEL, settings.ai_effort or "high")


def send(conn, request, *, client: LLMClient, anonymizer: Anonymizer, case_id: int, kind: str,
         question: str, system: str, user_anonymized: str, schema: dict, prompt_version: str,
         sources: list[dict]) -> tuple[int, dict]:
    """匿名化済みテキストを送信し、(ai_run_id, 解析済みJSON(匿名化のまま)) を返す。"""
    from .main import audit

    leaks = anonymizer.find_leaks(system + "\n" + user_anonymized)
    run = {
        "case_id": case_id, "kind": kind, "question": question, "model": client.model,
        "prompt_version": prompt_version, "sent_text": user_anonymized,
        "mapping_json": json.dumps(anonymizer.mapping(), ensure_ascii=False),
        "sources_json": json.dumps(sources, ensure_ascii=False), "created_at": db.now(),
    }
    if leaks:
        run.update(status="送信前停止", sent_text="", error=f"匿名化漏れ {len(leaks)}語")
        rid = _insert(conn, run)
        audit(conn, request, "AI送信を中止(匿名化漏れ)", "ai_run", rid, case_id, {"leaks": len(leaks)})
        raise AnonymizationLeak(leaks)

    run["status"] = "送信中"
    rid = _insert(conn, run)
    audit(conn, request, "AI送信", "ai_run", rid, case_id,
          {"kind": kind, "model": client.model, "chars": len(user_anonymized), "sources": len(sources)})
    try:
        res = client.complete(system, user_anonymized, schema)
        data = json.loads(res.text)
    except (LLMError, json.JSONDecodeError) as e:
        msg = str(e) if isinstance(e, LLMError) else "AI の応答を解析できませんでした"
        conn.execute("UPDATE ai_runs SET status='失敗', error=? WHERE id=?", (msg, rid))
        raise LLMError(msg) from e
    conn.execute("UPDATE ai_runs SET status='完了', model=?, response_text=?, input_tokens=?, output_tokens=? "
                 "WHERE id=?", (res.model, res.text, res.input_tokens, res.output_tokens, rid))
    return rid, data


def _insert(conn, data: dict) -> int:
    cols = ",".join(data)
    return conn.execute(f"INSERT INTO ai_runs({cols}) VALUES({','.join('?' * len(data))})",
                        tuple(data.values())).lastrowid

