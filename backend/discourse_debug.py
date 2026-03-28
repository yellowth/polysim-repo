"""
Opt-in discourse diagnostics. Set DISCOURSE_DEBUG=1 in .env (or export) and restart uvicorn.

Logs to stderr and backend/logs/discourse_debug.log. Optionally emits WebSocket events
type "discourse_debug" so the browser console can show the same (see useSimulation.js).
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

_LOG: logging.Logger | None = None


def discourse_debug_enabled() -> bool:
    v = os.environ.get("DISCOURSE_DEBUG", "").strip().lower()
    return v in ("1", "true", "yes")


def _logger() -> logging.Logger:
    global _LOG
    if _LOG is not None:
        return _LOG
    _LOG = logging.getLogger("polysim.discourse")
    _LOG.setLevel(logging.DEBUG if discourse_debug_enabled() else logging.WARNING)
    if discourse_debug_enabled() and not _LOG.handlers:
        fmt = logging.Formatter("%(asctime)s [discourse] %(levelname)s %(message)s")
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        _LOG.addHandler(sh)
        log_dir = Path(__file__).resolve().parent / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        path = os.environ.get("DISCOURSE_LOG_FILE", "").strip() or str(log_dir / "discourse_debug.log")
        fh = logging.FileHandler(path, encoding="utf-8")
        fh.setFormatter(fmt)
        _LOG.addHandler(fh)
        _LOG.debug("discourse_debug logging initialized path=%s", path)
    return _LOG


def dlog(msg: str, *args: Any) -> None:
    if discourse_debug_enabled():
        _logger().info(msg, *args)


def dlog_warning(msg: str, *args: Any) -> None:
    if discourse_debug_enabled():
        _logger().warning(msg, *args)


def dlog_error(msg: str, *args: Any) -> None:
    """Always log errors when debug is on; also use for non-debug critical paths if needed."""
    if discourse_debug_enabled():
        _logger().error(msg, *args)


def dlog_exception(ctx: str, exc: BaseException) -> None:
    if not discourse_debug_enabled():
        return
    _logger().error("%s: %s", ctx, exc, exc_info=exc)


async def emit_debug(websocket, phase: str, message: str, extra: dict | None = None) -> None:
    """Send a small debug payload to the client (and log)."""
    extra = dict(extra or {})
    if "traceback" in extra and isinstance(extra["traceback"], str):
        extra["traceback"] = extra["traceback"][-4000:]
    payload = {"phase": phase, "message": message, **extra}
    dlog("[%s] %s %s", phase, message, extra or {})
    if not discourse_debug_enabled():
        return
    try:
        await websocket.send_json({"type": "discourse_debug", "data": payload})
    except Exception as e:
        dlog_warning("emit_debug send failed: %s", e)
