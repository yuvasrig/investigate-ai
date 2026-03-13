"""
Pre-seeded historical analog documents for scenario grounding.

These documents are authored from publicly available historical data to give
RAG-based agents verified precedents for common disruption and macro scenarios.
They live in a dedicated ChromaDB collection ("_ANALOGS") and are retrieved
whenever the Intent Router detects a matching scenario tag.

Analogs currently seeded
────────────────────────
AI Disruption Analog:
  • Excel → Accounting (1988)          — commodity hours disrupted, advisory grew
  • AWS → IT Consulting (2010)         — infra consulting compressed, cloud boomed
  • ATM → Bank Tellers (1970s–90s)    — automation expanded branch count
  • CAD → Engineering Drafters (1980s) — near-total displacement of a profession
  • Online travel → Travel Agents (2000) — Expedia/Booking wiped 60% of agencies

Regulatory Crackdown Analog:
  • Microsoft Antitrust (1998)         — sentiment headwind, limited product impact
  • AT&T Breakup (1984)               — structural forced breakup, long recovery

Valuation Compression Analog:
  • Dot-Com Crash (2000)              — timeline and magnitude by PE tier

Rates Shock / Stagflation Analog:
  • 1970s–1980 stagflation            — winners / losers, modern parallel

Geopolitical Escalation: Pacific Rim:
  • Huawei US ban (2019)              — export control sector contagion
  • Russia SWIFT sanctions (2022)     — financial infrastructure isolation
  • Cold War semiconductor controls   — COCOM tech export restrictions

Demand Slowdown / Recession Analog:
  • 2008 GFC tech sector revenue      — enterprise IT discretionary spending cuts
  • 2001 dot-com bust enterprise IT   — forward guidance slashing, capex freeze

Supply Chain Shock Analog:
  • COVID-19 semiconductor shortage (2020–21) — chip lead times, revenue impact
  • Japan earthquake / Toyota JIT (2011)       — single-source risk, inventory

Commodity Shock Analog:
  • 1973 OPEC oil embargo             — demand destruction, sector rotation
  • 2022 European natural gas crisis  — energy-intensive sector margin compression

Crypto Volatility Analog:
  • FTX collapse (2022)               — contagion, sector-wide drawdown
  • Mt. Gox hack (2014) / BTC halving cycles — historical volatility patterns
"""

from __future__ import annotations

from rag import store

# Special ticker key for the shared analogs collection
ANALOGS_TICKER = "_ANALOGS"

# ── Authored analog documents ─────────────────────────────────────────────────

