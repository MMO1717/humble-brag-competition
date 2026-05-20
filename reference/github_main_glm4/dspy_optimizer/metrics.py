from __future__ import annotations


def exact_match(prediction: str, gold: str) -> float:
    return 1.0 if str(prediction).strip() == str(gold).strip() else 0.0


def strategy_score(prediction: str, preferred: str, acceptable: list[str] | None = None) -> float:
    acceptable = acceptable or []
    prediction = str(prediction).strip()
    if prediction == str(preferred).strip():
        return 1.0
    if prediction in acceptable:
        return 0.5
    return 0.0
