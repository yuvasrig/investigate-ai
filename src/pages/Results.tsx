import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  TrendingUp, AlertTriangle, Target, Scale, CheckCircle2, AlertCircle,
  FileDown, Loader2, Info, FlaskConical, Trophy, ChevronDown, ChevronUp,
  BookOpen, Database, ShieldCheck, ExternalLink,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { useAnalysis } from "@/context/AnalysisContext";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell, Tooltip } from "recharts";
import { TrafficLight } from "@/components/TrafficLight";
import { PortfolioExposure, ExposureData } from "@/components/PortfolioExposure";
import CitationModal from "@/components/CitationModal";

import type {
  AgentEvidenceScore,
  BearAnalysis,
  BullAnalysis,
  EvaluatedScenario,
  EvidenceAssessment,
  SecFiling,
  StrategistAnalysis,
  VerifiedClaim,
} from "@/services/api";

const API_BASE = (import.meta.env.VITE_API_URL as string) || "http://localhost:8000";

interface MarketNewsItem {
  title?: string;
  publisher?: string;
  link?: string;
}

const riskColor: Record<string, string> = {
  LOW: "text-bull bg-bull/10",
  MODERATE: "text-strategist bg-strategist/10",
  HIGH: "text-bear bg-bear/10",
  "VERY HIGH": "text-bear bg-bear/20",
};

// ── Analyst role descriptions ─────────────────────────────────────────────────
const ANALYST_ROLES = {
  bull: {
    tagline: "Senior Equity Analyst",
    description:
      "Builds the strongest possible upside case. Focuses on growth drivers, competitive moats, and why the valuation is justified.",
  },
  bear: {
    tagline: "Veteran Short Seller",
    description:
      "Stress-tests risks and downside scenarios. Challenges bull assumptions with historical precedent and structural headwinds.",
  },
  strategist: {
    tagline: "Head of Portfolio Construction",
    description:
      "Evaluates portfolio-level fit, concentration risk, and hidden ETF exposure. Ensures the trade doesn't break diversification rules.",
  },
};

const AGENT_ROLES_TAB = [
  {
    key: "bull",
    title: "Bull Analyst",
    subtitle: "Senior Equity Analyst",
    accent: "text-bull bg-bull/10",
    role:
      "Builds the strongest upside case for the stock using growth quality, competitive moats, and valuation support.",
    focusesOn: [
      "Competitive advantages and defensibility",
      "Growth catalysts and earnings momentum",
      "Best-case target price and timeline",
    ],
  },
  {
    key: "bear",
    title: "Bear Analyst",
    subtitle: "Veteran Short Seller",
    accent: "text-bear bg-bear/10",
    role:
      "Builds the strongest downside case by stress-testing assumptions and identifying structural risks.",
    focusesOn: [
      "Valuation concerns and downside asymmetry",
      "Competitive and execution threats",
      "Worst-case target price and timeline",
    ],
  },
  {
    key: "strategist",
    title: "Portfolio Strategist",
    subtitle: "Head of Portfolio Construction",
    accent: "text-strategist bg-strategist/10",
    role:
      "Translates the debate into position sizing and portfolio fit while managing concentration risk.",
    focusesOn: [
      "Current and indirect exposure",
      "Diversification and concentration limits",
      "Recommended allocation and alternatives",
    ],
  },
  {
    key: "cio",
    title: "CIO / Judge",
    subtitle: "Chief Investment Officer",
    accent: "text-accent bg-accent/10",
    role:
      "Makes the final decision by weighing conviction against evidence quality across all agents.",
    focusesOn: [
      "Evidence-weighted winner selection",
      "Final action, amount, and confidence",
      "Entry strategy, risk management, and key factors",
    ],
  },
] as const;

// ── Historical analog context lookup ─────────────────────────────────────────
// Keywords matched case-insensitively as substrings of an analog title.
// All keywords in an entry must match (AND logic). First match wins.
const ANALOG_CONTEXT_MAP: { keywords: string[]; context: string; category: string }[] = [
  {
    keywords: ["excel", "account"],
    context:
      "When spreadsheet software spread in the 1980s, bookkeeping demand fell ~50% in 10 years, but firms that pivoted to advisory services grew revenue 2–3×. Disruption compressed commodity hours while expanding higher-value advisory work.",
    category: "AI Disruption",
  },
  {
    keywords: ["aws", "consulting"],
    context:
      "AWS mainstream adoption (2010–2016) eliminated 30–40% of on-premise infrastructure consulting revenue, yet cloud migration consulting created a new $50B+ market. Advisory firms that pivoted grew total revenues despite commodity-tier compression.",
    category: "AI Disruption",
  },
  {
    keywords: ["atm", "teller"],
    context:
      "ATM deployment (1970–1995) actually increased total teller employment by lowering branch operating costs, enabling banks to open more locations. Automation can expand total market even while transforming human roles.",
    category: "AI Disruption",
  },
  {
    keywords: ["cad", "draft"],
    context:
      "AutoCAD's mass adoption (1985–1995) reduced engineering drafters by 40% in 17 years — the worst-case displacement scenario where cognitive complexity of remaining work was too low for role transformation at scale.",
    category: "AI Disruption",
  },
  {
    keywords: ["travel agent"],
    context:
      "Expedia and Booking.com wiped 41% of US travel agent locations within 5 years of internet mainstream adoption. Surviving agencies pivoted to luxury/complex itineraries at 3–5× the margin — disintermediation forces upmarket migration.",
    category: "AI Disruption",
  },
  {
    keywords: ["microsoft", "antitrust"],
    context:
      "The 1998 DOJ antitrust suit against Microsoft created 15–25% P/E multiple compression over 18 months but had minimal product impact after settlement. Regulatory fears in tech historically create multi-year sentiment headwinds rather than existential business change.",
    category: "Regulatory",
  },
  {
    keywords: ["at&t"],
    context:
      "The 1984 AT&T forced divestiture caused short-term disruption, but the 8 post-breakup entities collectively outperformed the S&P 500 by 25% over the following decade. Regulatory breakups can unlock sum-of-parts value exceeding the pre-split whole.",
    category: "Regulatory",
  },
  {
    keywords: ["dot-com", "valuat"],
    context:
      "The 2000 dot-com crash saw high-multiple tech (P/E >100×) fall an average 85%; the Nasdaq took 15 years to recover its 2000 peak. Companies with P/E >40× and <20% revenue growth face 60–75% downside in multiple-compression scenarios.",
    category: "Valuation",
  },
  {
    keywords: ["stagflation"],
    context:
      "The 1970s–1980 stagflation cycle delivered S&P 500 real returns of −15% over 14 years, with energy stocks +400% and high-PE growth stocks −60–80%. Rate normalisation from peak historically leads to 15–25% P/E re-expansion in tech over 12–18 months.",
    category: "Rates",
  },
  {
    keywords: ["1980", "rate shock"],
    context:
      "The 1980 Fed Funds peak at 20% compressed high-PE multiples by 40–60%. Historical precedent shows tech sector outperformance in the 12–18 months following peak rates, with P/E re-expansion of 15–25% as rates normalise.",
    category: "Rates",
  },
  {
    keywords: ["huawei"],
    context:
      "The 2019 Huawei Entity List ban created 12–24 month revenue headwinds of 10–20% for directly exposed chip suppliers, then resolved via alternative customers. Semiconductor names with >15% China revenue faced 25–40% multiple compression during active escalation.",
    category: "Geopolitical",
  },
  {
    keywords: ["swift"],
    context:
      "The 2022 Russia SWIFT sanctions caused concentrated 10–25% stock drawdowns in energy and companies with >5% Russia revenue, while contagion to unrelated sectors was limited and mean-reverting within 60 days. Safe-haven assets outperformed during active conflict.",
    category: "Geopolitical",
  },
  {
    keywords: ["cocom"],
    context:
      "Cold War COCOM export controls showed compliance costs of 2–5% of revenue and direct revenue loss of 5–15% in the first 2 years, partially offset by domestic demand. Historical precedent suggests 20–30% P/E compression during active restriction, recovering with policy clarity.",
    category: "Geopolitical",
  },
  {
    keywords: ["gfc"],
    context:
      "The 2008 GFC caused enterprise IT spending to fall 8% in 2009. Companies with >60% recurring revenue fell 5–15% while project-based consulting fell 20–35%. Enterprise tech returned to 2007 spending levels within 2 years of the trough.",
    category: "Recession",
  },
  {
    keywords: ["2001", "capex"],
    context:
      "The 2001 dot-com bust froze enterprise IT capex, with Cisco revenue falling 15% and Sun Microsystems 52%. Guidance cuts of 25–35% typically follow peak with a 6–9 month stock price lead. Revenue troughs last 6–10 quarters for enterprise tech.",
    category: "Recession",
  },
  {
    keywords: ["covid", "semiconductor"],
    context:
      "The 2020–2021 semiconductor shortage stretched lead times from 12 to 52+ weeks. Companies on just-in-time <30-day inventory took 15–25% revenue hits in peak shortage quarters vs those with 90+ day buffers who were largely insulated.",
    category: "Supply Chain",
  },
  {
    keywords: ["toyota", "jit"],
    context:
      "The 2011 Tohoku earthquake collapsed Toyota's JIT supply chain, cutting global output 40% in 2 months. Companies sourcing >30% of critical components from a single geography face 15–25% stock drawdowns and 2–6 months of revenue disruption per major shock.",
    category: "Supply Chain",
  },
  {
    keywords: ["opec"],
    context:
      "The 1973 OPEC embargo quadrupled oil prices in 3 months, pushing S&P 500 down 48% peak-to-trough. Airlines fell 40–60% and auto OEMs 30–50%, while oil majors gained 80–120%. Commodity shocks compress energy-intensive margins 30–60% within 2 quarters.",
    category: "Commodity",
  },
  {
    keywords: ["european", "natural gas"],
    context:
      "The 2022 European natural gas crisis pushed prices 17× above pre-crisis levels, costing BASF €8.3B in extra energy costs. Energy-intensive industrial stocks recovered 60–70% of peak losses within 18 months once commodity prices normalised.",
    category: "Commodity",
  },
  {
    keywords: ["ftx"],
    context:
      "The FTX collapse (Nov 2022) wiped $200B in crypto market cap in 8 days and triggered contagion bankruptcies (BlockFi, Genesis). Crypto exchange failures cause 25–40% Bitcoin drawdowns in 2–4 weeks, with crypto-adjacent equities amplifying moves 2–4×.",
    category: "Crypto",
  },
  {
    keywords: ["gox"],
    context:
      "Mt. Gox's 2014 hack triggered an 85% Bitcoin drawdown over 13 months. Bitcoin halving cycles (2012, 2016, 2020) show a consistent pattern: ~80% peak-to-trough corrections following parabolic run-ups. Crypto equities amplify Bitcoin moves 2–4× in both directions.",
    category: "Crypto",
  },
  {
    keywords: ["halving"],
    context:
      "Bitcoin halving cycles (2012, 2016, 2020) follow a consistent pattern: post-halving run-up to peak occurs 12–18 months after halving, followed by ~80% corrections. Miners and crypto-adjacent equities (MARA, RIOT) amplify BTC moves 2–4× in both directions.",
    category: "Crypto",
  },
];

