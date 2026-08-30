"""
Pluggable AI-text-detection providers.

Why this exists
---------------
Measured on a controlled corpus (see `samples/eval/` and
`backend/test_detector_eval.py`), the single built-in heuristic scored 3/8
against known provenance while the hosted model scored 5/8. Neither is
reliable alone, and both were defeated by AI text written in a human
register. Rather than trusting one number, the app should be able to run
several independent detectors and show where they agree.

Adding a provider
-----------------
Subclass `Detector`, implement `available()` and `detect()`, and register it
in `registry.py`. Nothing else in the app needs to change — `run_all()`
discovers whatever is registered and skips providers that aren't configured.

Cost note: every provider shipped here is FREE. `HeuristicDetector` and
`BinocularsDetector` run entirely on local models. Hosted providers are
opt-in and stay disabled unless their key is present in the environment.
"""
from app.detectors.base import Detector, DetectorResult, DetectorVerdict
from app.detectors.registry import available_detectors, run_all

__all__ = [
    "Detector",
    "DetectorResult",
    "DetectorVerdict",
    "available_detectors",
    "run_all",
]
