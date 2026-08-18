"""Best-effort channel-name -> standard signal-type mapping, with a
confidence score. Never applied silently: ingestion stores the guess and
its confidence, and the Channel Mapping screen (Phase 4) requires the user
to review/correct it before it's treated as confirmed (README §5).
"""

import re

STANDARD_SIGNAL_TYPES = [
    "eeg", "eog", "emg", "ecg", "resp", "airflow", "effort", "spo2", "bp", "position", "other",
]

# (regex matched against a normalized, lowercased channel name, standard type, confidence)
# Order matters — more specific patterns must come before generic catch-alls.
_RULES: list[tuple[re.Pattern[str], str, float]] = [
    (re.compile(r"^sao2$|^spo2$|^so2$"), "spo2", 0.95),
    (re.compile(r"\bsao2\b|\bspo2\b|\bso2\b|\bo2 ?sat\b"), "spo2", 0.85),
    (re.compile(r"^ecg$|^ekg$"), "ecg", 0.95),
    (re.compile(r"\becg\b|\bekg\b"), "ecg", 0.85),
    (re.compile(r"^eeg$"), "eeg", 0.95),
    (re.compile(r"\beeg\b"), "eeg", 0.85),
    (re.compile(r"\beog\b"), "eog", 0.85),
    (re.compile(r"\bemg\b|\bchin\b"), "emg", 0.8),
    (re.compile(r"\bbp\b|\bblood ?pressure\b"), "bp", 0.8),
    (re.compile(r"\bposition\b|\bbody ?pos\b"), "position", 0.85),
    (re.compile(r"\bairflow\b|\bnasal\b|\btherm(istor|ocouple)?\b|\bflow\b"), "airflow", 0.75),
    (re.compile(r"\beffort\b|\bthora(x|cic)\b|\babdomen?\b|\bchest\b|\bbelt\b"), "effort", 0.75),
    (re.compile(r"\bresp\w*\b"), "resp", 0.7),
]


def guess_signal_type(channel_name: str) -> tuple[str | None, float]:
    normalized = re.sub(r"[^a-z0-9]+", " ", channel_name.lower()).strip()
    for pattern, signal_type, confidence in _RULES:
        if pattern.search(normalized):
            return signal_type, confidence
    return None, 0.0
