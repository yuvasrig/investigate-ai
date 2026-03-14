import re

from schemas import IntentRouterResult

# Tickers whose business model is directly exposed to an AI disruption scenario —
# automatically inject that scenario even when the user_query doesn't mention AI.
_TICKER_SCENARIOS: dict[str, list[str]] = {
    # Consulting / IT services — at direct risk of AI displacing knowledge work
    "ACN":  ["AI Disruption Analog"],
    "IBM":  ["AI Disruption Analog"],
    "WIT":  ["AI Disruption Analog"],
    "CTSH": ["AI Disruption Analog"],
    "INFY": ["AI Disruption Analog"],
    "TCS":  ["AI Disruption Analog"],
    "EPAM": ["AI Disruption Analog"],
    "GLOB": ["AI Disruption Analog"],
    # Legal / research platforms
    "LSE":  ["AI Disruption Analog"],
    "TRI":  ["AI Disruption Analog"],
    # Big-4 adjacent: staffing & outsourcing
    "MAN":  ["AI Disruption Analog"],
    "ADP":  ["AI Disruption Analog"],
}

_STOPWORDS = {
    "A", "AN", "AND", "ARE", "BE", "BUY", "DO", "FOR", "HOLD", "I", "IF", "IN",
    "IS", "IT", "ME", "MY", "OF", "ON", "OR", "SELL", "SHOULD", "THE", "TO",
    "WE", "WHAT", "WHY", "WITH", "YOU",
}

_SCENARIO_RULES: list[tuple[re.Pattern[str], str]] = [
    # AI disruption checked first — most specific pattern, prevents false matches
    (re.compile(
        r"\bai\b|\bartificial\s+intelligence\b|\bllm\b|\bclaude\b|\bgpt\b"
        r"|\bchatgpt\b|\bautomat|\bdisrupt|\breplace\b|\bdisplace\b"
        r"|\bconsult|\bwhite.?collar\b|\bknowledge\s+work",
        re.I,
    ), "AI Disruption Analog"),
    (re.compile(r"\btaiwan\b|\bchina\b|\bgeopolitic|\bpacific\b", re.I), "Geopolitical Escalation: Pacific Rim"),
    (re.compile(r"\bstagflation\b|\binflation\b|\brates?\b|\bfed\b", re.I), "Rates Shock / Stagflation Analog"),
    (re.compile(r"\brecession\b|\bslowdown\b|\bsoft landing\b|\bhard landing\b", re.I), "Demand Slowdown / Recession Analog"),
    (re.compile(r"\bai bubble\b|\bbubble\b|\bovervalued\b|\bvaluation\b", re.I), "Valuation Compression Analog"),
    (re.compile(r"\bregulat|\bantitrust\b|\blawsuit\b|\bban\b", re.I), "Regulatory Crackdown Analog"),
    (re.compile(r"\bsupply chain\b|\bshipping\b|\bshortage\b", re.I), "Supply Chain Shock Analog"),
    (re.compile(r"\benergy\b|\boil\b|\bgas\b|\bcommodity\b", re.I), "Commodity Shock Analog"),
    (re.compile(
        r"\bcrypto\b|\bbitcoin\b|\bbtc\b|\beth\b|\bethereum\b|\bsolana\b|\bsol\b"
        r"|\bblockchain\b|\bdefi\b|\bnft\b|\bftx\b|\bcoinbase\b|\bcoin\b"
        r"|\bhalving\b|\bstablecoin\b|\bweb3\b|\btoken\b|\bwallet\b",
        re.I,
    ), "Crypto Volatility Analog"),
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


def route_intent(user_query: str, ticker: str | None = None) -> IntentRouterResult:
    """Deterministic Tier-2 classifier for query routing and stress scenarios."""
    query = user_query.strip()
    scenarios = _extract_scenarios(query)

    # Auto-inject scenarios based on the ticker's known business exposure
    if ticker:
        for auto_scenario in _TICKER_SCENARIOS.get(ticker.upper(), []):
            if auto_scenario not in scenarios:
                scenarios.append(auto_scenario)

    return IntentRouterResult(
        target_asset=_extract_ticker(query) or ticker,
        scenarios=scenarios,
        requires_deep_dive=_requires_deep_dive(query, scenarios),
    )