// ── Category → Tailwind classes ───────────────────────────────────────────────
const CATEGORY_STYLE: Record<string, { border: string; badge: string }> = {
  "AI Disruption":  { border: "border-l-purple-500", badge: "bg-purple-100 text-purple-700" },
  "Regulatory":     { border: "border-l-amber-500",  badge: "bg-amber-100 text-amber-700" },
  "Geopolitical":   { border: "border-l-strategist", badge: "bg-strategist/10 text-strategist" },
  "Valuation":      { border: "border-l-bear",       badge: "bg-bear/10 text-bear" },
  "Rates":          { border: "border-l-orange-500", badge: "bg-orange-100 text-orange-700" },
  "Recession":      { border: "border-l-bear",       badge: "bg-bear/10 text-bear" },
  "Supply Chain":   { border: "border-l-amber-600",  badge: "bg-amber-100 text-amber-800" },
  "Commodity":      { border: "border-l-yellow-600", badge: "bg-yellow-100 text-yellow-800" },
  "Crypto":         { border: "border-l-orange-400", badge: "bg-orange-100 text-orange-700" },
  "default":        { border: "border-l-accent",     badge: "bg-accent/10 text-accent" },
};

// ── Helpers ───────────────────────────────────────────────────────────────────
function lookupAnalog(verifiedAnalogUsed: string): { context: string; category: string } | null {
  const lower = verifiedAnalogUsed.toLowerCase();
  for (const entry of ANALOG_CONTEXT_MAP) {
    if (entry.keywords.every((kw) => lower.includes(kw))) {
      return { context: entry.context, category: entry.category };
    }
  }
  return null;
}

function getScenarioAnalogs(scenario: EvaluatedScenario): string[] {
  const analogs = scenario.verified_analogs_used ?? [];
  if (analogs.length > 0) return analogs;
  return scenario.verified_analog_used ? [scenario.verified_analog_used] : [];
}

function countEvaluatedAnalogs(scenarios: EvaluatedScenario[]): number {
  return scenarios.reduce((total, scenario) => total + getScenarioAnalogs(scenario).length, 0);
}

function categoryFromScenarioName(scenarioName: string): string {
  if (/ai disruption/i.test(scenarioName)) return "AI Disruption";
  if (/regulatory/i.test(scenarioName)) return "Regulatory";
  if (/geopolit/i.test(scenarioName)) return "Geopolitical";
  if (/valuation/i.test(scenarioName)) return "Valuation";
  if (/stagflat|rates?\s+shock/i.test(scenarioName)) return "Rates";
  if (/recession|demand slow/i.test(scenarioName)) return "Recession";
  if (/supply chain/i.test(scenarioName)) return "Supply Chain";
  if (/commodity/i.test(scenarioName)) return "Commodity";
  if (/crypto/i.test(scenarioName)) return "Crypto";
  return "default";
}

// ── Inline components — report framework ──────────────────────────────────────

function ReportHeaderBar({
  analysisId,
  timestamp,
  executionTime,
  llmProvider,
}: {
  analysisId: string;
  timestamp: string;
  executionTime: number;
  llmProvider: string;
}) {
  const ts = new Date(timestamp);
  const dateStr = ts.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  const timeStr = ts.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });

  return (
    <div className="bg-secondary/40 border-b border-border px-6 py-2">
      <div className="container mx-auto max-w-6xl flex flex-wrap items-center gap-x-4 gap-y-0.5 text-[11px] text-muted-foreground">
        <span className="font-semibold text-foreground">InvestiGate AI</span>
        <span className="text-border">|</span>
        <span>Equity Research — AI Generated</span>
        <span className="text-border">|</span>
        <span>{dateStr} · {timeStr}</span>
        <span className="text-border">|</span>
        <span>ID: {analysisId.slice(0, 8).toUpperCase()}</span>
        <span className="text-border">|</span>
        <span>{executionTime.toFixed(1)}s</span>
        <span className="text-border">|</span>
        <span className="capitalize">{llmProvider}</span>
      </div>
    </div>
  );
}

