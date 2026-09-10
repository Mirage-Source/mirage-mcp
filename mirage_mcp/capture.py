"""
Append-only session capture. Every probe/response pair the honeypot sees
gets written to disk verbatim, along with the classifier's verdict — the
raw record is authoritative, the verdict is a derived opinion that can be
recomputed later as the signature bank improves.
"""

import json
import threading
import time
import uuid
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SESSIONS_LOG = DATA_DIR / "sessions.jsonl"

_write_lock = threading.Lock()


def new_session_id() -> str:
    return uuid.uuid4().hex


def record_event(
    *,
    session_id: str,
    tool_name: str,
    probe_id: str | None,
    response_text: str,
    verdict_label: str,
    verdict_confidence: float,
    declared_agent: str | None = None,
    client_info: dict[str, Any] | None = None,
    ip_hash: str | None = None,
    country: str | None = None,
) -> None:
    """Append one capture event as a JSON line. Never raises on a
    classification failure upstream — record what was observed even when
    the verdict is indeterminate.

    declared_agent is a self-reported, unverified label the caller
    optionally supplies (real ground truth when honest, noise when not —
    treat it the same way mirage-crawl treats a claimed crawler identity:
    a signal to check, never a fact to trust outright).

    ip_hash/country are derived from the connecting IP (see identity.py /
    geo.py) -- the raw IP itself is never passed in and never stored here.
    """
    event = {
        "ts": time.time(),
        "session_id": session_id,
        "tool_name": tool_name,
        "probe_id": probe_id,
        "response_text": response_text,
        "verdict_label": verdict_label,
        "verdict_confidence": verdict_confidence,
        "declared_agent": declared_agent,
        "client_info": client_info,
        "ip_hash": ip_hash,
        "country": country,
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event, ensure_ascii=False)

    with _write_lock:
        with SESSIONS_LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
