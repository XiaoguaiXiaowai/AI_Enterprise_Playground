from __future__ import annotations

import re

from app.modules.guardrails.schemas import GuardResult


class Guard:
    name: str

    def evaluate(self, text: str) -> GuardResult:
        raise NotImplementedError


class PromptInjectionGuard(Guard):
    name = "prompt_injection"

    _patterns = [
        r"\bignore\b.*\b(instruction|previous|system)\b",
        r"\b(system prompt|developer message)\b",
        r"\b(jailbreak|DAN|do anything now)\b",
        r"\bact as\b.*\b(system|developer)\b",
    ]

    def evaluate(self, text: str) -> GuardResult:
        lowered = text.lower()
        hits = []
        for p in self._patterns:
            if re.search(p, lowered):
                hits.append(p)
        passed = len(hits) == 0
        return GuardResult(
            name=self.name,
            passed=passed,
            score=0.0 if passed else 1.0,
            reasons=["prompt_injection_detected"] if not passed else [],
        )


class PIIGuard(Guard):
    name = "pii"

    _email = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
    _phone = re.compile(r"\b(\+?\d{1,3}[- ]?)?(\d{2,4}[- ]?)?\d{7,12}\b")
    _id_like = re.compile(r"\b\d{17}[\dXx]\b")
    _credit_card = re.compile(r"\b(?:\d[ -]*?){13,19}\b")

    def evaluate(self, text: str) -> GuardResult:
        reasons: list[str] = []
        if self._email.search(text):
            reasons.append("email")
        if self._phone.search(text):
            reasons.append("phone")
        if self._id_like.search(text):
            reasons.append("id_like")
        if self._credit_card.search(text):
            reasons.append("card_like")
        passed = len(reasons) == 0
        return GuardResult(
            name=self.name,
            passed=passed,
            score=0.0 if passed else 1.0,
            reasons=reasons,
        )


class ToxicityGuard(Guard):
    name = "toxicity"

    _keywords = [
        "kill you",
        "hate you",
        "stupid",
        "idiot",
        "moron",
        "die",
    ]

    def evaluate(self, text: str) -> GuardResult:
        lowered = text.lower()
        hits = [k for k in self._keywords if k in lowered]
        passed = len(hits) == 0
        return GuardResult(
            name=self.name,
            passed=passed,
            score=0.0 if passed else 1.0,
            reasons=hits,
        )

