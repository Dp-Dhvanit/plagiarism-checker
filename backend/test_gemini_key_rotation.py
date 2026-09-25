"""
Test the multi-key Gemini rotation logic in app/gemini_keys.py in isolation,
using fake keys and simulated errors — no real network call, no real API key
required. This validates the rotation/fallback mechanism itself; it cannot
prove real Google accounts behave the same way, only that this project's
logic does what it claims to.

Usage:
  python test_gemini_key_rotation.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

os.environ["GEMINI_API_KEY"] = "fake_key_one,fake_key_two,fake_key_three"

from app import gemini_keys  # noqa: E402  (must come after the env var is set)

PASS = "PASS"
FAIL = "FAIL"
_results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    _results.append((name, condition, detail))
    print(f"[{PASS if condition else FAIL}] {name}" + (f" — {detail}" if detail else ""))


class FakeClient:
    def __init__(self, key: str):
        self.key = key


class QuotaError(Exception):
    def __str__(self) -> str:
        return "429 RESOURCE_EXHAUSTED: quota exceeded"


# Never construct a real google.genai.Client — these are fake key strings,
# and this test only exercises the rotation logic, not the SDK itself.
gemini_keys._client_for = lambda key: FakeClient(key)  # type: ignore[assignment]


def reset_state() -> None:
    """Fresh rotation state between tests — internal, but this is a
    white-box test of that internal state by design."""
    gemini_keys._clients.clear()
    gemini_keys._exhausted_until.clear()


def main() -> None:
    print("=" * 70)
    print("TEST A — key parsing and count")
    keys = gemini_keys._keys()
    check("three comma-separated keys parsed", keys == ["fake_key_one", "fake_key_two", "fake_key_three"], str(keys))
    check("is_configured() true with keys set", gemini_keys.is_configured())
    check("key_count() == 3", gemini_keys.key_count() == 3)

    print("\nTEST B — first key exhausted, falls back to second")
    reset_state()
    tried: list[str] = []

    def fn_first_fails(client: FakeClient):
        tried.append(client.key)
        if client.key == "fake_key_one":
            raise QuotaError()
        return f"answered by {client.key}"

    result = gemini_keys.call_with_rotation(fn_first_fails)
    check("result came from the second key", result == "answered by fake_key_two", result)
    check("first key was tried before falling back", tried == ["fake_key_one", "fake_key_two"], str(tried))

    print("\nTEST C — exhausted key is skipped on the NEXT call, not retried first")
    tried.clear()

    def fn_record(client: FakeClient):
        tried.append(client.key)
        return "ok"

    result = gemini_keys.call_with_rotation(fn_record)
    check("second call goes straight to key two", tried == ["fake_key_two"], str(tried))

    print("\nTEST D — every key exhausted raises the last error, not silently swallowed")
    reset_state()

    def fn_all_fail(client: FakeClient):
        raise QuotaError()

    raised = False
    try:
        gemini_keys.call_with_rotation(fn_all_fail)
    except QuotaError:
        raised = True
    check("QuotaError propagates when all keys exhausted", raised)

    print("\nTEST E — a non-quota error is NOT retried against other keys")
    reset_state()
    tried.clear()

    def fn_bad_request(client: FakeClient):
        tried.append(client.key)
        raise ValueError("malformed request — not a quota problem")

    raised = False
    try:
        gemini_keys.call_with_rotation(fn_bad_request)
    except ValueError:
        raised = True
    check("ValueError propagates immediately", raised)
    check("only the first key was tried (no pointless rotation)", tried == ["fake_key_one"], str(tried))

    print("\nTEST E2 — a key-specific 403 falls through to the NEXT key (not treated as universal)")
    reset_state()
    tried.clear()

    def fn_403_on_first(client: FakeClient):
        tried.append(client.key)
        if client.key == "fake_key_one":
            raise ValueError("403 PERMISSION_DENIED: Your project has been denied access.")
        return f"answered by {client.key}"

    result = gemini_keys.call_with_rotation(fn_403_on_first)
    check("result came from the second key despite key one's 403", result == "answered by fake_key_two", result)
    check("both keys were tried in order", tried == ["fake_key_one", "fake_key_two"], str(tried))

    print("\nTEST F — single-key behavior is unchanged (back-compat)")
    reset_state()
    os.environ["GEMINI_API_KEY"] = "only_one_key"
    tried.clear()

    def fn_single(client: FakeClient):
        tried.append(client.key)
        return "single key answered"

    result = gemini_keys.call_with_rotation(fn_single)
    check("single configured key still works", result == "single key answered")
    check("exactly one key tried", tried == ["only_one_key"], str(tried))

    print("\n" + "=" * 70)
    total = len(_results)
    passed = sum(1 for _, ok, _ in _results if ok)
    print(f"{passed}/{total} checks passed")
    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    main()
