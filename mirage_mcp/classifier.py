"""
Rule-based fingerprint classifier: matches an agent's probe response text
against the pattern bank in signatures.py and reports the best-scoring
label, or "indeterminate" when nothing clears the confidence threshold.

Never silently drops a response it can't classify — an indeterminate verdict
is a first-class result, not an error, matching the verdict discipline used
elsewhere in Mirage's sensors.
"""

from dataclasses import dataclass, field

from mirage_mcp.signatures import CONFIDENCE_THRESHOLD, SIGNATURE_BANK

INDETERMINATE = "indeterminate"


@dataclass(frozen=True)
class Verdict:
    label: str
    confidence: float
    matched_signatures: list[str] = field(default_factory=list)


def classify(response_text: str) -> Verdict:
    """Score response_text against every signature and return the
    highest-confidence label, or an indeterminate verdict."""
    scores: dict[str, float] = {}
    matches: dict[str, list[str]] = {}

    for sig in SIGNATURE_BANK:
        if sig.pattern.search(response_text):
            scores[sig.label] = scores.get(sig.label, 0.0) + sig.weight
            matches.setdefault(sig.label, []).append(sig.pattern.pattern)

    if not scores:
        return Verdict(label=INDETERMINATE, confidence=0.0)

    best_label = max(scores, key=lambda label: scores[label])
    best_score = min(scores[best_label], 1.0)

    if best_score < CONFIDENCE_THRESHOLD:
        return Verdict(label=INDETERMINATE, confidence=best_score)

    return Verdict(
        label=best_label,
        confidence=best_score,
        matched_signatures=matches[best_label],
    )
