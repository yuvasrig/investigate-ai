"""
PDF export service for InvestiGate analysis reports.

Generates a clean, structured PDF from a stored AnalysisResponse dict.
Uses fpdf2 (lightweight, no system dependencies).
"""

from __future__ import annotations

from typing import Any

from fpdf import FPDF

# ── Colour palette (RGB) ──────────────────────────────────────────────────────

_BULL_RGB   = (34, 197, 94)
_BEAR_RGB   = (239, 68, 68)
_STRAT_RGB  = (99, 102, 241)
_ACCENT_RGB = (99, 102, 241)
_DARK_RGB   = (17, 24, 39)
_MUTED_RGB  = (107, 114, 128)
_RULE_RGB   = (220, 220, 220)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe(v: Any, fallback: str = "N/A") -> str:
    if v is None:
        return fallback
    s = str(v).strip()
    return s if s else fallback


def _money(v: Any) -> str:
    try:
        return f"${float(v):,.0f}"
    except (TypeError, ValueError):
        return _safe(v)


def _printable(text: str) -> str:
    """Strip any character outside Latin-1 (Helvetica only covers cp1252)."""
    return text.encode("latin-1", errors="replace").decode("latin-1")


# ── PDF class ─────────────────────────────────────────────────────────────────

class _PDF(FPDF):
    def header(self):
        pass

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*_MUTED_RGB)
        self.cell(0, 8, f"InvestiGate  |  Page {self.page_no()}", align="C")

    # ── Primitives ────────────────────────────────────────────────────────────

    def hr(self, gap_before: float = 2, gap_after: float = 3):
        self.ln(gap_before)
        self.set_draw_color(*_RULE_RGB)
        self.set_line_width(0.25)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(gap_after)

    def section_header(self, prefix: str, title: str,
                       rgb: tuple[int, int, int] = _DARK_RGB):
        """Colored prefix badge + section title on one line."""
        self.ln(3)
        # prefix badge (e.g. "BULL", "BEAR")
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*rgb)
        self.set_draw_color(*rgb)
        self.set_line_width(0.4)
        self.cell(0, 6, f"[ {prefix} ]  {title}", ln=True)
        self.line(self.l_margin, self.get_y(),
                  self.l_margin + 50, self.get_y())
        self.ln(3)
        self.set_text_color(*_DARK_RGB)

    def kv(self, label: str, value: str, label_w: float = 48):
        """Label + value on the same row; value wraps if needed."""
        printable_value = _printable(value)
        available = self.w - self.l_margin - self.r_margin - label_w
        if available < 10:
            label_w = 30
            available = self.w - self.l_margin - self.r_margin - label_w

        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*_MUTED_RGB)
        # Save Y before rendering label
        y_before = self.get_y()
        self.cell(label_w, 5, _printable(label.upper()), ln=False)

        self.set_font("Helvetica", "", 9)
        self.set_text_color(*_DARK_RGB)
        self.multi_cell(available, 5, printable_value)

        # Ensure we're below both columns
        if self.get_y() < y_before + 5:
            self.ln(5 - (self.get_y() - y_before))

    def bullet_item(self, text: str, color: tuple[int, int, int] = _MUTED_RGB):
        indent = 5
        available = self.w - self.l_margin - self.r_margin - indent
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*color)
        self.cell(indent, 5, "-", ln=False)
        self.set_text_color(*_DARK_RGB)
        self.multi_cell(available, 5, _printable(text))

    def numbered_item(self, n: int, text: str,
                      color: tuple[int, int, int] = _ACCENT_RGB):
        indent = 7
        available = self.w - self.l_margin - self.r_margin - indent
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*color)
        self.cell(indent, 5, f"{n}.", ln=False)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*_DARK_RGB)
        self.multi_cell(available, 5, _printable(text))

    def body(self, text: str):
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*_MUTED_RGB)
        self.multi_cell(0, 5, _printable(text))
        self.ln(1)

    def progress_bar(self, label: str, pct: int):
        """Render a single progress-bar row."""
        label_w = 55
        pct_w   = 12
        # guard
        page_w = self.w - self.l_margin - self.r_margin
        bar_total = max(page_w - label_w - pct_w - 4, 10)

        self.set_font("Helvetica", "", 8)
        self.set_text_color(*_MUTED_RGB)
        self.cell(label_w, 5, _printable(label), ln=False)

        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*_DARK_RGB)
        self.cell(pct_w, 5, f"{pct}%", ln=False)

        bar_x = self.get_x() + 2
        bar_y = self.get_y() + 1
        bar_filled = bar_total * pct / 100

        self.set_draw_color(*_RULE_RGB)
        self.rect(bar_x, bar_y, bar_total, 3)
        if bar_filled > 0:
            self.set_fill_color(*_ACCENT_RGB)
            self.rect(bar_x, bar_y, bar_filled, 3, style="F")

        self.ln(6)


# ── Main generator ────────────────────────────────────────────────────────────

