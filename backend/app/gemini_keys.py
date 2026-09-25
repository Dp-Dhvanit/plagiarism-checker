"""
Shared multi-key rotation for the Gemini API.

Google's free tier caps each (API key, model) pair at a small daily quota —
measured at 20 requests/day for gemini-3.6-flash (see IMPROVEMENTS.md). Each
Google account gets its own free-tier key with its own independent quota, so
GEMINI_API_KEY may be set to a comma-separated list of keys from different
accounts. When a call hits 429 RESOURCE_EXHAUSTED, it automatically retries
against the next key instead of failing outright.

This module owns only key selection/rotation. Model choice, timeouts, and
error-message formatting stay in gemini_client.py (the detectors) and
gemini_summarizer.py (the summary layer) — deliberately kept separate so
this doesn't couple those two otherwise-independent configs together.
"""
from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Callable, TypeVar

from dotenv import load_dotenv

load_dotenv()

try:
    from google import genai
    _SDK_AVAILABLE = True
except ImportError:
    _SDK_AVAILABLE = False

T = TypeVar("T")

_lock = threading.Lock()
_clients: dict[str, "genai.Client"] = {}
_exhausted_until: dict[str, datetime] = {}

# Google resets the free-tier daily quota at midnight Pacific, not at a fixed
# offset from the failing request — this cooldown is a pragmatic stand-in,
# not an exact reset time. Worst case a key is retried a bit early, gets
# marked exhausted again immediately, and costs one wasted call.
_COOLDOWN = timedelta(hours=1)


def _keys() -> list[str]:
    raw = os.environ.get("GEMINI_API_KEY", "")
    # dict.fromkeys instead of a set to preserve the .env ordering — rotation
    # order should be deterministic and match how the user listed them.
    return list(dict.fromkeys(k.strip() for k in raw.split(",") if k.strip()))


def is_configured() -> bool:
    return _SDK_AVAILABLE and bool(_keys())


def key_count() -> int:
    return len(_keys())


def is_quota_error(exc: Exception) -> bool:
    msg = str(exc)
    return "429" in msg or "RESOURCE_EXHAUSTED" in msg


# A 401/403 is specific to the KEY/PROJECT that made the call, not to the
# request itself — one Google account's project being rate-limited,
# suspended, or missing a permission says nothing about a DIFFERENT
# account's key. Treated the same as a quota error: skip to the next key
# rather than aborting the whole rotation. (400/404 stay genuinely
# universal — a malformed request or a retired model name fails the same
# way no matter which key answers, so those still raise immediately.)
def is_key_specific_auth_error(exc: Exception) -> bool:
    msg = str(exc)
    return "401" in msg or "403" in msg or "PERMISSION_DENIED" in msg or "UNAUTHENTICATED" in msg


# Retry is opt-IN, not opt-out: only an error confirmed to be transient
# (a fast-failing network blip or a 5xx server error — the call would
# likely succeed a moment later) gets retried. Everything else — quota
# (handled by key rotation above), a request that already timed out (it
# already burned its full 25-90s budget once; retrying costs a lot for
# little chance of a different outcome — move to the next key instead), a
# clear permanent rejection, or any error this module doesn't recognize —
# is NOT retried and raises immediately. Retrying on anything not
# affirmatively classified as permanent (the previous, inverted logic) was
# a real bug: a generic, unrelated error would get retried 3 times per key
# across every configured key before finally raising.
_TRANSIENT_MARKERS = ("500", "502", "503", "504", "unavailable", "internal error",
                       "servererror", "connection", "network", "reset by peer")
_TIMEOUT_MARKERS = ("timeout", "timed out", "deadline")
_RETRY_BACKOFF_S = (0.5, 1.5)  # one retry after ~0.5s, one more after ~1.5s


def _is_transient_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(marker in msg for marker in _TRANSIENT_MARKERS)


def _is_timeout_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(marker in msg for marker in _TIMEOUT_MARKERS)


def _client_for(key: str) -> "genai.Client":
    if key not in _clients:
        _clients[key] = genai.Client(api_key=key)
    return _clients[key]


def _rotation_order() -> list[str]:
    """Configured keys, freshest-first: keys not currently on cooldown come
    before ones that are. If every key is on cooldown, try them all anyway —
    a stale cooldown shouldn't make the feature look permanently dead."""
    now = datetime.now(timezone.utc)
    with _lock:
        keys = _keys()
        fresh = [k for k in keys if _exhausted_until.get(k, now) <= now]
        stale = [k for k in keys if k not in fresh]
    return fresh + stale


def _mark_exhausted(key: str) -> None:
    with _lock:
        _exhausted_until[key] = datetime.now(timezone.utc) + _COOLDOWN


def call_with_rotation(fn: Callable[["genai.Client"], T]) -> T:
    """Call `fn(client)` against each configured key in rotation order,
    advancing to the next key on a quota/rate-limit error OR a key-specific
    auth error (401/403 — see is_key_specific_auth_error). A CONFIRMED
    transient failure (a 5xx server error, a network blip) is retried on
    the SAME key with a short backoff before giving up — key rotation
    wouldn't help there, the call itself just needs another try. Anything
    else — a timed-out request, a genuinely universal rejection (bad
    request, model not found), or any error this module doesn't
    specifically recognize as transient — is raised immediately, no
    retry, since no other key would fare differently. Raises the last
    exception if every key is exhausted.
    """
    order = _rotation_order()
    if not order:
        raise RuntimeError("No GEMINI_API_KEY configured.")

    last_exc: Exception | None = None
    for key in order:
        client = _client_for(key)
        for attempt in range(len(_RETRY_BACKOFF_S) + 1):
            try:
                return fn(client)
            except Exception as exc:
                if is_quota_error(exc) or is_key_specific_auth_error(exc):
                    _mark_exhausted(key)
                    last_exc = exc
                    break  # this key is done; move to the next one
                if not _is_transient_error(exc):
                    raise
                last_exc = exc
                if _is_timeout_error(exc) or attempt == len(_RETRY_BACKOFF_S):
                    break  # don't retry a slow timeout; try the next key instead
                time.sleep(_RETRY_BACKOFF_S[attempt])
    assert last_exc is not None
    raise last_exc
