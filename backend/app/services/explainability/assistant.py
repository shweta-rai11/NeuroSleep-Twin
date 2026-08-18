"""The Research Assistant itself: narrates the structured context built by
context.py, via a local Ollama model (preferred — no key needed), a real
Anthropic call (if ANTHROPIC_API_KEY is set), or a deterministic template
fallback. All paths are constrained to the same rule — only narrate what's
in `context`, never invent a number or reach past it (README §5, §15, §22:
"only narrates structured, already-computed pipeline output — it never
reasons directly over raw signals").
"""

from dataclasses import dataclass, field

from app.core.config import get_settings

SYSTEM_PROMPT = """You are the NeuroSleep Twin Research Assistant. You narrate ONLY the JSON \
context you are given below — every number in your answer must come from that context. \
Never invent a number, never speculate about raw signals you cannot see, and never make a \
diagnostic or treatment claim. Every field name states its own unit or scale (e.g. a key \
ending in "_minutes" is minutes, "_pct" or one prefixed "pct_" is a percent, "mean_spo2" is a \
percent SpO2 reading, a bare 0-1 value like "sensitivity" is a proportion) — carry that unit \
into your answer exactly, never reinterpret it as a different unit. If the context doesn't \
contain something the question asks about, say so plainly rather than guessing. Keep answers \
to 2-4 sentences, plain language, research-prototype tone (not clinical authority)."""


@dataclass
class AssistantAnswer:
    answer: str
    configured: bool
    evidence: dict = field(default_factory=dict)


def _template_answer(context: dict, question: str) -> str:
    q = question.lower()

    if any(w in q for w in ["event", "apnea", "hypopnea", "candidate"]):
        re_ = context.get("respiratory_events")
        if not re_:
            return "No candidate respiratory events are available for this study — check that a respiratory/airflow channel is mapped."
        return (
            f"This study has {re_['total']} candidate respiratory events "
            f"({re_['apnea']} apnea-like, {re_['hypopnea']} hypopnea-like), "
            f"a rate of {re_['events_per_hour']} events/hour. These are machine-learning "
            f"estimates from an amplitude-envelope detector, not a clinical scoring."
        )

    if any(w in q for w in ["oxygen", "spo2", "desat", "saturation"]):
        ox = context.get("oxygen_burden")
        if not ox:
            return "No SpO2 channel is available for this study, so oxygen burden can't be computed."
        return (
            f"Mean SpO2 was {ox['mean_spo2']}% (minimum {ox['min_spo2']}%), with "
            f"{ox['pct_time_below_90']}% of the recording spent below 90%. The oxygen "
            f"desaturation index (ODI) was {ox['odi']} dips/hour."
        )

    if any(w in q for w in ["stage", "sleep", "hypnogram", "rem", "n1", "n2", "n3", "wake"]):
        stages = context.get("sleep_stage_minutes")
        if not stages:
            return "No ground-truth sleep-stage annotations are available for this study."
        parts = ", ".join(f"{k} {v}min" for k, v in stages.items())
        return f"Sleep stage breakdown (from the dataset's own annotations): {parts}."

    if any(w in q for w in ["benchmark", "accuracy", "performance", "sensitiv", "specific", "auroc"]):
        bm = context.get("benchmark_vs_ground_truth")
        if not bm:
            return "No ground-truth annotations are available to benchmark against for this study."
        return (
            f"Against this study's ground-truth epoch annotations, the detector reached "
            f"sensitivity {bm['sensitivity']}, specificity {bm['specificity']}, "
            f"precision {bm['precision']}, and AUROC {bm['auroc']}."
        )

    # Fallback: a general summary of whatever is available.
    study = context.get("study", {})
    lines = [f"{study.get('record_name', 'This study')} is {study.get('duration_minutes')} minutes long."]
    if "respiratory_events" in context:
        lines.append(f"{context['respiratory_events']['total']} candidate respiratory events were detected.")
    if "oxygen_burden" in context:
        lines.append(f"Mean SpO2 was {context['oxygen_burden']['mean_spo2']}%.")
    if "sleep_stage_minutes" in context:
        lines.append("Ground-truth sleep-stage annotations are available.")
    if "benchmark_vs_ground_truth" in context:
        lines.append(f"Benchmarked AUROC vs. ground truth: {context['benchmark_vs_ground_truth']['auroc']}.")
    return " ".join(lines)


def _call_anthropic(context: dict, question: str, api_key: str, model: str) -> str:
    import json

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=400,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Context:\n{json.dumps(context, indent=2)}\n\nQuestion: {question}",
            }
        ],
    )
    return "".join(block.text for block in message.content if block.type == "text")


def _call_ollama(context: dict, question: str, base_url: str, model: str) -> str:
    import json

    import httpx

    response = httpx.post(
        f"{base_url}/api/chat",
        json={
            "model": model,
            "stream": False,
            "think": False,  # hybrid-reasoning models (qwen3, ...) — narration doesn't need a thinking trace
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Context:\n{json.dumps(context, indent=2)}\n\nQuestion: {question}"},
            ],
        },
        timeout=90.0,
    )
    response.raise_for_status()
    return response.json()["message"]["content"].strip()


def answer_question(context: dict, question: str) -> AssistantAnswer:
    settings = get_settings()

    if settings.ollama_model:
        try:
            text = _call_ollama(context, question, settings.ollama_base_url, settings.ollama_model)
            return AssistantAnswer(answer=text, configured=True, evidence=context)
        except Exception:  # noqa: BLE001 — fall through to the next provider rather than fail the request
            pass

    if settings.anthropic_api_key:
        try:
            text = _call_anthropic(context, question, settings.anthropic_api_key, settings.anthropic_model)
            return AssistantAnswer(answer=text, configured=True, evidence=context)
        except Exception as exc:  # noqa: BLE001 — fall back rather than fail the request
            return AssistantAnswer(
                answer=f"(Model call failed, falling back to template narration: {exc})\n\n" + _template_answer(context, question),
                configured=True, evidence=context,
            )

    return AssistantAnswer(answer=_template_answer(context, question), configured=False, evidence=context)