def generate_pdf(analysis: dict) -> bytes:
    """Return PDF bytes for the given analysis dict."""
    pdf = _PDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_margins(15, 15, 15)

    ticker   = _safe(analysis.get("ticker"))
    ts       = _safe(analysis.get("timestamp"))
    provider = _safe(analysis.get("llm_provider"))
    exec_t   = analysis.get("execution_time")
    market   = analysis.get("market_data") or {}

    company = _safe(market.get("longName") or market.get("shortName"), ticker)
    price   = market.get("currentPrice")
    price_s = f"${price:,.2f}" if price else "N/A"

    bull  = analysis.get("bull_analysis") or {}
    bear  = analysis.get("bear_analysis") or {}
    strat = analysis.get("strategist_analysis") or {}
    rec   = analysis.get("final_recommendation") or {}
    cbd   = rec.get("confidence_breakdown") or {}

    # ── Report header ─────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*_DARK_RGB)
    pdf.cell(0, 10, _printable(ticker), ln=True)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*_MUTED_RGB)
    pdf.cell(0, 5, _printable(company), ln=True)

    pdf.set_font("Helvetica", "", 8)
    meta = f"Price: {price_s}  |  {ts}  |  Provider: {provider}"
    if exec_t:
        meta += f"  |  Runtime: {exec_t}s"
    pdf.cell(0, 5, _printable(meta), ln=True)
    pdf.hr(gap_before=3, gap_after=4)

    # ── Executive summary ─────────────────────────────────────────────────────
    pdf.section_header("RECOMMENDATION", "Executive Summary", _ACCENT_RGB)

    action    = _safe(rec.get("action", "")).upper()
    amt       = _money(rec.get("recommended_amount"))
    conf      = _safe(rec.get("confidence_overall"))
    entry     = _safe(rec.get("entry_strategy"))
    risk_mgmt = _safe(rec.get("risk_management"))

    pdf.kv("Action",         action)
    pdf.kv("Amount",         amt)
    pdf.kv("Confidence",     f"{conf}%")
    pdf.kv("Entry Strategy", entry)
    pdf.kv("Risk Mgmt",      risk_mgmt)
    pdf.ln(2)
    pdf.body(_safe(rec.get("reasoning")))

    # ── Key factors ───────────────────────────────────────────────────────────
    pdf.hr()
    pdf.section_header("FACTORS", "Key Decision Factors", _ACCENT_RGB)
    for i, factor in enumerate((rec.get("key_factors") or []), 1):
        pdf.numbered_item(i, _safe(factor))

    # ── Confidence breakdown ──────────────────────────────────────────────────
    pdf.hr()
    pdf.section_header("CONFIDENCE", "Confidence Breakdown", _ACCENT_RGB)
    for key, val in cbd.items():
        label = key.replace("_", " ").title()
        pct   = max(0, min(100, int(val))) if isinstance(val, (int, float)) else 0
        pdf.progress_bar(label, pct)

    # ── Bull analyst ──────────────────────────────────────────────────────────
    pdf.hr()
    pdf.section_header("BULL", "Bull Analyst", _BULL_RGB)
    pdf.kv("Confidence",   f"{_safe(bull.get('confidence'))}/10")
    pdf.kv("Best Target",  _money(bull.get("best_case_target")))
    pdf.kv("Timeline",     _safe(bull.get("best_case_timeline")))
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*_DARK_RGB)
    pdf.cell(0, 5, "Competitive Advantages", ln=True)
    for adv in (bull.get("competitive_advantages") or []):
        pdf.bullet_item(adv, _BULL_RGB)

    pdf.ln(1)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(0, 5, "Growth Catalysts", ln=True)
    for cat in (bull.get("growth_catalysts") or []):
        pdf.bullet_item(cat)

    vj = bull.get("valuation_justification")
    if vj:
        pdf.ln(1)
        pdf.kv("Valuation", _safe(vj))

    # ── Bear analyst ──────────────────────────────────────────────────────────
    pdf.hr()
    pdf.section_header("BEAR", "Bear Analyst", _BEAR_RGB)
    pdf.kv("Confidence",   f"{_safe(bear.get('confidence'))}/10")
    pdf.kv("Worst Target", _money(bear.get("worst_case_target")))
    pdf.kv("Timeline",     _safe(bear.get("worst_case_timeline")))
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*_DARK_RGB)
    pdf.cell(0, 5, "Competition & Risks", ln=True)
    for threat in (bear.get("competition_threats") or []):
        pdf.bullet_item(threat, _BEAR_RGB)

    vc = bear.get("valuation_concerns")
    if vc:
        pdf.ln(1)
        pdf.kv("Valuation Concerns", _safe(vc))

    # ── Portfolio strategist ──────────────────────────────────────────────────
    pdf.hr()
    pdf.section_header("PORTFOLIO", "Portfolio Strategist", _STRAT_RGB)
    pdf.kv("Current Exposure",  _safe(strat.get("current_exposure")))
    pdf.kv("Conc. Risk",        _safe(strat.get("concentration_risk")))
    pdf.kv("Allocation",        _money(strat.get("recommended_allocation")))
    pdf.ln(2)

    reasoning_s = strat.get("reasoning")
    if reasoning_s:
        pdf.body(_safe(reasoning_s))

    alts = strat.get("alternative_options") or []
    if alts:
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*_DARK_RGB)
        pdf.cell(0, 5, "Alternatives", ln=True)
        for alt in alts:
            pdf.bullet_item(alt)

    # ── Disclaimer ────────────────────────────────────────────────────────────
    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 7)
    pdf.set_text_color(*_MUTED_RGB)
    pdf.multi_cell(
        0, 4,
        "This report is generated by InvestiGate, an AI-powered multi-agent investment analysis "
        "tool. It is for informational purposes only and does not constitute financial advice. "
        "Always consult a qualified financial advisor before making investment decisions.",
    )

    return bytes(pdf.output())
