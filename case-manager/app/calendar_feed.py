"""iPhone カレンダー連携(iCalendar 形式)。

- 購読用フィード: 期限・期日(と期限つき TODO)を配信。iPhone の「照会するカレンダーを追加」で登録する。
  カレンダーアプリは Cookie を送れないため、推測できない長いトークンを URL に含める(ハッシュのみ保存)。
- 1件ずつの .ics: 期限・期日をカレンダーに取り込む(通知つき)。
"""
from __future__ import annotations

import datetime as dt
import hashlib

VTIMEZONE = [
    "BEGIN:VTIMEZONE", "TZID:Asia/Tokyo",
    "BEGIN:STANDARD", "DTSTART:19700101T000000", "TZOFFSETFROM:+0900", "TZOFFSETTO:+0900", "TZNAME:JST",
    "END:STANDARD", "END:VTIMEZONE",
]


def esc(s: str) -> str:
    return (s or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\r\n", "\\n").replace("\n", "\\n")


def fold(line: str) -> str:
    """RFC 5545: 75オクテットで折り返す(UTF-8 の文字の途中では切らない)。"""
    out, cur = [], b""
    for ch in line:
        b = ch.encode()
        if len(cur) + len(b) > (75 if not out else 74):
            out.append(cur.decode())
            cur = b""
        cur += b
    out.append(cur.decode())
    return "\r\n ".join(out)


def uid_for(kind: str, item_id: int, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{kind}:{item_id}".encode()).hexdigest()[:24] + "@case-manager"


def _stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def event_lines(*, uid: str, summary: str, date: str, time: str = "", description: str = "",
                location: str = "", alarms: tuple[str, ...] = ("-P2DT15H", "-PT15H")) -> list[str]:
    """date: YYYY-MM-DD。time(HH:MM)があれば1時間の予定、なければ終日。"""
    d = dt.date.fromisoformat(date)
    lines = ["BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{_stamp()}", f"SUMMARY:{esc(summary)}"]
    if time:
        hh, mm = (int(x) for x in time.split(":")[:2])
        start = dt.datetime(d.year, d.month, d.day, hh, mm)
        end = start + dt.timedelta(hours=1)
        lines += [f"DTSTART;TZID=Asia/Tokyo:{start:%Y%m%dT%H%M%S}", f"DTEND;TZID=Asia/Tokyo:{end:%Y%m%dT%H%M%S}"]
        alarms = ("-P1D", "-PT2H")
    else:
        lines += [f"DTSTART;VALUE=DATE:{d:%Y%m%d}", f"DTEND;VALUE=DATE:{d + dt.timedelta(days=1):%Y%m%d}"]
    if description:
        lines.append(f"DESCRIPTION:{esc(description)}")
    if location:
        lines.append(f"LOCATION:{esc(location)}")
    for trig in alarms:
        lines += ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{esc(summary)}", f"TRIGGER:{trig}", "END:VALARM"]
    lines.append("END:VEVENT")
    return lines


def calendar(name: str, events: list[list[str]]) -> str:
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//case-manager//JA", "CALSCALE:GREGORIAN",
             "METHOD:PUBLISH", f"X-WR-CALNAME:{esc(name)}", "X-WR-TIMEZONE:Asia/Tokyo",
             "REFRESH-INTERVAL;VALUE=DURATION:PT1H", "X-PUBLISHED-TTL:PT1H", *VTIMEZONE]
    for ev in events:
        lines += ev
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold(x) for x in lines) + "\r\n"


def deadline_summary(d: dict, title_mode: str) -> str:
    """title_mode: full=事件名を含める / masked=案件番号のみ。機微案件は常に伏せる。"""
    head = "【未確定】" if not d.get("confirmed", 1) else ""
    case = f"案件#{d['case_id']}" if (title_mode == "masked" or d.get("sensitive")) else d["case_title"]
    return f"{head}{d['kind']}: {d['title']}({case})"
