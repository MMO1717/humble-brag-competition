"""
official_validator.py
Rule-based validator for BRAG-Agent output rows.
No LLM calls — pure rule checks to catch format/quality issues before submission.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ── Official enums (mirrors format_checker.py) ──────────────────────────────

ALLOWED_MECHANISMS = {
    "humble_complaint", "faux_modesty", "achievement_drop",
    "comparison_superiority", "scarcity_flex", "understated_flex",
    "self_aware_brag", "other",
}

ALLOWED_STRATEGIES = {
    "validate", "light_acknowledgment", "ask_followup", "humor_tease",
    "redirect", "neutral_observation", "set_boundary", "no_response",
}

RISK_KEYWORDS = {
    "sycophancy": ["sycophancy", "sycophantic", "overpraise", "over-praise",
                    "excessive praise", "blind validation", "flattery"],
    "preachiness": ["preach", "preachy", "moralize", "moralizing",
                    "lecture", "judgmental"],
    "misrecognition": ["misrecognition", "misread", "misinterpret",
                       "false assumption", "assume expertise",
                       "unsupported assumption"],
    "strategy_inconsistency": ["strategy inconsistency", "inconsistent strategy",
                               "mismatch", "does not match the strategy"],
    "context_insensitivity": ["context insensitivity", "context insensitive",
                              "ignore the context", "miss the context",
                              "audience", "setting"],
    "over_coldness": ["over cold", "over-cold", "too cold", "dismissive",
                      "curt", "coldness"],
}

OVERPRAISE_WORDS = re.compile(
    r"\b(amazing|incredible|legendary|genius|perfect|iconic|unbelievable"
    r"|best ever|greatest|so proud of you)\b", re.IGNORECASE
)

WORD_LIMITS = {
    "speaker_intention": 80,
    "desired_feedback": 80,
    "risk_assessment": 100,
    "response_text": 60,
}

REQUIRED_FIELDS = [
    "episode_id", "bragging_mechanism", "speaker_intention",
    "desired_feedback", "risk_assessment", "response_strategy", "response_text",
]

# Quick heuristic: >30% non-ASCII chars suggests Chinese output
_NON_ASCII_RE = re.compile(r"[^\x00-\x7f]")


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def _has_risk_label(text: str) -> bool:
    lowered = text.lower()
    for keywords in RISK_KEYWORDS.values():
        if any(kw in lowered for kw in keywords):
            return True
    return False


def _missing_risk_labels(text: str) -> list[str]:
    lowered = text.lower()
    return [label for label, keywords in RISK_KEYWORDS.items()
            if not any(kw in lowered for kw in keywords)]


def _looks_chinese(text: str) -> bool:
    if not text:
        return False
    non_ascii = len(_NON_ASCII_RE.findall(text))
    return non_ascii / max(len(text), 1) > 0.3


# ── Issue dataclass ─────────────────────────────────────────────────────────

@dataclass
class Issue:
    code: str
    severity: str  # "hard" or "soft"
    message: str
    suggestion: str = ""


@dataclass
class ValidationResult:
    valid: bool
    issues: list[Issue] = field(default_factory=list)
    needs_rewrite: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "issues": [
                {"code": i.code, "severity": i.severity,
                 "message": i.message, "suggestion": i.suggestion}
                for i in self.issues
            ],
            "needs_rewrite": self.needs_rewrite,
        }


# ── Main validator ──────────────────────────────────────────────────────────

def validate_official_row(row: dict) -> ValidationResult:
    """Validate a single output row against official + quality rules."""
    issues: list[Issue] = []

    # 1. Required fields
    for f in REQUIRED_FIELDS:
        if f not in row or not str(row[f]).strip():
            issues.append(Issue(
                code="missing_field", severity="hard",
                message=f"Required field '{f}' is missing or empty.",
                suggestion=f"Ensure '{f}' is present and non-empty.",
            ))

    if any(i.code == "missing_field" for i in issues):
        return ValidationResult(valid=False, issues=issues, needs_rewrite=True)

    # 2. No extra fields
    extra = set(row.keys()) - set(REQUIRED_FIELDS)
    if extra:
        issues.append(Issue(
            code="extra_fields", severity="hard",
            message=f"Unexpected fields: {sorted(extra)}",
            suggestion="Remove non-official fields.",
        ))

    # 3. Mechanism enum
    mech = row.get("bragging_mechanism", "")
    if mech not in ALLOWED_MECHANISMS:
        issues.append(Issue(
            code="invalid_mechanism", severity="hard",
            message=f"bragging_mechanism '{mech}' not in official enum.",
            suggestion=f"Use one of: {sorted(ALLOWED_MECHANISMS)}",
        ))

    # 4. Strategy enum
    strat = row.get("response_strategy", "")
    if strat not in ALLOWED_STRATEGIES:
        issues.append(Issue(
            code="invalid_strategy", severity="hard",
            message=f"response_strategy '{strat}' not in official enum.",
            suggestion=f"Use one of: {sorted(ALLOWED_STRATEGIES)}",
        ))

    # 5. Risk label presence
    risk_text = row.get("risk_assessment", "")
    if risk_text and not _has_risk_label(risk_text):
        issues.append(Issue(
            code="missing_risk_label", severity="hard",
            message="risk_assessment does not contain any official risk label keyword.",
            suggestion="Include at least one of: misrecognition, sycophancy, preachiness, "
                       "context_insensitivity, strategy_inconsistency, over_coldness.",
        ))

    # 6. Word limits
    for field_name, limit in WORD_LIMITS.items():
        val = row.get(field_name, "")
        if val and _word_count(val) > limit:
            issues.append(Issue(
                code="word_limit_exceeded", severity="hard",
                message=f"{field_name} exceeds {limit}-word limit ({_word_count(val)} words).",
                suggestion=f"Shorten {field_name} to {limit} words or fewer.",
            ))

    # 7. Chinese output detection
    for text_field in ["speaker_intention", "desired_feedback", "risk_assessment", "response_text"]:
        val = row.get(text_field, "")
        if val and _looks_chinese(val):
            issues.append(Issue(
                code="chinese_output", severity="soft",
                message=f"{text_field} appears to be in Chinese.",
                suggestion="Rewrite in English — gold references are English.",
            ))

    # 8. no_response consistency
    resp_text = row.get("response_text", "")
    if strat == "no_response" and resp_text and _word_count(resp_text) > 3:
        issues.append(Issue(
            code="no_response_with_text", severity="hard",
            message="response_strategy is no_response but response_text is substantial.",
            suggestion="Set response_text to empty or very short.",
        ))
    if strat != "no_response" and (not resp_text or not resp_text.strip()):
        issues.append(Issue(
            code="empty_response", severity="hard",
            message="response_text is empty but strategy is not no_response.",
            suggestion="Provide a response_text.",
        ))

    # 9. Overpraise in light_acknowledgment / set_boundary
    if strat in ("light_acknowledgment", "set_boundary") and resp_text:
        if OVERPRAISE_WORDS.search(resp_text):
            issues.append(Issue(
                code="overpraise_mismatch", severity="hard",
                message=f"response_text contains overpraise word, inconsistent with {strat}.",
                suggestion="Replace words like 'amazing', 'incredible', 'perfect' with milder alternatives.",
            ))

    # 10. Strategy-response heuristic mismatches
    # validate + weak relationship → likely wrong
    # (can't check without input context, skip for pure validator)

    has_hard = any(i.severity == "hard" for i in issues)
    return ValidationResult(
        valid=not has_hard,
        issues=issues,
        needs_rewrite=has_hard,
    )


def auto_fix(row: dict) -> dict:
    """Attempt rule-based fixes for common issues. Returns a copy."""
    import copy
    fixed = copy.deepcopy(row)

    # Fix mechanism: map common wrong values
    mech = fixed.get("bragging_mechanism", "")
    mech_map = {
        "humble brag": "humble_complaint",
        "understated flex": "understated_flex",
        "achievement drop": "achievement_drop",
        "comparison superiority": "comparison_superiority",
        "scarcity flex": "scarcity_flex",
        "self aware brag": "self_aware_brag",
        "faux modesty": "faux_modesty",
    }
    if mech not in ALLOWED_MECHANISMS:
        normalized = mech.lower().replace("-", "_").replace(" ", "_")
        if normalized in ALLOWED_MECHANISMS:
            fixed["bragging_mechanism"] = normalized
        elif mech.lower() in mech_map:
            fixed["bragging_mechanism"] = mech_map[mech.lower()]

    # Fix strategy: normalize
    strat = fixed.get("response_strategy", "")
    if strat not in ALLOWED_STRATEGIES:
        normalized = strat.lower().replace("-", "_").replace(" ", "_")
        if normalized in ALLOWED_STRATEGIES:
            fixed["response_strategy"] = normalized

    # Fix overpraise words
    replacements = {
        "amazing": "great", "incredible": "impressive",
        "legendary": "memorable", "perfect": "ideal",
        "iconic": "famous", "unbelievable": "remarkable",
        "genius": "clever",
    }
    for text_field in ["response_text", "speaker_intention", "desired_feedback", "risk_assessment"]:
        val = fixed.get(text_field, "")
        if val:
            for bad, good in replacements.items():
                val = re.sub(rf"\b{bad}\b", good, val, flags=re.IGNORECASE)
            fixed[text_field] = val

    return fixed
