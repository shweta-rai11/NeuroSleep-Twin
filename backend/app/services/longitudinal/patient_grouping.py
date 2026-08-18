import re

_MITBIH_NIGHT_SUFFIX = re.compile(r"^(slp\d+)[ab]$")


def patient_key(dataset_id: str, record_name: str) -> str:
    """Groups multi-night recordings from the same person. Only MIT-BIH
    PSG's explicit 'a'/'b' suffix (e.g. slp01a/slp01b) denotes a second
    night from the same patient — records without that suffix (e.g.
    slp67x) are each their own patient, never merged by guesswork."""
    if dataset_id == "mitbih-psg":
        match = _MITBIH_NIGHT_SUFFIX.match(record_name)
        if match:
            return match.group(1)
    return f"{dataset_id}:{record_name}"
