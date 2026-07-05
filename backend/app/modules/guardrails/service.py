from __future__ import annotations

from app.modules.guardrails.guards import PIIGuard, PromptInjectionGuard, ToxicityGuard
from app.modules.guardrails.schemas import GuardReport


def evaluate_text(*, text: str) -> GuardReport:
    guards = [PromptInjectionGuard(), PIIGuard(), ToxicityGuard()]
    results = [g.evaluate(text) for g in guards]
    passed = all(r.passed for r in results)
    return GuardReport(passed=passed, results=results)


def should_block(report: GuardReport) -> bool:
    return not report.passed