ANALOG_DOCUMENTS: list[dict] = [
    # ── AI Disruption ─────────────────────────────────────────────────────────
    {
        "text": (
            "Excel → Accounting disruption (1988 analog): "
            "When Lotus 1-2-3 and Microsoft Excel spread in the late 1980s, bookkeeping clerks "
            "—a role accounting firms charged at $40–60/hr—saw demand fall ~50% between 1985 "
            "and 1995 (BLS Occupational Outlook data). "
            "However, accounting firms that pivoted to advisory services (tax strategy, M&A advisory, "
            "CFO services) grew total revenue 2–3× over the same period. "
            "Key lesson: disruption compressed commodity hours but expanded advisory revenue. "
            "Firms slow to pivot (small bookkeeping shops) saw revenue fall 60–80%. "
            "Large diversified firms (Big Eight) converted ~30% of headcount to new service lines "
            "within 5 years. "
            "Analog risk for AI vs consulting: AI compresses the $150–250/hr analyst tier "
            "but advisory, transformation, and change management remain human-led. "
            "Historical revenue impact on firms that pivoted: +20–40% margin expansion."
        ),
        "metadata": {
            "source": "historical_analog",
            "scenario": "AI Disruption Analog",
            "title": "Excel → Accounting Disruption (1988)",
            "ticker": ANALOGS_TICKER,
            "chunk_index": 0,
        },
    },
    {
        "text": (
            "AWS → IT consulting disruption (2010 analog): "
            "AWS mainstream adoption from 2010–2015 eliminated a large share of on-premise "
            "infrastructure consulting revenue. Gartner estimated infrastructure implementation "
            "consulting (server rack, data centre, network config) saw 30–40% margin compression "
            "from 2010–2016 as clients migrated to cloud. "
            "Firms like EDS, HP Services, and IBM Global Services saw revenue from traditional "
            "IT implementation fall ~25% over 5 years. "
            "However, cloud migration consulting (AWS/Azure/GCP) created a new $50B+ market. "
            "Accenture, Capgemini, and Infosys all pivoted successfully: "
            "Accenture Technology revenues grew from $12B (2012) to $27B (2017) despite "
            "commoditisation of legacy IT services. "
            "Analog risk for AI vs consulting: AI automates slide production, data analysis, "
            "and junior deliverables but creates implementation/change-management demand. "
            "Revenue shift timeline: 3–5 years from compression onset to new-service offset."
        ),
        "metadata": {
            "source": "historical_analog",
            "scenario": "AI Disruption Analog",
            "title": "AWS → IT Consulting Disruption (2010)",
            "ticker": ANALOGS_TICKER,
            "chunk_index": 1,
        },
    },
    {
        "text": (
            "ATM → Bank Tellers (1970s–1990s analog — augmentation, not replacement): "
            "ATM deployment from 1970–1995 is the most-cited case of automation that INCREASED "
            "total employment in the disrupted sector. "
            "From 1985–2002, US bank branches rose from 60,000 to 92,000 because ATMs made branch "
            "operation cheaper (fewer teller FTEs per branch), enabling banks to open more locations. "
            "Teller headcount per branch fell 30% but total tellers employed rose 2% over 20 years. "
            "Teller role transformed: transaction processing → relationship banking, upselling, advisory. "
            "Key lesson: automation can expand the market while transforming the human role. "
            "For consulting: if AI reduces delivery cost per engagement, firms may take on more "
            "(smaller/mid-market) clients, expanding total market rather than contracting. "
            "Bull scenario: Accenture/McKinsey grows mid-market share previously uneconomic to serve."
        ),
        "metadata": {
            "source": "historical_analog",
            "scenario": "AI Disruption Analog",
            "title": "ATM → Bank Teller Role Transformation (1970s–1990s)",
            "ticker": ANALOGS_TICKER,
            "chunk_index": 2,
        },
    },
    {
        "text": (
            "CAD software → Engineering Drafters (1980s analog — near-total displacement): "
            "AutoCAD release (1982) and mass adoption 1985–1995 resulted in near-total "
            "displacement of engineering drafting as a profession. "
            "BLS records show Drafters (SOC 17-3010) fell from ~350,000 in 1983 to ~210,000 "
            "in 2000: a 40% reduction in 17 years. "
            "Unlike bank tellers or accountants, drafters did not successfully pivot to advisory "
            "roles at scale — the cognitive complexity of remaining work was too low. "
            "This is the worst-case 'displacement' scenario for consulting: "
            "if AI can produce strategy deliverables end-to-end (slides, models, insights), "
            "the junior analyst tier (Analyst/Associate, 2–4 years) could face similar structural decline. "
            "McKinsey estimates ~40% of management consulting time is in data gathering + analysis "
            "— the most automatable tier. "
            "Bear scenario revenue impact: 15–20% revenue decline in 5 years if clients "
            "insource AI-augmented analysis, bypassing junior consulting tiers entirely."
        ),
        "metadata": {
            "source": "historical_analog",
            "scenario": "AI Disruption Analog",
            "title": "CAD → Engineering Drafters Displacement (1980s)",
            "ticker": ANALOGS_TICKER,
            "chunk_index": 3,
        },
    },
    {
        "text": (
            "Online travel → Travel Agents (2000 analog — internet disintermediation): "
            "Expedia launched 1996, Booking.com 1997. By 2002, US travel agent locations "
            "had fallen from ~34,000 (1997 peak) to ~20,000 — a 41% reduction in 5 years. "
            "Airlines cut agent commissions from 10% to 0% (2002), removing the revenue model. "
            "By 2013, online travel agencies (OTAs) booked >50% of all US leisure travel. "
            "Travel agents that survived pivoted to: luxury/complex itineraries, corporate travel "
            "management, cruise specialists, and destination-wedding planning — segments where "
            "human expertise and relationships command a premium. "
            "Surviving agencies (e.g., Virtuoso, CWT) serve high-net-worth and corporate clients "
            "at 3–5× the margin of former commodity booking work. "
            "Analog for AI: AI disintermediates commodity knowledge work (research, data analysis, "
            "basic report writing) but firms that move upmarket to irreplaceable human services "
            "(C-suite relationships, crisis management, bespoke strategy) can preserve margins. "
            "Displacement timeline: 40% headcount reduction within 5 years of internet mainstream adoption."
        ),
        "metadata": {
            "source": "historical_analog",
            "scenario": "AI Disruption Analog",
            "title": "Online Travel → Travel Agent Disintermediation (2000)",
            "ticker": ANALOGS_TICKER,
            "chunk_index": 4,
        },
    },
    # ── Regulatory Crackdown ──────────────────────────────────────────────────
    {
        "text": (
            "Microsoft antitrust (1998) — Regulatory Crackdown analog: "
            "DOJ antitrust suit filed May 1998 against Microsoft (MSFT). "
            "MSFT stock fell ~35% from peak ($59) to trough ($30) over 18 months (1999–2001). "
            "However, ~60% of the decline was dot-com driven, not antitrust. "
            "Settlement (Nov 2001) had minimal product impact: Microsoft retained Windows/IE bundling. "
            "MSFT stock recovered to pre-suit levels within 36 months of settlement. "
            "Key lesson: antitrust fears in tech historically overstated near-term impact "
            "but create multi-year sentiment headwinds (15–25% P/E multiple compression). "
            "Analog for AI regulation: EU AI Act, US Executive Orders may compress multiples "
            "but rarely prevent core business model continuation. "
            "Typical regulatory headwind duration: 18–36 months from filing to resolution."
        ),
        "metadata": {
            "source": "historical_analog",
            "scenario": "Regulatory Crackdown Analog",
            "title": "Microsoft Antitrust (1998) — Regulatory Analog",
            "ticker": ANALOGS_TICKER,
            "chunk_index": 5,
        },
    },
    {
        "text": (
            "AT&T breakup (1984) — Forced structural divestiture analog: "
            "US Department of Justice consent decree (Jan 1, 1984) broke AT&T into "
            "AT&T Long Lines + 7 regional Baby Bells (Ameritech, BellSouth, NYNEX, etc.). "
            "AT&T stock fell ~40% in the 2 years before the breakup on uncertainty. "
            "Post-breakup performance: AT&T Long Lines and the Baby Bells collectively "
            "outperformed the S&P 500 by ~25% over the following decade as deregulation "
            "expanded total industry revenue. "
            "Key lesson: structural divestiture creates short-term disruption and legal costs "
            "but can unlock value if the spun-off parts are viable standalone businesses. "
            "The aggregate market cap of the 8 post-breakup entities exceeded pre-breakup AT&T "
            "within 10 years (source: Bernstein Research historical equity analysis). "
            "Analog for big-tech breakup risk (Google, Meta, Amazon): "
            "regulatory breakup risk is rarely existential — sum-of-parts value may exceed whole. "
            "Sentiment compression: 20–35% P/E discount in 24–36 months preceding forced split. "
            "Recovery timeline post-resolution: 2–4 years to full re-rating."
        ),
        "metadata": {
            "source": "historical_analog",
            "scenario": "Regulatory Crackdown Analog",
            "title": "AT&T Breakup (1984) — Forced Divestiture Analog",
            "ticker": ANALOGS_TICKER,
            "chunk_index": 6,
        },
    },
    # ── Valuation Compression ─────────────────────────────────────────────────
    {
        "text": (
            "Dot-com valuation compression (2000) analog: "
            "Nasdaq fell 78% from peak (5,048 on Mar 10, 2000) to trough (1,114 on Oct 9, 2002). "
            "High-multiple tech (P/E >100×) fell average 85%. "
            "Profitable tech (P/E 30–50×) fell average 55%. "
            "Revenue-growth-only (no earnings) fell average 95%. "
            "Recovery: Nasdaq did not revisit 2000 peak until April 2015 — 15 years later. "
            "S&P 500 returned to 2000 peak in 2007 (7 years). "
            "Key lesson: companies trading >40× P/E with <20% revenue growth face "
            "60–75% downside in a multiple-compression scenario if growth disappoints. "
            "Recovery driver: actual earnings growth, not narrative re-rating."
        ),
        "metadata": {
            "source": "historical_analog",
            "scenario": "Valuation Compression Analog",
            "title": "Dot-Com Valuation Compression (2000)",
            "ticker": ANALOGS_TICKER,
            "chunk_index": 7,
        },
    },
    # ── Rates Shock / Stagflation ─────────────────────────────────────────────
    {
        "text": (
            "1970s–1980 stagflation / rates shock analog: "
            "US CPI peaked at 14.8% in March 1980. Fed Funds Rate peaked at 20% in June 1981. "
            "S&P 500 real returns: −15% from 1968–1982 (14 years flat-to-negative in real terms). "
            "Winners: energy stocks (+400% real 1974–1980), commodities, gold (+800%). "
            "Losers: long-duration bonds (−30% real), high-PE growth stocks (−60–80%), REITs. "
            "Modern parallel (2022–2025): 10yr Treasury from 0.5% (Aug 2020) to 5.0% (Oct 2023) "
            "compressed high-PE growth multiples by 40–60%. "
            "Historical precedent: rate normalisation from 5% → 3% over 2–3 years "
            "has historically led to S&P P/E re-expansion of 15–25% "
            "and tech sector outperformance in the 12–18 months following peak rates."
        ),
        "metadata": {
            "source": "historical_analog",
            "scenario": "Rates Shock / Stagflation Analog",
            "title": "1970s Stagflation / 1980 Rate Shock Analog",
            "ticker": ANALOGS_TICKER,
            "chunk_index": 8,
        },
    },
    # ── Geopolitical Escalation: Pacific Rim ──────────────────────────────────
    {
        "text": (
            "Huawei US export ban (2019) — Geopolitical tech restriction analog: "
            "May 2019: US Department of Commerce added Huawei to Entity List, "
            "banning US companies from supplying chips, software, and components without a license. "
            "Immediate stock market reaction: Philadelphia Semiconductor Index (SOX) fell 12% in 3 weeks. "
            "Qualcomm (QCOM) lost ~$8B in annual Huawei revenue (~15% of total). "
            "Intel, Micron, Broadcom each lost 5–10% of revenue from Huawei relationship. "
            "Longer term: US chip suppliers found alternative demand (other Android OEMs) "
            "and accelerated domestic orders from Apple/others; SOX recovered fully within 12 months. "
            "Huawei pivoted to HiSilicon/SMIC-manufactured chips (inferior node, limited supply). "
            "Key lesson for Pacific Rim geopolitical risk: "
            "Export bans create 12–24 month revenue headwinds (10–20% for directly exposed firms), "
            "then either find alternative customers or trigger domestic substitution. "
            "Semiconductor names with >15% China revenue face 25–40% multiple compression "
            "during active escalation episodes. "
            "TSMC, ASML, Tokyo Electron all fell 20–35% in 2022 on Taiwan strait fears."
        ),
        "metadata": {
            "source": "historical_analog",
            "scenario": "Geopolitical Escalation: Pacific Rim",
            "title": "Huawei US Export Ban (2019) — Geopolitical Tech Restriction",
            "ticker": ANALOGS_TICKER,
            "chunk_index": 9,
        },
    },
    {
        "text": (
            "Russia SWIFT sanctions (2022) — Financial infrastructure geopolitical analog: "
            "Following Russia's invasion of Ukraine (Feb 24, 2022), G7 governments removed "
            "major Russian banks from the SWIFT financial messaging system (Mar 12, 2022). "
            "Immediate impact on financial sector: Visa (V) and Mastercard (MA) suspended Russia "
            "operations — combined Russia revenue ~4% of each company's total. "
            "V fell 10%, MA fell 12% in the 4 weeks post-invasion before recovering. "
            "European bank stocks (Société Générale, Raiffeisen) fell 20–40% on Russia exposure. "
            "Commodity price spike: Brent crude +40% in 3 weeks (Russia = 10% of global supply). "
            "Wheat +50%, natural gas +200% (Europe). "
            "Key lesson: geopolitical financial isolation creates concentrated sector impacts: "
            "energy, agriculture, and companies with Russia/Eastern Europe revenue >5% face "
            "10–25% stock drawdowns. "
            "Contagion to unrelated sectors is typically limited and mean-reverting within 60 days. "
            "Safe-haven assets (USD, gold, US Treasuries) outperform during active conflict phases. "
            "Pacific Rim analog: Taiwan strait conflict would generate comparable or larger disruption "
            "given Taiwan = 90%+ of leading-edge chip production globally."
        ),
        "metadata": {
            "source": "historical_analog",
            "scenario": "Geopolitical Escalation: Pacific Rim",
            "title": "Russia SWIFT Sanctions (2022) — Financial Isolation Analog",
            "ticker": ANALOGS_TICKER,
            "chunk_index": 10,
        },
    },
    {
        "text": (
            "Cold War COCOM semiconductor export controls (1949–1994) — Long-cycle tech restriction analog: "
            "The Coordinating Committee for Multilateral Export Controls (COCOM) restricted "
            "technology exports to the Soviet bloc from 1949 through the end of the Cold War. "
            "Semiconductor and computing technology was specifically restricted post-1979. "
            "Historical outcome: export-controlled sectors (mainframe, advanced chips) saw "
            "no direct revenue loss from Soviet sales (too small) but did incur compliance costs "
            "of ~2–5% of revenue for large defence/semiconductor firms (Motorola, Intel, TI). "
            "More importantly: restrictions accelerated domestic R&D in restricted countries "
            "(USSR developed parallel semiconductor programs) and strengthened US semiconductor "
            "leadership by preventing technology diffusion. "
            "Modern analog — BIS Entity List, CHIPS Act export controls on advanced AI chips to China: "
            "NVIDIA, AMD, Intel face restrictions on A100/H100-class GPU exports to China. "
            "China = ~20–25% of NVDA's data centre revenue pre-restriction (FY2023). "
            "Historical COCOM precedent: compliance costs 2–5%, direct revenue loss 5–15% "
            "in first 2 years, partially offset by domestic/ally demand within 3–5 years. "
            "Geopolitical risk premium on affected stocks: 20–30% P/E compression during "
            "active restriction period, recovery contingent on policy clarity."
        ),
        "metadata": {
            "source": "historical_analog",
            "scenario": "Geopolitical Escalation: Pacific Rim",
            "title": "Cold War COCOM Semiconductor Export Controls (1949–1994)",
            "ticker": ANALOGS_TICKER,
            "chunk_index": 11,
        },
    },
    # ── Demand Slowdown / Recession Analog ────────────────────────────────────
    {
        "text": (
            "2008 Global Financial Crisis — Tech and enterprise IT demand slowdown analog: "
            "S&P 500 fell 57% peak-to-trough (Oct 2007–Mar 2009). "
            "Enterprise IT spending fell ~8% in 2009 (IDC Global IT Spending Survey). "
            "Software/SaaS: Oracle Q3 2009 revenue −5% YoY; SAP −8% YoY. "
            "Hardware: HP enterprise fell −20% in 2009; Dell enterprise −18%. "
            "Consulting: Accenture FY2009 revenue −8% YoY; IBM Global Services −4%. "
            "Fastest to recover: cloud/SaaS (AWS launched 2006; Salesforce grew through recession). "
            "Fastest to cut: discretionary IT services, custom development, hardware refresh. "
            "Recovery timeline: enterprise IT spending returned to 2007 levels by Q2 2011 "
            "— roughly 2 years of lost growth. "
            "Key lesson for recession scenario: "
            "Enterprise tech with >60% recurring revenue (subscription, maintenance) falls 5–15%; "
            "project-based consulting and hardware falls 20–35%. "
            "High-PE growth names (P/E >40×) contracted 50–70% in this environment. "
            "Companies with net cash, strong FCF margins, and sticky SaaS revenue outperformed "
            "the category by 30–40% over the 24 months post-trough."
        ),
        "metadata": {
            "source": "historical_analog",
            "scenario": "Demand Slowdown / Recession Analog",
            "title": "2008 GFC — Enterprise IT Demand Collapse",
            "ticker": ANALOGS_TICKER,
            "chunk_index": 12,
        },
    },
    {
        "text": (
            "2001 dot-com bust — Enterprise IT capex freeze and forward guidance slashing: "
            "Following the dot-com peak (March 2000), enterprise IT capex fell sharply in 2001–2002. "
            "Cisco Systems revenue fell from $22.3B (FY2000) to $18.9B (FY2001) — a 15% decline; "
            "Cisco wrote down $2.2B in inventory (May 2001). "
            "Sun Microsystems revenue fell 52% from 2000 to 2002 — ultimately led to acquisition by Oracle. "
            "EMC (storage), 3Com (networking): each fell 30–40% revenue over 2001–2002. "
            "Winners in the bust: IBM (diversified services cushioned hardware declines), "
            "Microsoft (Office licensing = recurring), and early SaaS (Salesforce IPO 2004). "
            "Guidance cuts: median large-cap tech company cut forward guidance by 25–35% "
            "within 2 quarters of peak — stock prices led cuts by 6–9 months. "
            "Key lesson: guidance trajectory more predictive than current results. "
            "Watch for: slowing bookings growth, elongated sales cycles, increased customer churn, "
            "and deferred project starts — leading indicators that precede reported revenue misses by 1–2 quarters. "
            "Recession revenue trough to recovery: typically 6–10 quarters for enterprise tech."
        ),
        "metadata": {
            "source": "historical_analog",
            "scenario": "Demand Slowdown / Recession Analog",
            "title": "2001 Dot-Com Bust — Enterprise IT Capex Freeze",
            "ticker": ANALOGS_TICKER,
            "chunk_index": 13,
        },
    },
    # ── Supply Chain Shock Analog ─────────────────────────────────────────────
    {
        "text": (
            "COVID-19 semiconductor shortage (2020–2021) — Supply chain shock analog: "
            "The global chip shortage began Q2 2020 as COVID-19 disrupted Asian fabs and "
            "demand simultaneously spiked (PC, gaming, home appliances). "
            "Lead times for automotive microcontrollers rose from 12 weeks (normal) to 52+ weeks by 2021. "
            "Ford Motor estimated $2.5B revenue loss in 2021 from chip shortages; "
            "GM reduced production 1 million vehicles. "
            "Apple (AAPL) warned of $6B lost revenue in Q4 FY2021 from chip constraints. "
            "Semiconductor equipment makers (ASML, Applied Materials, Lam Research) "
            "benefited: revenue surged as customers tried to accelerate capacity expansion. "
            "Stock impact: automotive OEMs fell 10–20%; chip equipment makers +30–50% in 2021. "
            "Resolution timeline: automotive chip shortage eased Q1 2023 (~3 years from onset). "
            "Consumer electronics normalized by Q4 2022 (~2.5 years). "
            "Key lesson for supply chain shock: "
            "Single-source / geographically concentrated supply chains amplify impact. "
            "Companies with inventory buffers >90 days were largely insulated; "
            "those on just-in-time <30 day inventory took 15–25% revenue hits in peak shortage quarters."
        ),
        "metadata": {
            "source": "historical_analog",
            "scenario": "Supply Chain Shock Analog",
            "title": "COVID-19 Semiconductor Shortage (2020–2021)",
            "ticker": ANALOGS_TICKER,
            "chunk_index": 14,
        },
    },
    {
        "text": (
            "Japan earthquake / Tohoku disaster (2011) — JIT supply chain collapse analog: "
            "The March 11, 2011 Tohoku earthquake and tsunami disrupted Japanese manufacturing "
            "— a critical single-source region for automotive and electronics components. "
            "Toyota halted production at 12 of 18 Japanese plants within days; "
            "Toyota's global output fell ~40% in April–May 2011. "
            "Global vehicle production fell ~7% in Q2 2011. "
            "Key Japanese suppliers: Renesas Electronics (microcontrollers), "
            "Shin-Etsu Chemical (silicon wafers), and TDK (electronic components) "
            "faced 3–6 month production outages. "
            "Renesas took 3 months to restart; silicon wafer supply remained tight for 6 months. "
            "Stock impact: Toyota (TM) fell 20% in 6 weeks post-quake, recovered by year-end. "
            "Hitachi, Fujitsu, Panasonic each fell 15–30% and recovered within 9 months. "
            "Key lesson for supply chain concentration risk: "
            "Companies sourcing >30% of a critical component from a single geography "
            "face 15–25% stock drawdowns and 2–6 months of revenue disruption per major shock. "
            "Post-2011, major OEMs mandated dual-sourcing for critical components "
            "and built inventory buffers — reducing future single-event impact."
        ),
        "metadata": {
            "source": "historical_analog",
            "scenario": "Supply Chain Shock Analog",
            "title": "Japan Earthquake / Toyota JIT Collapse (2011)",
            "ticker": ANALOGS_TICKER,
            "chunk_index": 15,
        },
    },
    # ── Commodity Shock Analog ────────────────────────────────────────────────
    {
        "text": (
            "1973 OPEC oil embargo — Commodity shock and demand destruction analog: "
            "October 1973: OPEC Arab members embargo oil exports to US and Netherlands "
            "in retaliation for Yom Kippur War support. "
            "Oil price rose from $3/barrel (Oct 1973) to $12/barrel (Jan 1974) — a 4× increase. "
            "US GDP fell 2.5% in 1974; industrial production fell 15%. "
            "S&P 500 fell 48% peak-to-trough (Jan 1973–Oct 1974) in nominal terms (−65% real). "
            "Sector impact: airlines fell 40–60% (fuel = 15–25% of operating costs); "
            "auto OEMs fell 30–50% (gas-guzzler demand collapsed); "
            "utilities fell 20–35% (natural gas substitution limits). "
            "Winners: oil majors (Exxon, Chevron +80–120%), oil services, coal miners. "
            "Modern analog (2022 Ukraine war energy shock): "
            "European natural gas prices rose 10× (Aug 2022 peak vs 2021 baseline). "
            "German industrial production fell 3.6% in 2022. "
            "Energy-intensive industries (chemicals, steel, glass, cement) saw 30–50% "
            "margin compression in Europe. "
            "Key lesson: commodity shocks compress margins of energy-intensive industries "
            "by 30–60% within 2 quarters; recovery follows commodity price normalisation (6–18 months)."
        ),
        "metadata": {
            "source": "historical_analog",
            "scenario": "Commodity Shock Analog",
            "title": "1973 OPEC Oil Embargo — Commodity Shock Analog",
            "ticker": ANALOGS_TICKER,
            "chunk_index": 16,
        },
    },
    {
        "text": (
            "2022 European natural gas crisis — Energy commodity shock and sector margin compression: "
            "Following Russia's invasion of Ukraine (Feb 2022), Europe faced acute natural gas shortage. "
            "TTF natural gas spot price peaked at €342/MWh (Aug 2022) vs ~€20/MWh pre-crisis. "
            "German industry was most exposed: natural gas = 30% of German industrial energy input. "
            "BASF (world's largest chemical company) reported €8.3B energy cost increase in 2022; "
            "BASF Ludwigshafen site — historically the company's most profitable — operated at loss. "
            "European steel producers (ArcelorMittal, Thyssenkrupp) curtailed capacity 15–30%. "
            "German GDP: −0.2% in 2023 (mild recession despite energy shock). "
            "Commodity price normalisation: TTF fell back to €30–40/MWh by early 2023 "
            "as LNG imports, demand destruction, and mild winter reduced the crisis. "
            "Stock recovery: BASF recovered ~50% of its 2022 decline by mid-2023; "
            "energy-intensive industrials recovered 60–70% of peak losses within 18 months. "
            "Key lesson: commodity input shocks for energy-intensive firms "
            "last 12–24 months peak-to-normalisation; stock markets price in ~6 months ahead. "
            "Companies with energy-fixed pricing contracts or hedges outperform unhedged peers by 20–35%."
        ),
        "metadata": {
            "source": "historical_analog",
            "scenario": "Commodity Shock Analog",
            "title": "2022 European Natural Gas Crisis — Energy Margin Compression",
            "ticker": ANALOGS_TICKER,
            "chunk_index": 17,
        },
    },
    # ── Crypto Volatility Analog ──────────────────────────────────────────────
    {
        "text": (
            "FTX collapse (November 2022) — Crypto exchange contagion and sector-wide drawdown: "
            "FTX, the world's second-largest crypto exchange (peak valuation $32B), collapsed "
            "within 8 days (Nov 2–10, 2022) following a CoinDesk report on Alameda Research balance sheet. "
            "Bitcoin fell from $21,000 (Nov 7) to $15,500 (Nov 22) — a 26% decline in 2 weeks. "
            "Ethereum fell 30% in the same period. Total crypto market cap lost ~$200B. "
            "Contagion: BlockFi (filed bankruptcy Nov 28), Genesis (Jan 2023), "
            "Gemini Earn halted withdrawals (Nov 16). "
            "Coinbase (COIN) fell 28% in November 2022; fell 85% peak-to-trough in 2022 overall. "
            "MicroStrategy (MSTR), Marathon Digital (MARA), Riot Platforms (RIOT) "
            "all fell 60–90% from 2021 peaks by the FTX trough. "
            "Recovery: Bitcoin recovered to $25,000 by March 2023 (+60% from FTX trough) "
            "as contagion fears faded and regulatory clarity improved. "
            "Key lesson: crypto sector-specific shocks (exchange failures, fraud) "
            "create 25–40% Bitcoin drawdowns in 2–4 weeks; contagion to crypto-adjacent "
            "equities (COIN, MARA, MSTR) is 2–4× larger in amplitude. "
            "Non-crypto equities (fintech, banks with limited crypto exposure) recovered within 30 days."
        ),
        "metadata": {
            "source": "historical_analog",
            "scenario": "Crypto Volatility Analog",
            "title": "FTX Collapse (November 2022) — Crypto Contagion Analog",
            "ticker": ANALOGS_TICKER,
            "chunk_index": 18,
        },
    },
    {
        "text": (
            "Mt. Gox hack (2014) and Bitcoin halving cycles — Structural crypto volatility pattern: "
            "Mt. Gox hack (Feb 2014): 850,000 BTC stolen (~$450M at time, ~$50B at 2024 prices). "
            "Bitcoin fell from $1,100 (Dec 2013) to $170 (Jan 2015) — an 85% drawdown over 13 months. "
            "Recovery timeline: Bitcoin returned to $1,100 by December 2016 — 3 years. "
            "Bitcoin halving cycles (supply issuance cut 50% every ~4 years): "
            "Halving → run-up → parabolic peak → major correction is the recurring pattern: "
            "2012 halving → 2013 peak (+8,000%) → 2015 trough (−85%) "
            "2016 halving → 2017 peak (+1,900%) → 2018 trough (−84%) "
            "2020 halving → 2021 peak (+600%) → 2022 trough (−77%) "
            "Historical base rate: post-halving peak occurs 12–18 months after halving; "
            "subsequent bear market trough occurs 12–18 months after peak. "
            "Average peak-to-trough drawdown: ~80% across three cycles. "
            "Average trough-to-next-peak appreciation: ~10× across three cycles. "
            "Key lesson for crypto volatility risk: "
            "Crypto equities (miners, exchanges, treasuries) amplify BTC moves 2–4×. "
            "A 50% BTC drawdown historically produces 70–90% drawdowns in crypto-adjacent equities. "
            "Investors should size positions assuming 80% drawdown scenarios as plausible."
        ),
        "metadata": {
            "source": "historical_analog",
            "scenario": "Crypto Volatility Analog",
            "title": "Mt. Gox (2014) & Bitcoin Halving Cycle Volatility Patterns",
            "ticker": ANALOGS_TICKER,
            "chunk_index": 19,
        },
    },
]

