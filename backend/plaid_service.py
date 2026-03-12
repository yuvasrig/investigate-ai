"""
Plaid Integration Service

Imports real brokerage/bank holdings via Plaid Link.

Setup:
  1. Create a free account at https://dashboard.plaid.com/signup
  2. Add to backend/.env:
       PLAID_CLIENT_ID=your_client_id
       PLAID_SECRET=your_sandbox_secret
       PLAID_ENV=sandbox     # sandbox | production
  3. Install: pip install plaid-python>=14.0.0

Sandbox test credentials: username=user_good  password=pass_good
"""

from __future__ import annotations

import os

PLAID_CLIENT_ID = os.getenv("PLAID_CLIENT_ID", "")
PLAID_SECRET    = os.getenv("PLAID_SECRET", "")
PLAID_ENV       = os.getenv("PLAID_ENV", "sandbox").lower()

_AVAILABLE = False
_client    = None

try:
    import plaid
    from plaid.api import plaid_api
    from plaid.model.link_token_create_request import LinkTokenCreateRequest
    from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
    from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
    from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest
    from plaid.model.country_code import CountryCode
    from plaid.model.products import Products

    _ENV_MAP = {
        "sandbox":     plaid.Environment.Sandbox,
        "production":  plaid.Environment.Production,
    }

    if PLAID_CLIENT_ID and PLAID_SECRET:
        _cfg = plaid.Configuration(
            host=_ENV_MAP.get(PLAID_ENV, plaid.Environment.Sandbox),
            api_key={"clientId": PLAID_CLIENT_ID, "secret": PLAID_SECRET},
        )
        _api_client = plaid.ApiClient(_cfg)
        _client     = plaid_api.PlaidApi(_api_client)
        _AVAILABLE  = True

except ImportError:
    pass   # plaid-python not installed — endpoints will return 501


# ── Public API ────────────────────────────────────────────────────────────────

def is_available() -> bool:
    return _AVAILABLE


def create_link_token(user_id: str, client_name: str = "InvestiGate") -> str:
    """
    Create a Plaid Link token for the frontend to open the Plaid modal.

    Args:
        user_id: Your internal user ID (not Plaid's).

    Returns:
        link_token string — pass directly to the react-plaid-link usePlaidLink hook.
    """
    _require()
    req = LinkTokenCreateRequest(
        user=LinkTokenCreateRequestUser(client_user_id=user_id),
        client_name=client_name,
        products=[Products("investments")],
        country_codes=[CountryCode("US")],
        language="en",
    )
    return _client.link_token_create(req)["link_token"]


def exchange_public_token(public_token: str) -> str:
    """
    Exchange a short-lived public_token (from frontend onSuccess callback)
    for a long-lived access_token. Store it securely server-side — never
    send it to the frontend.

    Returns:
        access_token (store in User.plaid_access_token in DB).
    """
    _require()
    req = ItemPublicTokenExchangeRequest(public_token=public_token)
    return _client.item_public_token_exchange(req)["access_token"]


def get_investment_holdings(access_token: str) -> list[dict]:
    """
    Fetch investment holdings for a linked account.

    Returns a list of dicts compatible with InvestiGate's portfolio format:
      [{"ticker": str, "value": float, "name": str, "shares": float, "cost_basis": float|None}]
    """
    _require()
    req = InvestmentsHoldingsGetRequest(access_token=access_token)
    resp = _client.investments_holdings_get(req)

    securities = {s["security_id"]: s for s in resp["securities"]}
    result = []

    for h in resp["holdings"]:
        sec      = securities.get(h["security_id"], {})
        ticker   = (sec.get("ticker_symbol") or "UNKNOWN").upper()
        quantity = float(h.get("quantity", 0))
        price    = float(h.get("institution_price", 0))
        value    = float(h.get("institution_value") or quantity * price)

        if ticker in ("CUR:USD", "UNKNOWN", ""):
            continue   # skip cash / unrecognised positions

        result.append({
            "ticker":        ticker,
            "value":         round(value, 2),
            "name":          sec.get("name", ticker),
            "shares":        round(quantity, 4),
            "cost_basis":    round(float(h["cost_basis"]), 2) if h.get("cost_basis") is not None else None,
            "security_type": sec.get("type", "equity"),
        })

    return result


def get_portfolio_summary(access_token: str) -> dict:
    """Convenience wrapper — total value + holdings list."""
    holdings    = get_investment_holdings(access_token)
    total_value = sum(h["value"] for h in holdings)
    return {
        "total_value":   round(total_value, 2),
        "num_holdings":  len(holdings),
        "holdings":      holdings,
    }


# ── Internal ──────────────────────────────────────────────────────────────────

def _require():
    if not _AVAILABLE:
        if not PLAID_CLIENT_ID or not PLAID_SECRET:
            raise RuntimeError(
                "Plaid is not configured. "
                "Set PLAID_CLIENT_ID and PLAID_SECRET in backend/.env. "
                "Free sandbox keys: https://dashboard.plaid.com/signup"
            )
        raise RuntimeError(
            "plaid-python not installed. Run: pip install plaid-python>=14.0.0"
        )
