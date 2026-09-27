"""
Agent 1 — Smart Routing (problem P11: misrouting by region, language, complexity).

Why: routing only on product category + severity sends APAC cases to
engineers asleep in another time zone, and German/Spanish/Japanese cases to
engineers who can't read them. Every misroute adds a reassignment hop, hurts
Time to First Response, and is the first impression the customer gets.

How: deterministic rules first (free, auditable, instant) — country -> region,
script/lexicon -> language, severity/premium -> tier, licensing intent ->
licensing queue. An LLM (budget tier) is used only when the language or
intent is ambiguous. The agent RECOMMENDS a queue; the routing platform's
skill-based rules apply it once validated in pilot (see governance/policy.py).
"""

from __future__ import annotations
import re

REGION = {"US": "AMER", "CA": "AMER", "BR": "AMER", "MX": "AMER",
          "GB": "EMEA", "IE": "EMEA", "DE": "EMEA", "AT": "EMEA", "CH": "EMEA", "FR": "EMEA", "BE": "EMEA",
          "ES": "EMEA", "PT": "EMEA", "NL": "EMEA", "IT": "EMEA", "SE": "EMEA", "PL": "EMEA", "AE": "EMEA", "ZA": "EMEA",
          "AR": "AMER", "CL": "AMER", "CO": "AMER",
          "JP": "APAC", "AU": "APAC", "SG": "APAC", "IN": "APAC", "NZ": "APAC", "KR": "APAC", "MY": "APAC", "PH": "APAC"}

_LANG_HINTS = {
    "DE": re.compile(r"\b(die|der|und|bitte|nicht|verbindung|helfen|uns)\b", re.I),
    "ES": re.compile(r"\b(el|la|los|no|conector|origen|datos|error de|por favor)\b", re.I),
    "FR": re.compile(r"\b(le|les|nous|ne|pas|connexion|merci)\b", re.I),
}
_JA = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")
SUPPORTED_LANG_QUEUES = {"EN", "DE", "ES", "JA"}   # languages with staffed coverage
LICENSING = re.compile(r"\b(renew|renewal|seats?|license key|licen[cs]e|activation|subscription|invoice)\b", re.I)


def detect_language(text: str) -> str:
    if _JA.search(text):
        return "JA"
    scores = {lang: len(rx.findall(text)) for lang, rx in _LANG_HINTS.items()}
    lang, score = max(scores.items(), key=lambda kv: kv[1])
    return lang if score >= 2 else "EN"


def route(subject: str, body: str, country: str, severity: int, premium: bool) -> dict:
    text = f"{subject} {body}"
    reasons = []
    if severity == 1:
        return {"queue": "CORE-SEV1", "reasons": ["Severity 1 -> core team per support model"]}
    if premium:
        return {"queue": "CORE-PREMIUM", "reasons": ["Premium entitlement -> core team per support model"]}
    if LICENSING.search(text):
        return {"queue": "LICENSING", "reasons": ["Licensing/renewal intent detected"]}
    region = REGION.get(country, "AMER")
    lang = detect_language(text)
    reasons.append(f"Country {country} -> region {region}")
    reasons.append(f"Detected language {lang}")
    if lang not in SUPPORTED_LANG_QUEUES:
        reasons.append(f"No staffed {lang} queue -> English queue in region with translation assist")
        lang = "EN"
    return {"queue": f"L1-{region}-{lang}", "reasons": reasons}