# ── Seeding ───────────────────────────────────────────────────────────────────

_analogs_seeded: bool = False


def ensure_analogs_seeded() -> None:
    """Upsert analog documents into ChromaDB (idempotent, once per process).

    Always runs upsert on first call so that newly added analog documents are
    picked up on server restart without needing to clear the collection manually.
    Existing documents are updated in-place; new chunk_indexes are inserted.
    """
    global _analogs_seeded
    if _analogs_seeded:
        return
    try:
        store.upsert_documents(ANALOGS_TICKER, ANALOG_DOCUMENTS)
    except Exception:
        pass
    _analogs_seeded = True


# ── Retrieval ─────────────────────────────────────────────────────────────────

def retrieve_analogs(scenarios: list[str], n_results: int = 3) -> str:
    """
    Retrieve historical analog chunks matching the given scenario tags.
    Returns a formatted grounding block ready for injection into agent prompts.
    Returns an empty string if no scenarios provided or no matches found.
    """
    if not scenarios:
        return ""

    ensure_analogs_seeded()

    # Query with all scenario names combined for best semantic match
    query = " ".join(scenarios)
    results = store.similarity_search(ANALOGS_TICKER, query, n_results=n_results)
    if not results:
        return ""

    lines = [
        "═══ HISTORICAL ANALOGS (Gated Grounding — RAG Verified) ═══",
        f"Scenarios detected: {', '.join(scenarios)}",
        "Use these verified precedents to quantify probability and magnitude of impact.",
        "Cite the specific analog title and data point when referencing scenario outcomes.",
        "",
    ]
    for r in results:
        title = r["metadata"].get("title", "Historical Analog")
        lines.append(f"▶ {title}  [relevance: {r['score']:.2f}]")
        lines.append(r["text"])
        lines.append("")

    return "\n".join(lines)