function EnhancedStockHeader({
  ticker,
  action,
  confidenceOverall,
  trafficLightColor,
  companyName,
  sector,
  currentPrice,
  regularMarketChange,
  regularMarketChangePercent,
  bullTarget,
  bearTarget,
}: {
  ticker: string;
  action: string;
  confidenceOverall: number;
  trafficLightColor: string;
  companyName?: string;
  sector?: string;
  currentPrice?: number;
  regularMarketChange?: number;
  regularMarketChangePercent?: number;
  bullTarget: number;
  bearTarget: number;
}) {
  const actionUpper = action.toUpperCase();
  const actionColor =
    actionUpper === "BUY"  ? "bg-bull text-white" :
    actionUpper === "SELL" ? "bg-bear text-white" :
                             "bg-blue-500 text-white";

  const pillColor =
    trafficLightColor === "green" ? "bg-emerald-100 text-emerald-700" :
    trafficLightColor === "yellow" ? "bg-secondary text-muted-foreground" :
    "bg-rose-100 text-rose-700";

  const changePositive = (regularMarketChange ?? 0) >= 0;

  const lo = Math.min(bearTarget, bullTarget);
  const hi = Math.max(bearTarget, bullTarget);
  const hasBar = hi > lo && currentPrice != null;
  const pricePct = hasBar
    ? Math.max(0, Math.min(100, ((currentPrice - lo) / (hi - lo)) * 100))
    : 0;

  return (
    <div className="mb-6">
      {/* Top row: ticker + pills + price */}
      <div className="flex flex-wrap items-start justify-between gap-4 mb-3">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-4xl font-bold text-foreground tracking-tight">{ticker}</h1>
            <span className={`px-3 py-1 rounded-full text-sm font-bold uppercase tracking-wide ${actionColor}`}>
              {actionUpper}
            </span>
            <span className={`px-2.5 py-1 rounded-full text-xs font-semibold uppercase tracking-wide ${pillColor}`}>
              {trafficLightColor}
            </span>
          </div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            {companyName && <span className="font-medium text-foreground/80">{companyName}</span>}
            {companyName && sector && <span>·</span>}
            {sector && <span>{sector}</span>}
          </div>
        </div>
        <div className="text-right">
          {currentPrice != null && (
            <p className="text-3xl font-bold text-foreground tabular-nums">
              ${currentPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </p>
          )}
          {regularMarketChange != null && regularMarketChangePercent != null && (
            <p className={`text-sm font-semibold tabular-nums ${changePositive ? "text-bull" : "text-bear"}`}>
              {changePositive ? "+" : ""}{regularMarketChange.toFixed(2)}
              {" "}({changePositive ? "+" : ""}{(regularMarketChangePercent * 100).toFixed(2)}%)
            </p>
          )}
          <div className="flex items-center gap-2 mt-1 justify-end">
            <span className="text-[11px] text-muted-foreground">Confidence</span>
            <span className="text-lg font-bold text-accent tabular-nums">{confidenceOverall}%</span>
          </div>
        </div>
      </div>

      {/* Price range bar */}
      {hasBar && (
        <div className="mt-2">
          <div className="relative h-2 w-full rounded-full overflow-visible"
            style={{ background: "linear-gradient(to right, hsl(var(--bear)), hsl(220 13% 70%), hsl(var(--bull)))" }}>
            <div
              className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-foreground border-2 border-background shadow"
              style={{ left: `${pricePct}%`, transform: "translate(-50%, -50%)" }}
            />
          </div>
          <div className="flex justify-between mt-1.5 text-[11px] text-muted-foreground">
            <span className="text-bear font-semibold">Bear ${bearTarget.toLocaleString()}</span>
            {currentPrice != null && (
              <span className="text-foreground font-medium">
                Current ${currentPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            )}
            <span className="text-bull font-semibold">Bull ${bullTarget.toLocaleString()}</span>
          </div>
        </div>
      )}
    </div>
  );
}

function MarketMetricsStrip({ marketData }: { marketData: Record<string, unknown> | null }) {
  if (!marketData) return null;

  const md = marketData;
  const getNumber = (...keys: string[]) => {
    for (const key of keys) {
      const value = md[key];
      if (typeof value === "number") return value;
    }
    return undefined;
  };

  const trailingPE = getNumber("trailingPE", "pe_trailing");
  const forwardPE  = getNumber("forwardPE", "pe_forward");
  const marketCap  = getNumber("marketCap", "market_cap");
  const beta       = getNumber("beta");
  const low52      = getNumber("fiftyTwoWeekLow", "52_week_low");
  const high52     = getNumber("fiftyTwoWeekHigh", "52_week_high");
  const divYield   = getNumber("dividendYield", "dividend_yield");

  const formatCap = (v: number) => {
    if (v >= 1e12) return `$${(v / 1e12).toFixed(1)}T`;
    if (v >= 1e9)  return `$${(v / 1e9).toFixed(0)}B`;
    if (v >= 1e6)  return `$${(v / 1e6).toFixed(0)}M`;
    return `$${v.toLocaleString()}`;
  };

  const peStr = trailingPE != null
    ? `${trailingPE.toFixed(1)}×`
    : forwardPE != null
    ? `${forwardPE.toFixed(1)}× fwd`
    : "N/A";

  const metrics = [
    { label: "P/E (TTM)",    value: peStr },
    { label: "Market Cap",   value: marketCap != null ? formatCap(marketCap) : "N/A" },
    { label: "Beta",         value: beta != null ? beta.toFixed(2) : "N/A" },
    { label: "52W Range",    value: low52 != null && high52 != null ? `$${low52.toLocaleString()} – $${high52.toLocaleString()}` : "N/A" },
    { label: "Div Yield",    value: divYield != null ? `${(divYield * 100).toFixed(2)}%` : "N/A" },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 mb-8">
      {metrics.map((m) => (
        <div key={m.label} className="bg-card rounded-lg border border-border p-3 text-center">
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1 font-medium">{m.label}</p>
          <p className="text-sm font-bold text-foreground tabular-nums">{m.value}</p>
        </div>
      ))}
    </div>
  );
}

// ── Scenario Analysis Section ─────────────────────────────────────────────────

function ScenarioDropdown({ scenario, index }: { scenario: EvaluatedScenario; index: number }) {
  const [open, setOpen] = useState(index === 0);
  const analogs = getScenarioAnalogs(scenario);
  const analogContexts = analogs
    .map((analog) => ({ analog, info: lookupAnalog(analog) }))
    .filter((item) => item.info);
  const category = analogContexts[0]?.info?.category ?? categoryFromScenarioName(scenario.scenario_name);
  const style = CATEGORY_STYLE[category] ?? CATEGORY_STYLE["default"];

  return (
    <div className={`bg-card rounded-xl border border-border border-l-4 ${style.border} shadow-sm`}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full p-5 text-left flex items-start justify-between gap-3"
        aria-expanded={open}
      >
        <div>
          <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider mb-1">
            Scenario {index + 1}
          </p>
          <p className="text-sm font-semibold text-foreground leading-snug">{scenario.scenario_name}</p>
          <p className="text-xs text-muted-foreground mt-1">
            {analogs.length} analog{analogs.length === 1 ? "" : "s"} matched
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${style.badge}`}>
            {category}
          </span>
          {open ? <ChevronUp size={14} className="text-muted-foreground" /> : <ChevronDown size={14} className="text-muted-foreground" />}
        </div>
      </button>
      {open && (
        <div className="px-5 pb-5">
          <div className="p-3 bg-secondary/40 rounded-lg mb-3">
            <p className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider mb-1">Verified Analogs Used</p>
            <div className="space-y-1.5">
              {analogs.map((analog, analogIndex) => (
                <p key={`${scenario.scenario_name}-${analogIndex}`} className="text-xs text-foreground font-medium">
                  {analog}
                </p>
              ))}
            </div>
          </div>
          {analogContexts.length > 0 && (
            <div className="space-y-2">
              {analogContexts.map(({ analog, info }) => (
                <div key={analog}>
                  <p className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider mb-1">
                    Why it matches
                  </p>
                  <p className="text-xs text-muted-foreground leading-relaxed">{info?.context}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function HistoricalAnalysisCard({
  evaluatedScenarios,
  showDetails,
  onToggle,
}: {
  evaluatedScenarios: EvaluatedScenario[];
  showDetails: boolean;
  onToggle: () => void;
}) {
  const analogCount = countEvaluatedAnalogs(evaluatedScenarios);
  const displayedScenarios = evaluatedScenarios.slice(0, 5);
  const hiddenScenarioCount = Math.max(evaluatedScenarios.length - displayedScenarios.length, 0);

  return (
    <Card className="shadow-sm h-full">
      <CardContent className="p-6">
        <div className="flex items-center gap-2 mb-4">
          <ShieldCheck size={16} className="text-accent" />
          <h4 className="text-lg font-semibold text-foreground">Historical Analysis</h4>
        </div>
        <p className="text-sm text-muted-foreground mb-5">
          Historical analogs the AI used to stress-test the thesis for this run.
        </p>
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="text-center p-4 bg-secondary/30 rounded-xl border border-border">
            <p className="text-3xl font-bold text-foreground tabular-nums">{analogCount}</p>
            <p className="text-xs text-muted-foreground mt-1.5 font-medium">Historical Analogs</p>
          </div>
          <div className="text-center p-4 bg-secondary/30 rounded-xl border border-border">
            <p className="text-3xl font-bold text-foreground tabular-nums">{evaluatedScenarios.length}</p>
            <p className="text-xs text-muted-foreground mt-1.5 font-medium">Scenario Buckets</p>
          </div>
        </div>
        <button
          onClick={onToggle}
          className="mb-4 flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <ShieldCheck size={12} />
          {showDetails ? "Hide" : "Show"} detailed historical analysis
          {showDetails ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </button>
        {showDetails && (
          evaluatedScenarios.length === 0 ? (
            <div className="rounded-xl border border-border bg-secondary/30 p-6 text-center">
              <p className="text-sm text-muted-foreground">
                No historical scenario precedents were triggered for this analysis. The agents relied on current
                SEC filings, market data, and news rather than macro-stress scenario analogs.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {displayedScenarios.map((s, i) => (
                <ScenarioDropdown key={`${s.scenario_name}-${i}`} scenario={s} index={i} />
              ))}
              {hiddenScenarioCount > 0 && (
                <p className="text-xs text-muted-foreground">
                  Showing the top 5 scenario buckets for readability. {hiddenScenarioCount} additional scenario{hiddenScenarioCount === 1 ? "" : "s"} not shown.
                </p>
              )}
            </div>
          )
        )}
      </CardContent>
    </Card>
  );
}

// ── Analyst "About" toggle card ───────────────────────────────────────────────
function AnalystAbout({ role }: { role: "bull" | "bear" | "strategist" }) {
  const [open, setOpen] = useState(false);
  const r = ANALYST_ROLES[role];
  return (
    <div className="mt-1 mb-4">
      <button
        className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <Info size={12} />
        <span>{open ? "Hide" : "About this analyst"}</span>
      </button>
      {open && (
        <div className="mt-2 p-3 bg-secondary/60 rounded-lg border border-border text-xs text-muted-foreground leading-relaxed">
          <p className="font-semibold text-foreground mb-0.5">{r.tagline}</p>
          <p>{r.description}</p>
        </div>
      )}
    </div>
  );
}

function AgentRolesTab() {
  return (
    <Card className="shadow-sm mb-8">
      <CardContent className="p-6">
        <h3 className="text-lg font-semibold text-foreground mb-2">What Each Agent Does</h3>
        <p className="text-sm text-muted-foreground mb-5">
          Bull, Bear, Strategist, and CIO each have distinct mandates so the final call is made after structured debate.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {AGENT_ROLES_TAB.map((agent) => (
            <div key={agent.key} className="rounded-lg border border-border p-4">
              <div className="flex items-center justify-between mb-2 gap-2">
                <h4 className="text-sm font-semibold text-foreground">{agent.title}</h4>
                <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${agent.accent}`}>
                  {agent.subtitle}
                </span>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed mb-3">{agent.role}</p>
              <p className="text-xs font-semibold text-foreground mb-1.5">Primary Focus</p>
              <ul className="space-y-1">
                {agent.focusesOn.map((line) => (
                  <li key={line} className="text-xs text-muted-foreground">• {line}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function WarningBanner({
  trafficColor,
  concentrationRisk,
}: {
  trafficColor?: string;
  concentrationRisk?: string;
}) {
  const isHighRisk = trafficColor === "red";
  const isConcentrated =
    concentrationRisk === "HIGH" || concentrationRisk === "VERY HIGH";

  if (!isHighRisk && !isConcentrated) return null;

  const messages: string[] = [];
  if (isHighRisk)
    messages.push(
      "🔴 High-risk signal: Bull and Bear analysts are strongly divided. Proceed with extra caution."
    );
  if (isConcentrated)
    messages.push(
      `⚠️ Portfolio concentration is ${concentrationRisk}: This position may breach the 15% single-stock guideline. Consider sizing down.`
    );

  return (
    <div className="mb-6 rounded-lg border border-amber-400 bg-amber-50 p-4 space-y-1.5">
      {messages.map((m, i) => (
        <p key={i} className="text-sm font-medium text-amber-800">
          {m}
        </p>
      ))}
    </div>
  );
}

function countSpeculativeClaims(claims: VerifiedClaim[]): number {
  return claims.filter((claim) => claim.is_speculative).length;
}

function ClaimList({
  claims,
  icon,
  iconColor,
  ticker,
  secFiling,
}: {
  claims: VerifiedClaim[];
  icon: React.ReactNode;
  iconColor: string;
  ticker?: string;
  secFiling?: SecFiling | null;
}) {
  const [citation, setCitation] = useState<{ claim: VerifiedClaim } | null>(null);

  return (
    <>
      <ul className="space-y-2">
        {claims.map((item, index) => (
          <li key={`${item.claim}-${index}`} className="flex items-start gap-2 text-sm text-muted-foreground">
            <span className={`shrink-0 mt-0.5 ${iconColor}`}>{icon}</span>
            <div className="min-w-0">
              <span>{item.claim}</span>
              {item.is_speculative && (
                <span className="ml-2 inline-flex rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-700">
                  speculative
                </span>
              )}
              {item.sec_section && ticker && (
                <button
                  onClick={() => setCitation({ claim: item })}
                  className="ml-2 inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-blue-700 hover:bg-blue-200 transition-colors cursor-pointer"
                  title={`View SEC source: ${item.sec_section}`}
                >
                  SEC ↗
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>

      {citation && ticker && (
        <CitationModal
          ticker={ticker}
          secSection={citation.claim.sec_section!}
          claimText={citation.claim.claim}
          filingUrl={secFiling?.filing_url}
          onClose={() => setCitation(null)}
        />
      )}
    </>
  );
}

// ── Evidence Scoring Components ───────────────────────────────────────────────

function ScoreBar({ label, score, max }: { label: string; score: number; max: number }) {
  const pct = Math.round((score / max) * 100);
  const color =
    pct >= 80 ? "bg-bull" : pct >= 60 ? "bg-amber-400" : pct >= 40 ? "bg-orange-400" : "bg-bear";
  return (
    <div>
      <div className="flex items-center justify-between text-xs mb-1">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-semibold tabular-nums text-foreground">
          {score}/{max}
        </span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-secondary overflow-hidden">
        <div
          className={`h-full rounded-full ${color} transition-all duration-700`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function EvidenceScoreCard({
  scores,
  weightedScore,
  agentColor,
  hallucinationPenalty = 0,
  speculativeClaimsCount = 0,
}: {
  scores: AgentEvidenceScore;
  weightedScore: number;
  agentColor: string;
  hallucinationPenalty?: number;
  speculativeClaimsCount?: number;
}) {
  const totalPct = Math.round((scores.total / 40) * 100);
  const ringColor =
    totalPct >= 75 ? "text-bull" : totalPct >= 55 ? "text-amber-500" : "text-bear";

  return (
    <div className="mt-4 pt-4 border-t border-border">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
          <FlaskConical size={13} className="text-muted-foreground" />
          Evidence Quality
        </div>
        <span className={`text-lg font-bold tabular-nums ${ringColor}`}>
          {scores.total}/40
        </span>
      </div>
      <div className="space-y-2">
        <ScoreBar label="Data Citations" score={scores.data_citations} max={10} />
        <ScoreBar label="Calculation Rigor" score={scores.calculation_rigor} max={10} />
        <ScoreBar label="Historical Precedent" score={scores.historical_precedent} max={10} />
        <ScoreBar label="Counterarguments" score={scores.counterargument} max={10} />
      </div>
      {hallucinationPenalty < 0 && (
        <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
          Hallucination penalty {hallucinationPenalty} for {speculativeClaimsCount} speculative claim
          {speculativeClaimsCount === 1 ? "" : "s"}.
        </div>
      )}
      <div className={`mt-3 pt-3 border-t border-border flex items-center justify-between`}>
        <div>
          <p className="text-xs text-muted-foreground">Weighted Score</p>
          <p className="text-xs text-muted-foreground/70">Conviction × Evidence</p>
        </div>
        <span className={`text-xl font-bold tabular-nums ${agentColor}`}>
          {weightedScore.toFixed(1)}
        </span>
      </div>
    </div>
  );
}

function EvidenceInlineBadge({
  scores,
  weightedScore,
}: {
  scores: AgentEvidenceScore;
  weightedScore: number;
}) {
  const totalPct = Math.round((scores.total / 40) * 100);
  const textColor =
    totalPct >= 75 ? "text-bull" : totalPct >= 55 ? "text-amber-600" : "text-bear";

  return (
    <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground bg-secondary/40 rounded-lg px-3 py-2">
      <FlaskConical size={12} className="shrink-0 text-muted-foreground" />
      <span>
        Evidence Quality:{" "}
        <span className={`font-semibold ${textColor}`}>{scores.total}/40</span>
        {" · "}
        Weighted:{" "}
        <span className={`font-semibold ${textColor}`}>{weightedScore.toFixed(1)}</span>
      </span>
    </div>
  );
}

function WeightedScoresPanel({ evidence }: { evidence: EvidenceAssessment }) {
  const agents = [
    { key: "bull", label: "🐂 Bull Analyst", weighted: evidence.bull_weighted, total: evidence.bull.total, color: "text-bull", bar: "bg-bull" },
    { key: "bear", label: "🐻 Bear Analyst", weighted: evidence.bear_weighted, total: evidence.bear.total, color: "text-bear", bar: "bg-bear" },
    { key: "strategist", label: "📊 Strategist", weighted: evidence.strategist_weighted, total: evidence.strategist.total, color: "text-strategist", bar: "bg-strategist" },
  ] as const;

  const maxWeighted = Math.max(evidence.bull_weighted, evidence.bear_weighted, evidence.strategist_weighted);

  return (
    <div className="mt-6 pt-6 border-t border-border">
      <div className="flex items-center gap-2 mb-4">
        <Trophy size={16} className="text-accent" />
        <h4 className="text-sm font-semibold text-foreground">Evidence-Weighted Decision</h4>
      </div>

      <div className="space-y-3 mb-4">
        {agents.map((a) => {
          const barPct = maxWeighted > 0 ? (a.weighted / maxWeighted) * 100 : 0;
          return (
            <div key={a.key} className="rounded-lg p-3 bg-secondary/40">
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-foreground">{a.label}</span>
                </div>
                <div className="text-right">
                  <span className={`text-base font-bold tabular-nums ${a.color}`}>
                    {a.weighted.toFixed(1)}
                  </span>
                  <span className="text-xs text-muted-foreground ml-1">
                    ({a.total}/40 evidence)
                  </span>
                </div>
              </div>
              <div className="h-1.5 w-full rounded-full bg-secondary overflow-hidden">
                <div
                  className={`h-full rounded-full ${a.bar} transition-all duration-700`}
                  style={{ width: `${barPct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {evidence.winner_reasoning && (
        <div className="text-xs text-muted-foreground leading-relaxed bg-secondary/40 rounded-lg p-3">
          {evidence.winner_reasoning}
        </div>
      )}
    </div>
  );
}

// ── Agent card sub-components (with evidence score accordion) ─────────────────

function BullCard({
  bull_analysis,
  evidence,
  ticker,
  secFiling,
}: {
  bull_analysis: BullAnalysis;
  evidence: EvidenceAssessment | null;
  ticker?: string;
  secFiling?: SecFiling | null;
}) {
  const [showEvidence, setShowEvidence] = useState(false);
  const speculativeClaimsCount =
    countSpeculativeClaims(bull_analysis.competitive_advantages) +
    countSpeculativeClaims(bull_analysis.growth_catalysts);
  const hallucinationPenalty = speculativeClaimsCount > 0 ? -20 : 0;
  return (
    <Card className="border-l-4 border-l-bull shadow-sm">
      <CardContent className="p-6">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-bull flex items-center justify-center">
              <TrendingUp className="text-white" size={14} />
            </div>
            <span className="font-semibold text-foreground">Bull Analyst</span>
            {speculativeClaimsCount > 0 && (
              <span className="text-[11px] font-semibold bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">
                {speculativeClaimsCount} speculative
              </span>
            )}
          </div>
          <span className="text-xs font-semibold bg-bull/10 text-bull px-2 py-1 rounded-full">
            {bull_analysis.confidence}/10
          </span>
        </div>
        <AnalystAbout role="bull" />
        <div className="h-1 w-full rounded-full bg-secondary mb-3">
          <div className="h-full rounded-full bg-bull" style={{ width: `${bull_analysis.confidence * 10}%` }} />
        </div>
        {/* Evidence inline badge — always visible */}
        {evidence && (
          <EvidenceInlineBadge scores={evidence.bull} weightedScore={evidence.bull_weighted} />
        )}
        <p className="text-xs text-muted-foreground mt-5 mb-1">Best Case Target</p>
        <p className="text-2xl font-bold text-foreground mb-0.5 tabular-nums">
          ${bull_analysis.best_case_target.toLocaleString()}
        </p>
        <p className="text-xs text-muted-foreground mb-5">{bull_analysis.best_case_timeline}</p>
        <p className="text-sm font-semibold text-foreground mb-3">Key Advantages</p>
        <ClaimList
          claims={bull_analysis.competitive_advantages}
          icon={<CheckCircle2 size={14} />}
          iconColor="text-bull"
          ticker={ticker}
          secFiling={secFiling}
        />
        <p className="text-xs font-semibold text-foreground mt-5 mb-2">Growth Catalysts</p>
        <ClaimList
          claims={bull_analysis.growth_catalysts}
          icon={<TrendingUp size={13} />}
          iconColor="text-bull"
          ticker={ticker}
          secFiling={secFiling}
        />
        {bull_analysis.valuation_justification && (
          <div className="mt-4 p-3 bg-bull/5 rounded-lg">
            <p className="text-xs font-semibold text-foreground mb-1">Valuation Justification</p>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {bull_analysis.valuation_justification}
            </p>
          </div>
        )}
        {evidence && (
          <>
            <button
              onClick={() => setShowEvidence((v) => !v)}
              className="mt-4 flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              <FlaskConical size={12} />
              {showEvidence ? "Hide" : "Show"} detailed evidence breakdown
              {showEvidence ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>
            {showEvidence && (
              <EvidenceScoreCard
                scores={evidence.bull}
                weightedScore={evidence.bull_weighted}
                agentColor="text-bull"
                hallucinationPenalty={hallucinationPenalty}
                speculativeClaimsCount={speculativeClaimsCount}
              />
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function BearCard({
  bear_analysis,
  evidence,
  ticker,
  secFiling,
}: {
  bear_analysis: BearAnalysis;
  evidence: EvidenceAssessment | null;
  ticker?: string;
  secFiling?: SecFiling | null;
}) {
  const [showEvidence, setShowEvidence] = useState(false);
  const speculativeClaimsCount =
    countSpeculativeClaims(bear_analysis.competition_threats) +
    countSpeculativeClaims(bear_analysis.cyclical_risks);
  const hallucinationPenalty = speculativeClaimsCount > 0 ? -20 : 0;
  return (
    <Card className="border-l-4 border-l-bear shadow-sm">
      <CardContent className="p-6">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-bear flex items-center justify-center">
              <AlertTriangle className="text-white" size={14} />
            </div>
            <span className="font-semibold text-foreground">Bear Analyst</span>
            {speculativeClaimsCount > 0 && (
              <span className="text-[11px] font-semibold bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">
                {speculativeClaimsCount} speculative
              </span>
            )}
          </div>
          <span className="text-xs font-semibold bg-bear/10 text-bear px-2 py-1 rounded-full">
            {bear_analysis.confidence}/10
          </span>
        </div>
        <AnalystAbout role="bear" />
        <div className="h-1 w-full rounded-full bg-secondary mb-3">
          <div className="h-full rounded-full bg-bear" style={{ width: `${bear_analysis.confidence * 10}%` }} />
        </div>
        {/* Evidence inline badge — always visible */}
        {evidence && (
          <EvidenceInlineBadge scores={evidence.bear} weightedScore={evidence.bear_weighted} />
        )}
        <p className="text-xs text-muted-foreground mt-5 mb-1">Worst Case Target</p>
        <p className="text-2xl font-bold text-foreground mb-0.5 tabular-nums">
          ${bear_analysis.worst_case_target.toLocaleString()}
        </p>
        <p className="text-xs text-muted-foreground mb-5">{bear_analysis.worst_case_timeline}</p>
        <p className="text-sm font-semibold text-foreground mb-3">Key Risks</p>
        <ClaimList
          claims={bear_analysis.competition_threats}
          icon={<AlertCircle size={14} />}
          iconColor="text-bear"
          ticker={ticker}
          secFiling={secFiling}
        />
        <div className="mt-5 p-3 bg-secondary rounded-lg">
          <p className="text-xs font-semibold text-foreground mb-1">Valuation Concerns</p>
          <p className="text-xs text-muted-foreground leading-relaxed">
            {bear_analysis.valuation_concerns}
          </p>
        </div>
        {bear_analysis.cyclical_risks.length > 0 && (
          <div className="mt-4">
            <p className="text-xs font-semibold text-foreground mb-2">Cyclical Risks</p>
            <ClaimList
              claims={bear_analysis.cyclical_risks}
              icon={<AlertTriangle size={13} />}
              iconColor="text-bear"
              ticker={ticker}
              secFiling={secFiling}
            />
          </div>
        )}
        {evidence && (
          <>
            <button
              onClick={() => setShowEvidence((v) => !v)}
              className="mt-4 flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              <FlaskConical size={12} />
              {showEvidence ? "Hide" : "Show"} detailed evidence breakdown
              {showEvidence ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>
            {showEvidence && (
              <EvidenceScoreCard
                scores={evidence.bear}
                weightedScore={evidence.bear_weighted}
                agentColor="text-bear"
                hallucinationPenalty={hallucinationPenalty}
                speculativeClaimsCount={speculativeClaimsCount}
              />
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function StrategistCard({
  strategist_analysis,
  evidence,
}: {
  strategist_analysis: StrategistAnalysis;
  evidence: EvidenceAssessment | null;
}) {
  const [showEvidence, setShowEvidence] = useState(false);
  return (
    <Card className="border-l-4 border-l-strategist shadow-sm">
      <CardContent className="p-6">
        <div className="flex items-center gap-2 mb-1">
          <div className="w-7 h-7 rounded-full bg-strategist flex items-center justify-center">
            <Target className="text-white" size={14} />
          </div>
          <span className="font-semibold text-foreground">Portfolio Strategist</span>
        </div>
        <AnalystAbout role="strategist" />
        <div className="h-1 w-full rounded-full bg-secondary mb-3">
          <div className="h-full rounded-full bg-strategist" style={{ width: "100%" }} />
        </div>
        {/* Evidence inline badge — always visible */}
        {evidence && (
          <EvidenceInlineBadge scores={evidence.strategist} weightedScore={evidence.strategist_weighted} />
        )}
        <p className="text-xs text-muted-foreground mt-5 mb-1">Current Exposure</p>
        <p className="text-xl font-bold text-foreground mb-3">{strategist_analysis.current_exposure}</p>
        <div className="flex items-center gap-2 mb-5">
          <span className="text-xs text-muted-foreground">Concentration Risk:</span>
          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${riskColor[strategist_analysis.concentration_risk] ?? "text-muted-foreground bg-secondary"}`}>
            {strategist_analysis.concentration_risk}
          </span>
        </div>
        <p className="text-xs text-muted-foreground mb-1">Recommended Allocation</p>
        <p className="text-2xl font-bold text-foreground mb-1 tabular-nums">
          ${strategist_analysis.recommended_allocation.toLocaleString()}
        </p>
        <p className="text-sm text-muted-foreground leading-relaxed mt-3">
          {strategist_analysis.reasoning}
        </p>
        {strategist_analysis.alternative_options.length > 0 && (
          <>
            <p className="text-xs font-semibold text-foreground mt-4 mb-2">Alternatives</p>
            <ul className="space-y-1">
              {strategist_analysis.alternative_options.map((o, i) => (
                <li key={i} className="text-xs text-muted-foreground">• {o}</li>
              ))}
            </ul>
          </>
        )}
        {evidence && (
          <>
            <button
              onClick={() => setShowEvidence((v) => !v)}
              className="mt-4 flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              <FlaskConical size={12} />
              {showEvidence ? "Hide" : "Show"} detailed evidence breakdown
              {showEvidence ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>
            {showEvidence && (
              <EvidenceScoreCard
                scores={evidence.strategist}
                weightedScore={evidence.strategist_weighted}
                agentColor="text-strategist"
              />
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

// ── Main Results component ────────────────────────────────────────────────────

const Results = () => {
  const navigate = useNavigate();
  const { analysisResult, formData } = useAnalysis();
  const [exporting, setExporting] = useState(false);
  const [showHistoricalAnalysis, setShowHistoricalAnalysis] = useState(false);
  const [showSourceLinks, setShowSourceLinks] = useState(false);

  const handleExportPdf = async () => {
    if (!analysisResult) return;
    setExporting(true);
    try {
      const res = await fetch(`${API_BASE}/export/pdf/${analysisResult.analysis_id}`);
      if (!res.ok) throw new Error(await res.text());
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `InvestiGate_${analysisResult.ticker}_${analysisResult.analysis_id.slice(0, 8)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Export failed");
    } finally {
      setExporting(false);
    }
  };

  if (!analysisResult) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center gap-4">
        <p className="text-muted-foreground">No analysis found.</p>
        <button onClick={() => navigate("/")} className="text-sm text-accent hover:text-accent/80">
          ← Start new analysis
        </button>
      </div>
    );
  }

  const {
    ticker,
    user_query,
    bull_analysis,
    bear_analysis,
    strategist_analysis,
    final_recommendation,
    market_data,
    traffic_light,
    portfolio_exposure,
    sec_filing,
    rag_summary,
    execution_time,
    timestamp,
    llm_provider,
    analysis_id,
  } = analysisResult;

  const evidence = final_recommendation.evidence_assessment ?? null;
  const proposedAmount = formData.amount ? parseFloat(formData.amount.replace(/,/g, "")) : 0;
  const analysisQuestion = (
    user_query?.trim()
    || formData.userQuery?.trim()
    || `Analyze ${ticker}`
  );
  const secSourceCount = rag_summary?.sec ?? rag_summary?.sec_docs ?? 0;
  const newsSourceCount = rag_summary?.news ?? rag_summary?.news_docs ?? 0;

  const md = market_data as Record<string, unknown> | null;
  const companyName = md?.longName as string | undefined;
  const sector      = md?.sector  as string | undefined;
  const currentPrice = md?.currentPrice as number | undefined;
  const regularMarketChange        = md?.regularMarketChange        as number | undefined;
  const regularMarketChangePercent = md?.regularMarketChangePercent as number | undefined;

  const breakdownData = Object.entries(final_recommendation.confidence_breakdown).map(([k, v]) => ({
    name: k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
    value: v as number,
  }));
  const secLinks = sec_filing
    ? [
        { label: "Item 1 - Business", url: sec_filing.section_urls.business },
        { label: "Item 1A - Risk Factors", url: sec_filing.section_urls.risk_factors },
        { label: "Item 7 - MD&A", url: sec_filing.section_urls.mda },
        { label: "Item 8 - Financials", url: sec_filing.section_urls.financials },
      ].filter((item) => Boolean(item.url))
    : [];
  const newsLinks = (Array.isArray(md?.recent_news) ? (md?.recent_news as MarketNewsItem[]) : [])
    .filter((item) => Boolean(item?.title) && Boolean(item?.link))
    .slice(0, 5);

  return (
    <div className="min-h-screen bg-background">
      {/* Report header bar */}
      <ReportHeaderBar
        analysisId={analysis_id}
        timestamp={timestamp}
        executionTime={execution_time}
        llmProvider={llm_provider}
      />

      {/* App nav header */}
      <header className="border-b border-border bg-card">
        <div className="container mx-auto flex items-center justify-between px-6 py-4">
          <h2 className="text-xl font-bold text-primary tracking-tight">InvestiGate</h2>
          <div className="flex items-center gap-4">
            <button onClick={() => navigate("/history")} className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              History
            </button>
            <button
              onClick={handleExportPdf}
              disabled={exporting}
              className="flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
            >
              {exporting ? <Loader2 size={14} className="animate-spin" /> : <FileDown size={14} />}
              Export PDF
            </button>
            <button onClick={() => navigate("/")} className="text-sm font-medium text-accent hover:text-accent/80 transition-colors">
              ← New Analysis
            </button>
          </div>
        </div>
      </header>

      <main className="container mx-auto max-w-6xl px-6 py-8 animate-fade-in">

        {/* Warning banner — shown before stock header for immediate visibility */}
        <WarningBanner
          trafficColor={traffic_light?.color}
          concentrationRisk={strategist_analysis.concentration_risk}
        />

        {/* Enhanced stock header */}
        <EnhancedStockHeader
          ticker={ticker}
          action={final_recommendation.action}
          confidenceOverall={final_recommendation.confidence_overall}
          trafficLightColor={final_recommendation.traffic_light_color}
          companyName={companyName}
          sector={sector}
          currentPrice={currentPrice}
          regularMarketChange={regularMarketChange}
          regularMarketChangePercent={regularMarketChangePercent}
          bullTarget={bull_analysis.best_case_target}
          bearTarget={bear_analysis.worst_case_target}
        />

        {/* Market metrics strip */}
        <MarketMetricsStrip marketData={market_data} />

        {/* ── §1 Executive Summary ───────────────────────────────────────────── */}
        <section className="mb-12">
          <h3 className="text-2xl font-bold text-foreground mb-5 flex items-center gap-2">
            <Scale className="text-accent" size={22} />
            §1 — Executive Summary
          </h3>
          <Card className="border-l-4 border-l-accent shadow-sm">
            <CardContent className="p-6">
              <div className="mb-6 rounded-xl border border-border bg-card p-4">
                <p className="text-xs text-muted-foreground uppercase tracking-wider mb-2 font-medium">
                  Question Asked
                </p>
                <p className="text-base text-foreground leading-relaxed">{analysisQuestion}</p>
              </div>
              {/* Metric grid — result first */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6 bg-secondary/30 p-4 rounded-xl border border-border/50">
                {[
                  { label: "Target Action",    value: final_recommendation.action.toUpperCase(), accent: true },
                  { label: "Amount",           value: `$${final_recommendation.recommended_amount.toLocaleString()}` },
                  { label: "Suggested Entry",  value: final_recommendation.entry_strategy },
                  { label: "Risk Management",  value: final_recommendation.risk_management },
                ].map((m) => (
                  <div key={m.label} className="text-center">
                    <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1 font-medium">{m.label}</p>
                    <p className={`text-sm font-bold ${m.accent ? "text-bull" : "text-foreground"} ${m.label === "Amount" ? "tabular-nums" : ""}`}>
                      {m.value}
                    </p>
                  </div>
                ))}
              </div>

              <p className="text-base text-muted-foreground leading-relaxed mb-6">
                {final_recommendation.reasoning}
              </p>

              {/* Key Decision Factors — numbered card grid */}
              <p className="text-sm font-semibold text-foreground mb-3 uppercase tracking-wider">Key Decision Factors</p>
              <div className="grid grid-cols-1 gap-2 mb-6">
                {final_recommendation.key_factors.map((f, i) => (
                  <div key={i} className="flex gap-3 rounded-lg border border-border p-3 bg-card">
                    <div className="w-6 h-6 rounded-full bg-accent flex items-center justify-center shrink-0 mt-0.5">
                      <span className="text-white text-[11px] font-bold">{i + 1}</span>
                    </div>
                    <p className="text-sm text-foreground leading-relaxed">{f}</p>
                  </div>
                ))}
              </div>
              {/* Evidence-Weighted Decision Panel — always visible */}
              {evidence && <WeightedScoresPanel evidence={evidence} />}
            </CardContent>
          </Card>
        </section>

        {/* Traffic Light */}
        {traffic_light && (
          <div className="mb-12">
            <TrafficLight trafficLight={traffic_light} />
          </div>
        )}

        {/* ── §3 Investment Thesis (Bull Case) ──────────────────────────────── */}
        <section className="mb-12">
          <h3 className="text-2xl font-bold text-foreground mb-6 flex items-center gap-2">
            §3 — Investment Thesis
            <span className="text-sm font-medium text-muted-foreground ml-2">(The Upside Case)</span>
          </h3>
          <BullCard
            bull_analysis={bull_analysis}
            evidence={evidence}
            ticker={ticker}
            secFiling={sec_filing}
          />
        </section>

        {/* ── §4 Principal Risks (Bear Case) ────────────────────────────────── */}
        <section className="mb-12">
          <h3 className="text-2xl font-bold text-foreground mb-6 flex items-center gap-2">
            §4 — Principal Risks
            <span className="text-sm font-medium text-muted-foreground ml-2">(The Downside Case)</span>
          </h3>
          <BearCard
            bear_analysis={bear_analysis}
            evidence={evidence}
            ticker={ticker}
            secFiling={sec_filing}
          />
        </section>

        {/* ── §5 Portfolio Allocation Strategy ──────────────────────────────── */}
        <section className="mb-16">
          <h3 className="text-2xl font-bold text-foreground mb-6">
            §5 — Portfolio Allocation Strategy
          </h3>
          <StrategistCard strategist_analysis={strategist_analysis} evidence={evidence} />

          {portfolio_exposure && (
            <div className="mt-6">
              <PortfolioExposure
                exposure={portfolio_exposure as ExposureData}
                ticker={ticker}
                proposedAmount={proposedAmount}
              />
            </div>
          )}
        </section>

        {/* Historical Analysis + Data Log */}
        {rag_summary && (
          <div className="grid gap-6 mb-12 lg:grid-cols-2">
            <HistoricalAnalysisCard
              evaluatedScenarios={final_recommendation.evaluated_scenarios}
              showDetails={showHistoricalAnalysis}
              onToggle={() => setShowHistoricalAnalysis((v) => !v)}
            />
            <Card className="shadow-sm h-full">
              <CardContent className="p-6">
                <div className="flex items-center gap-2 mb-4">
                  <Database size={16} className="text-accent" />
                  <h4 className="text-lg font-semibold text-foreground">Data Log</h4>
                </div>
                <p className="text-sm text-muted-foreground mb-5">
                  All sources indexed and retrieved for this analysis run.
                </p>
                <div className="grid grid-cols-3 gap-4 mb-4">
                  <div className="text-center p-4 bg-secondary/30 rounded-xl border border-border">
                    <p className="text-3xl font-bold text-foreground tabular-nums">{secSourceCount}</p>
                    <p className="text-xs text-muted-foreground mt-1.5 font-medium">SEC 10-K Sections</p>
                  </div>
                  <div className="text-center p-4 bg-secondary/30 rounded-xl border border-border">
                    <p className="text-3xl font-bold text-foreground tabular-nums">{newsSourceCount}</p>
                    <p className="text-xs text-muted-foreground mt-1.5 font-medium">News Articles</p>
                  </div>
                  <div className="text-center p-4 bg-secondary/30 rounded-xl border border-border">
                    <p className="text-3xl font-bold text-foreground tabular-nums">{countEvaluatedAnalogs(final_recommendation.evaluated_scenarios)}</p>
                    <p className="text-xs text-muted-foreground mt-1.5 font-medium">Historical Analogs</p>
                  </div>
                </div>
                <button
                  onClick={() => setShowSourceLinks((v) => !v)}
                  className="mb-4 flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  <Database size={12} />
                  {showSourceLinks ? "Hide" : "Show"} detailed source links
                  {showSourceLinks ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                </button>
                {showSourceLinks && (
                  <div className="grid gap-4 xl:grid-cols-2 mb-4">
                    <div className="rounded-xl border border-border bg-card p-4">
                      <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                        SEC Source Links
                      </p>
                      {secLinks.length > 0 ? (
                        <div className="space-y-2">
                          {secLinks.map((item) => (
                            <a
                              key={item.label}
                              href={item.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center justify-between gap-3 rounded-lg border border-border bg-secondary/30 px-3 py-2 text-sm text-foreground hover:border-accent/40 hover:bg-secondary/50 transition-colors"
                            >
                              <span>{item.label}</span>
                              <ExternalLink size={14} className="shrink-0 text-muted-foreground" />
                            </a>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-muted-foreground">SEC filing links are not available for this run.</p>
                      )}
                    </div>
                    <div className="rounded-xl border border-border bg-card p-4">
                      <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                        News Source Links
                      </p>
                      {newsLinks.length > 0 ? (
                        <div className="space-y-2">
                          {newsLinks.map((item, index) => (
                            <a
                              key={`${item.title}-${index}`}
                              href={item.link}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-start justify-between gap-3 rounded-lg border border-border bg-secondary/30 px-3 py-2 text-sm text-foreground hover:border-accent/40 hover:bg-secondary/50 transition-colors"
                            >
                              <div className="min-w-0">
                                <p>{item.title}</p>
                                {item.publisher && (
                                  <p className="text-xs text-muted-foreground mt-1">{item.publisher}</p>
                                )}
                              </div>
                              <ExternalLink size={14} className="shrink-0 text-muted-foreground mt-0.5" />
                            </a>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-muted-foreground">News source links are not available for this run.</p>
                      )}
                    </div>
                  </div>
                )}
                {rag_summary.cache_hit && (
                  <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                    <CheckCircle2 size={12} className="text-bull" />
                    Results served from cache — identical query run recently
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* ── Appendix ──────────────────────────────────────────────────────── */}
        <section className="mb-12 pt-8 border-t border-border">
          <h3 className="text-xl font-bold text-foreground mb-1">Appendix</h3>
          <p className="text-sm text-muted-foreground mb-8">Supporting analysis, data sources, and methodology.</p>

          {/* Confidence Analysis Chart */}
          <Card className="shadow-sm mb-8">
            <CardContent className="p-6">
              <h4 className="text-lg font-semibold text-foreground mb-1">Confidence Analysis</h4>
              <p className="text-sm text-muted-foreground mb-6">AI conviction scores across key dimensions</p>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={breakdownData} layout="vertical" margin={{ left: 20 }}>
                    <XAxis
                      type="number"
                      domain={[0, 100]}
                      tick={{ fontSize: 12, fill: "hsl(220 9% 46%)" }}
                      tickFormatter={(v: number) => `${v}%`}
                    />
                    <YAxis type="category" dataKey="name" tick={{ fontSize: 12, fill: "hsl(220 13% 13%)" }} width={140} />
                    <Tooltip
                      formatter={(value: number) => [`${value}%`, "Score"]}
                      contentStyle={{ borderRadius: 8, border: "1px solid hsl(220 13% 91%)", boxShadow: "0 1px 3px rgba(0,0,0,0.08)" }}
                    />
                    <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={20}>
                      {breakdownData.map((_, i) => (
                        <Cell key={i} fill={`hsl(239 84% ${67 - i * 5}%)`} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Agent Roles */}
          <AgentRolesTab />

          {/* Methodology */}
          <Card className="shadow-sm mb-8">
            <CardContent className="p-6">
              <div className="flex items-center gap-2 mb-4">
                <BookOpen size={16} className="text-accent" />
                <h4 className="text-lg font-semibold text-foreground">Methodology</h4>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed mb-4">
                InvestiGate uses a four-agent adversarial debate framework to generate balanced investment analysis:
              </p>
              <div className="space-y-3">
                {[
                  { step: "1", title: "Intent Routing", desc: "User query is parsed to identify ticker, action intent, and applicable macro scenarios (AI disruption, geopolitical risk, etc.)." },
                  { step: "2", title: "RAG Grounding", desc: "SEC 10-K filings and recent news are retrieved and embedded. Historical analog documents are retrieved for detected scenario tags." },
                  { step: "3", title: "Parallel Debate", desc: "Bull, Bear, and Strategist agents run concurrently, each constrained to build the strongest case for their mandate using the retrieved evidence." },
                  { step: "4", title: "Evidence Scoring", desc: "Each agent's output is scored on data citations, calculation rigor, historical precedent, and counterarguments (0–40 scale)." },
                  { step: "5", title: "Judge Decision", desc: "The CIO / Judge weights conviction against evidence quality, selects the winning argument, and outputs the final recommendation with confidence breakdown." },
                ].map((s) => (
                  <div key={s.step} className="flex gap-3">
                    <div className="w-6 h-6 rounded-full bg-accent/10 flex items-center justify-center shrink-0 mt-0.5">
                      <span className="text-accent text-[11px] font-bold">{s.step}</span>
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-foreground">{s.title}</p>
                      <p className="text-xs text-muted-foreground leading-relaxed">{s.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Disclaimer */}
          <div className="p-4 bg-secondary/30 rounded-xl border border-border">
            <div className="flex items-center gap-1.5 mb-2">
              <ShieldCheck size={14} className="text-muted-foreground" />
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Disclaimer</p>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              This report is generated by an AI system and is provided for informational and educational
              purposes only. It does not constitute financial advice, an offer to buy or sell securities, or
              a solicitation of any investment decision. Past performance of historical analogs does not
              guarantee future results. AI-generated analysis may contain errors, outdated information, or
              speculative claims — always verify independently before making investment decisions. Consult a
              qualified financial advisor before acting on any analysis in this report.
            </p>
          </div>
        </section>
      </main>
    </div>
  );
};

export default Results;
