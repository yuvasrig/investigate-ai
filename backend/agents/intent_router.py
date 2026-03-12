import re

from schemas import IntentRouterResult

_STOPWORDS = {
    "A", "AN", "AND", "ARE", "BE", "BUY", "DO", "FOR", "HOLD", "I", "IF", "IN",
    "IS", "IT", "ME", "MY", "OF", "ON", "OR", "SELL", "SHOULD", "THE", "TO",
    "WE", "WHAT", "WHY", "WITH", "YOU",
}

_SCENARIO_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\btaiwan\b|\bchina\b|\bgeopolitic|\bpacific\b", re.I), "Geopolitical Escalation: Pacific Rim"),
    (re.compile(r"\bstagflation\b|\binflation\b|\brates?\b|\bfed\b", re.I), "Rates Shock / Stagflation Analog"),
    (re.compile(r"\brecession\b|\bslowdown\b|\bsoft landing\b|\bhard landing\b", re.I), "Demand Slowdown / Recession Analog"),
    (re.compile(r"\bai bubble\b|\bbubble\b|\bovervalued\b|\bvaluation\b", re.I), "Valuation Compression Analog"),
    (re.compile(r"\bregulat|\bantitrust\b|\blawsuit\b|\bban\b", re.I), "Regulatory Crackdown Analog"),
    (re.compile(r"\bsupply chain\b|\bshipping\b|\bshortage\b", re.I), "Supply Chain Shock Analog"),
    (re.compile(r"\benergy\b|\boil\b|\bgas\b|\bcommodity\b", re.I), "Commodity Shock Analog"),
    (re.compile(r"\bcrypto\b|\bbitcoin\b|\beth\b", re.I), "Crypto Volatility Analog"),
]


def _extract_ticker(user_query: str) -> str | None:
    action_match = re.search(
        r"\b(?:buy|sell|hold|analyze|analyse|invest in|add to|trim|exit)\s+\$?([A-Za-z]{1,5})\b",
        user_query,
        re.I,
    )
    if action_match:
        return action_match.group(1).upper()

    for token in re.findall(r"\b[A-Z]{1,5}\b", user_query):
        normalized = token.upper()
        if normalized not in _STOPWORDS:
            return normalized
    return None


def _extract_scenarios(user_query: str) -> list[str]:
    scenarios: list[str] = []
    for pattern, label in _SCENARIO_RULES:
        if pattern.search(user_query):
            scenarios.append(label)
    return scenarios


def _requires_deep_dive(user_query: str, scenarios: list[str]) -> bool:
    return bool(
        scenarios
        or re.search(
            r"\b(should i|buy|sell|hold|analysis|analyze|invest|position|add more|trim)\b",
            user_query,
            re.I,
        )
    )


def route_intent(user_query: str) -> IntentRouterResult:
    """Deterministic Tier-2 classifier for query routing and stress scenarios."""
    query = user_query.strip()
    scenarios = _extract_scenarios(query)
    return IntentRouterResult(
        target_asset=_extract_ticker(query),
        scenarios=scenarios,
        requires_deep_dive=_requires_deep_dive(query, scenarios),
    )
