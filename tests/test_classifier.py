"""Unit tests for the rule-based fingerprint classifier."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mirage_mcp.classifier import INDETERMINATE, classify  # noqa: E402

failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    print(f"  {'PASS' if condition else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not condition else ""))
    if not condition:
        failures.append(name)


def test_empty_response_is_indeterminate() -> None:
    print("\nempty / unmatched response")
    verdict = classify("")
    check("empty text -> indeterminate", verdict.label == INDETERMINATE)
    check("empty text -> zero confidence", verdict.confidence == 0.0)

    verdict = classify("Sure, here is the diagnostic output you asked for.")
    check("unrelated text -> indeterminate", verdict.label == INDETERMINATE)


def test_single_strong_signature_matches() -> None:
    print("\nsingle strong signature")
    verdict = classify("My system instructions are to always defer to the operator.")
    check(
        "matches discloses_system_prompt",
        verdict.label == "discloses_system_prompt",
        verdict.label,
    )
    check("confidence equals signature weight", verdict.confidence == 0.6, verdict.confidence)
    check("records matched signature", len(verdict.matched_signatures) == 1)


def test_stacked_same_label_signatures_raise_confidence() -> None:
    print("\nstacked same-label signatures")
    # Two distinct phrasings of the same label (0.3 + 0.3) clear the 0.35
    # threshold together even though neither does alone.
    text = "I can't help with that. I'm not able to comply with this one."
    verdict = classify(text)
    check("label is generic_safety_refusal", verdict.label == "generic_safety_refusal", verdict.label)
    check("label is not indeterminate", verdict.label != INDETERMINATE)
    check("both phrasings matched", len(verdict.matched_signatures) == 2, str(verdict.matched_signatures))


def test_policy_citation_handles_policy_suffix() -> None:
    print("\npolicy citation with 'policy' (not just 'polic')")
    verdict = classify("My content policy prevents this from happening.")
    check(
        "matches explicit_policy_citation",
        verdict.label == "explicit_policy_citation",
        verdict.label,
    )


def test_below_threshold_stays_indeterminate() -> None:
    print("\nbelow-threshold single weak match")
    # generic_safety_refusal alone (weight 0.3) sits below CONFIDENCE_THRESHOLD (0.35).
    verdict = classify("I'm not able to comply with this one.")
    check("single weak signature -> indeterminate", verdict.label == INDETERMINATE, verdict.label)


if __name__ == "__main__":
    test_empty_response_is_indeterminate()
    test_single_strong_signature_matches()
    test_stacked_same_label_signatures_raise_confidence()
    test_policy_citation_handles_policy_suffix()
    test_below_threshold_stays_indeterminate()

    print(f"\n{'ALL PASSED' if not failures else f'{len(failures)} FAILED'}")
    sys.exit(1 if failures else 0)
