import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  TrendingUp, TrendingDown, Pause, Mic, MicOff,
  ChevronRight, Loader2, Search, Bell, BarChart2, X, Zap
} from "lucide-react";
import { motion } from "framer-motion";
import CountUp from "react-countup";
import {
  AreaChart, Area, Tooltip, ResponsiveContainer,
} from "recharts";
import { useAnalysis, type AnalysisAction } from "@/context/AnalysisContext";
import PortfolioReportCard, { type PortfolioReport } from "@/components/PortfolioReportCard";

const API_BASE = (import.meta.env.VITE_API_URL as string) || "http://localhost:8000";

interface Holding {
  ticker: string;
  name?: string;
  value: number;
  cost_basis?: number;
  shares?: number;
  sector?: string;
}

interface GrowthPoint { month: string; value: number; }

interface Portfolio {
  holdings: Holding[];
  total_value: number;
  cash?: number;
  growth_history?: GrowthPoint[];
}

// ── Mini portfolio sparkline ────────────────────────────────────────────────
function PortfolioChart({ data, positive }: { data: GrowthPoint[]; positive: boolean }) {
  const color = positive ? "#22c55e" : "#ef4444";
  return (
    <ResponsiveContainer width="100%" height={80}>
      <AreaChart data={data} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor={color} stopOpacity={0.25} />
            <stop offset="95%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Tooltip
          contentStyle={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 8, fontSize: 11 }}
          formatter={(v: number) => [`$${v.toLocaleString()}`, "Value"]}
          labelStyle={{ color: "#6b7280", fontWeight: 600 }}
        />
        <Area
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={2}
          fill="url(#chartGrad)"
          dot={false}
          activeDot={{ r: 4, fill: color }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

// ── Gradient ticker avatar ─────────────────────────────────────────────────
const AVATAR_GRADIENTS = [
  "from-blue-500 to-indigo-600",
  "from-violet-500 to-purple-600",
  "from-emerald-500 to-teal-600",
  "from-orange-500 to-amber-600",
  "from-rose-500 to-pink-600",
  "from-sky-500 to-cyan-600",
  "from-lime-500 to-green-600",
  "from-fuchsia-500 to-pink-600",
];

function TickerAvatar({ ticker }: { ticker: string }) {
  const idx = ticker.charCodeAt(0) % AVATAR_GRADIENTS.length;
  return (
    <div className={`w-10 h-10 rounded-full bg-gradient-to-br ${AVATAR_GRADIENTS[idx]} flex items-center justify-center shrink-0 shadow-sm`}>
      <span className="text-[10px] font-bold text-white tracking-tight">
        {ticker.slice(0, 2)}
      </span>
    </div>
  );
}

// Fake sparkline path for visual flair
function Sparkline({ positive }: { positive: boolean }) {
  const pts = positive
    ? "M0,20 C10,18 20,22 30,16 C40,10 50,14 60,8 C70,4 80,6 90,2 C95,1 98,2 100,0"
    : "M0,0 C10,2 20,1 30,6 C40,10 50,8 60,14 C70,18 80,16 90,20 C95,21 98,20 100,22";
  return (
    <svg viewBox="0 0 100 24" className="w-16 h-6" preserveAspectRatio="none">
      <path d={pts} fill="none" stroke={positive ? "#22c55e" : "#f43f5e"} strokeWidth="1.5" />
    </svg>
  );
}

const ACTION_CONFIG = {
  buy: {
    label: "Buy More",
    icon: TrendingUp,
    color: "text-emerald-400",
    border: "border-emerald-500/50",
    bg: "bg-emerald-500",
    desc: "Agents debate adding to this position",
  },
  hold: {
    label: "Hold",
    icon: Pause,
    color: "text-amber-400",
    border: "border-amber-500/50",
    bg: "bg-amber-500",
    desc: "Agents debate maintaining vs. trimming",
  },
  sell: {
    label: "Sell",
    icon: TrendingDown,
    color: "text-rose-400",
    border: "border-rose-500/50",
    bg: "bg-rose-500",
    desc: "Agents debate exiting this position",
  },
};

export default function Landing() {
  const navigate = useNavigate();
  const { setFormData, setAnalysisAction, setPlaidHoldings } = useAnalysis();

  const [portfolio, setPortfolio]           = useState<Portfolio | null>(null);
  const [loading, setLoading]               = useState(true);
  const [portfolioReport, setPortfolioReport] = useState<PortfolioReport | null>(null);

  // Which holding row is expanded
  const [expandedTicker, setExpandedTicker] = useState<string | null>(null);
  const [selectedAction, setSelectedAction] = useState<AnalysisAction>("buy");

  // Custom ticker panel
  const [showSearch, setShowSearch] = useState(false);
  const [searchTicker, setSearchTicker] = useState("");

  // Analysis params
  const [amount, setAmount] = useState("5000");
  const [riskTolerance, setRiskTolerance] = useState("moderate");
  const [timeHorizon, setTimeHorizon] = useState("1 year");

  // Voice
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  // Load portfolio + run Tier-1 analysis
  useEffect(() => {
    fetch(`${API_BASE}/api/portfolio/demo`)
      .then((r) => r.json())
      .then((data: Portfolio) => {
        setPortfolio(data);
        setPlaidHoldings(
          data.holdings.map((h) => ({
            ticker: h.ticker,
            value: h.value,
            name: h.name,
            shares: h.shares,
            cost_basis: h.cost_basis,
          }))
        );
        // Tier-1: automatic portfolio analysis
        return fetch(`${API_BASE}/api/portfolio/demo/analyze`);
      })
      .then((r) => r.json())
      .then((report: PortfolioReport) => setPortfolioReport(report))
      .catch(() => setPortfolio(null))
      .finally(() => setLoading(false));
  }, []);

  // Tier-2: launch 4-agent deep analysis from the report card
  const handleReportAnalyze = (ticker: string) => {
    const portfolioValue = portfolio?.total_value ?? 80000;
    const holding = portfolio?.holdings.find((h) => h.ticker === ticker);
    const suggestedAmount = holding
      ? String(Math.round(Math.max(500, Math.min(holding.value * 0.1, 10000)) / 100) * 100)
      : amount;
    setFormData({
      ticker,
      amount: suggestedAmount,
      portfolio: String(portfolioValue),
      riskTolerance,
      timeHorizon,
    });
    setAnalysisAction("hold"); // default to "hold" for existing positions
    navigate("/loading");
  };

  const handleRowClick = (ticker: string, currentValue: number) => {
    if (expandedTicker === ticker) {
      setExpandedTicker(null);
    } else {
      setExpandedTicker(ticker);
      setSelectedAction("buy");
      const suggested = Math.round((currentValue * 0.1) / 100) * 100;
      setAmount(String(Math.max(500, Math.min(suggested, 10000))));
      setShowSearch(false);
    }
  };

  const handleInvestigate = (ticker: string, isSearch = false) => {
    const portfolioValue = portfolio?.total_value ?? 80000;
    setFormData({
      ticker: isSearch ? searchTicker.trim().toUpperCase() : ticker,
      amount,
      portfolio: String(portfolioValue),
      riskTolerance,
      timeHorizon,
    });
    setAnalysisAction(selectedAction);
    navigate("/loading");
  };

  const toggleVoice = () => {
    if (listening) {
      recognitionRef.current?.stop();
      setListening(false);
      return;
    }
    const SR =
      (window as unknown as { SpeechRecognition?: typeof SpeechRecognition }).SpeechRecognition ??
      (window as unknown as { webkitSpeechRecognition?: typeof SpeechRecognition }).webkitSpeechRecognition;
    if (!SR) return;
    const rec = new SR();
    rec.lang = "en-US";
    rec.onresult = (e) => {
      const text = e.results[0][0].transcript;
      const m = text.match(/\b([A-Z]{1,5})\b/);
      const a = text.match(/\$?([\d,]+)/);
      if (m) setSearchTicker(m[1]);
      if (a) setAmount(a[1].replace(/,/g, ""));
    };
    rec.onend = () => setListening(false);
    recognitionRef.current = rec;
    rec.start();
    setListening(true);
  };

  // Totals
  const totalGain = portfolio
    ? portfolio.holdings.reduce(
      (sum, h) => sum + (h.cost_basis ? h.value - h.cost_basis : 0),
      0
    )
    : 0;
  const totalCost = portfolio
    ? portfolio.holdings.reduce((sum, h) => sum + (h.cost_basis ?? h.value), 0)
    : 0;
  const totalGainPct = totalCost > 0 ? (totalGain / totalCost) * 100 : 0;

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 flex flex-col">
      {/* ── Top nav ──────────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-20 bg-white/95 backdrop-blur border-b border-gray-200 shadow-sm">
        <div className="max-w-lg mx-auto px-4 py-3 flex items-center justify-between">
          <span className="font-bold text-lg tracking-tight text-gray-900">
            Investi<span className="text-blue-600">Gate</span>
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigate("/portfolio")}
              className="p-2 rounded-full hover:bg-gray-100 transition-colors text-gray-500 hover:text-gray-900"
              title="Portfolio Dashboard"
            >
              <BarChart2 className="w-4 h-4" />
            </button>
            <button className="p-2 rounded-full hover:bg-gray-100 transition-colors text-gray-500 hover:text-gray-900">
              <Bell className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-lg mx-auto w-full px-4 pb-24 flex-1">

        {/* ── Portfolio hero ──────────────────────────────────────────────────── */}
        <motion.section
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45 }}
          className="pt-6 pb-2"
        >
          {loading ? (
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 space-y-3 animate-pulse">
              <div className="h-3 w-28 bg-gray-200 rounded mx-auto" />
              <div className="h-12 w-40 bg-gray-200 rounded mx-auto" />
              <div className="h-5 w-36 bg-gray-200 rounded mx-auto" />
              <div className="h-20 bg-gray-100 rounded-xl" />
            </div>
          ) : (
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="px-6 pt-6 pb-4 text-center">
                <p className="text-xs text-gray-500 font-semibold uppercase tracking-widest mb-1">
                  Total Portfolio Value
                </p>
                <h1 className="text-5xl font-bold tracking-tight text-gray-900 mb-1 tabular-nums">
                  $<CountUp
                    end={portfolio?.total_value ?? 0}
                    duration={1.4}
                    separator=","
                    decimals={0}
                  />
                </h1>
                <div
                  className={`inline-flex items-center gap-1.5 text-sm font-semibold px-3 py-1 rounded-full ${
                    totalGainPct >= 0
                      ? "text-green-600 bg-green-50"
                      : "text-red-600 bg-red-50"
                  }`}
                >
                  {totalGainPct >= 0 ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
                  {totalGainPct >= 0 ? "+" : ""}
                  {totalGainPct.toFixed(2)}% (
                  {totalGain >= 0 ? "+" : "−"}$
                  {Math.abs(totalGain).toLocaleString(undefined, { maximumFractionDigits: 0 })})
                  <span className="text-gray-400 font-normal">all‑time</span>
                </div>
              </div>

              {/* Recharts area sparkline */}
              {portfolio?.growth_history && portfolio.growth_history.length > 1 && (
                <div className="px-2 pb-3">
                  <PortfolioChart data={portfolio.growth_history} positive={totalGainPct >= 0} />
                </div>
              )}
            </div>
          )}
        </motion.section>

        {/* ── Search / custom ticker ──────────────────────────────────────────── */}
        <div className="mb-4 mt-4">
          {!showSearch ? (
            <button
              onClick={() => {
                setShowSearch(true);
                setExpandedTicker(null);
              }}
              className="w-full flex items-center gap-3 px-4 py-3 rounded-2xl bg-white border border-gray-200 shadow-sm text-gray-500 hover:border-blue-400 hover:text-gray-900 transition-all text-sm"
            >
              <Search className="w-4 h-4 shrink-0" />
              <span>Search or enter a new ticker to analyze…</span>
            </button>
          ) : (
            <div className="rounded-2xl bg-white border border-blue-400 shadow-md overflow-hidden">
              <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-100">
                <Search className="w-4 h-4 text-gray-400 shrink-0" />
                <input
                  autoFocus
                  type="text"
                  value={searchTicker}
                  onChange={(e) => setSearchTicker(e.target.value.toUpperCase())}
                  placeholder="NVDA, AAPL, BTC-USD…"
                  className="flex-1 bg-transparent text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none font-mono"
                />
                <button
                  onClick={toggleVoice}
                  className={`p-1.5 rounded-full transition-colors ${listening ? "text-red-500 bg-red-50" : "text-gray-400 hover:text-gray-700"}`}
                >
                  {listening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                </button>
                <button onClick={() => setShowSearch(false)} className="text-gray-400 hover:text-gray-700">
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Action + params for search */}
              {searchTicker.length >= 1 && (
                <div className="p-4 space-y-4">
                  {/* Action selector */}
                  <div className="grid grid-cols-3 gap-2">
                    {(Object.keys(ACTION_CONFIG) as AnalysisAction[]).map((a) => {
                      const cfg = ACTION_CONFIG[a];
                      const Icon = cfg.icon;
                      return (
                        <button
                          key={a}
                          onClick={() => setSelectedAction(a)}
                          className={`flex flex-col items-center gap-1 py-2.5 rounded-xl border text-xs font-semibold transition-all ${selectedAction === a
                              ? `${cfg.color} ${cfg.border} bg-muted/40`
                              : "border-border text-muted-foreground hover:text-foreground"
                            }`}
                        >
                          <Icon className="w-4 h-4" />
                          {cfg.label}
                        </button>
                      );
                    })}
                  </div>
                  {/* Params */}
                  <AnalysisParams
                    amount={amount}
                    setAmount={setAmount}
                    riskTolerance={riskTolerance}
                    setRiskTolerance={setRiskTolerance}
                    timeHorizon={timeHorizon}
                    setTimeHorizon={setTimeHorizon}
                  />
                  <button
                    onClick={() => handleInvestigate(searchTicker, true)}
                    disabled={!searchTicker.trim()}
                    className={`w-full py-3 rounded-xl font-bold text-sm text-white transition-all active:scale-[0.98] disabled:opacity-40 ${ACTION_CONFIG[selectedAction].bg
                      }`}
                  >
                    Investigate {searchTicker} — {ACTION_CONFIG[selectedAction].label} →
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* ── Tier-1 Portfolio Analysis Report ────────────────────────────────── */}
        {!loading && portfolioReport && (
          <PortfolioReportCard
            report={portfolioReport}
            onAnalyze={handleReportAnalyze}
          />
        )}

        {/* ── Holdings list ───────────────────────────────────────────────────── */}
        <section>
          <p className="text-xs uppercase tracking-widest text-gray-500 font-semibold px-1 mb-3">
            Holdings
          </p>

          {loading ? (
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden divide-y divide-gray-100">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="flex items-center gap-3 px-4 py-4 animate-pulse">
                  <div className="w-10 h-10 rounded-full bg-gray-200" />
                  <div className="flex-1 space-y-1.5">
                    <div className="h-3 w-16 bg-gray-200 rounded" />
                    <div className="h-2.5 w-28 bg-gray-100 rounded" />
                  </div>
                  <div className="space-y-1.5">
                    <div className="h-3 w-14 bg-gray-200 rounded" />
                    <div className="h-2.5 w-10 bg-gray-100 rounded" />
                  </div>
                </div>
              ))}
            </div>
          ) : portfolio ? (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.15 }}
              className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden divide-y divide-gray-50"
            >
              {portfolio.holdings.map((holding) => {
                const gainLoss = holding.cost_basis
                  ? holding.value - holding.cost_basis
                  : null;
                const gainPct =
                  holding.cost_basis && gainLoss !== null
                    ? (gainLoss / holding.cost_basis) * 100
                    : null;
                const positive = gainPct === null ? true : gainPct >= 0;
                const isExpanded = expandedTicker === holding.ticker;

                return (
                  <div key={holding.ticker}>
                    {/* ── Row ── */}
                    <button
                      onClick={() => handleRowClick(holding.ticker, holding.value)}
                      className={`w-full flex items-center gap-3 px-4 py-3.5 hover:bg-gray-50 transition-colors text-left ${isExpanded ? "bg-blue-50/50" : ""}`}
                    >
                      {/* Gradient avatar */}
                      <TickerAvatar ticker={holding.ticker} />

                      {/* Name + sector */}
                      <div className="flex-1 min-w-0">
                        <div className="font-semibold text-sm text-gray-900">{holding.ticker}</div>
                        <div className="text-xs text-gray-500 truncate">
                          {holding.name ?? holding.sector ?? "—"}
                        </div>
                      </div>

                      {/* Sparkline */}
                      <Sparkline positive={positive} />

                      {/* Value + gain */}
                      <div className="text-right shrink-0">
                        <div className="font-semibold text-sm text-gray-900 tabular-nums">
                          ${holding.value.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                        </div>
                        {gainPct !== null ? (
                          <div className={`text-xs font-semibold ${gainPct >= 0 ? "text-green-600" : "text-red-500"}`}>
                            {gainPct >= 0 ? "+" : ""}{gainPct.toFixed(2)}%
                          </div>
                        ) : (
                          <div className="text-xs text-gray-400">
                            {holding.shares ? `${holding.shares} sh` : ""}
                          </div>
                        )}
                      </div>

                      <ChevronRight
                        className={`w-4 h-4 text-gray-300 shrink-0 transition-transform duration-200 ${isExpanded ? "rotate-90 text-blue-500" : ""}`}
                      />
                    </button>

                    {/* ── Expanded action panel ── */}
                    {isExpanded && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        transition={{ duration: 0.2 }}
                        className="px-4 pb-5 pt-3 bg-gray-50 border-t border-gray-100 space-y-4"
                      >
                        {/* Action selector */}
                        <div className="grid grid-cols-3 gap-2">
                          {(Object.keys(ACTION_CONFIG) as AnalysisAction[]).map((a) => {
                            const cfg = ACTION_CONFIG[a];
                            const Icon = cfg.icon;
                            const isActive = selectedAction === a;
                            return (
                              <button
                                key={a}
                                onClick={() => setSelectedAction(a)}
                                className={`flex flex-col items-center gap-1.5 py-3 rounded-xl border font-semibold text-xs transition-all ${
                                  isActive
                                    ? `${cfg.color} ${cfg.border} bg-white shadow-sm`
                                    : "border-gray-200 text-gray-500 hover:text-gray-700 bg-white"
                                }`}
                              >
                                <Icon className="w-4 h-4" />
                                {cfg.label}
                              </button>
                            );
                          })}
                        </div>

                        {/* Description */}
                        <p className="text-xs text-gray-500 text-center">
                          {ACTION_CONFIG[selectedAction].desc}
                        </p>

                        {/* Parameters */}
                        <AnalysisParams
                          amount={amount}
                          setAmount={setAmount}
                          riskTolerance={riskTolerance}
                          setRiskTolerance={setRiskTolerance}
                          timeHorizon={timeHorizon}
                          setTimeHorizon={setTimeHorizon}
                        />

                        {/* CTA */}
                        <button
                          onClick={() => handleInvestigate(holding.ticker)}
                          className={`w-full py-3.5 rounded-xl font-bold text-sm text-white transition-all active:scale-[0.98] shadow-sm ${ACTION_CONFIG[selectedAction].bg} hover:opacity-90`}
                        >
                          <span className="flex items-center justify-center gap-2">
                            <Zap className="w-4 h-4" />
                            Investigate {holding.ticker} — {ACTION_CONFIG[selectedAction].label}
                          </span>
                        </button>
                      </motion.div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-sm text-gray-500 text-center py-8">
              Could not load portfolio.
            </p>
          )}
        </section>

        {/* ── 4-agent legend ───────────────────────────────────────────────────── */}
        {!expandedTicker && !showSearch && (
          <motion.section
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="mt-6 bg-white rounded-2xl shadow-sm border border-gray-100 p-5"
          >
            <p className="text-xs text-gray-500 font-semibold mb-4 text-center uppercase tracking-widest">
              4-Agent Debate Engine
            </p>
            <div className="grid grid-cols-4 gap-3 text-center">
              {[
                { e: "🐂", t: "Bull",       d: "Upside case",    bg: "bg-green-50",   txt: "text-green-700"  },
                { e: "🐻", t: "Bear",        d: "Risk case",      bg: "bg-red-50",     txt: "text-red-700"    },
                { e: "📊", t: "Strategist",  d: "Portfolio fit",  bg: "bg-blue-50",    txt: "text-blue-700"   },
                { e: "⚖️", t: "CIO",         d: "Final call",     bg: "bg-purple-50",  txt: "text-purple-700" },
              ].map((a) => (
                <div key={a.t} className={`rounded-xl ${a.bg} py-3 px-2`}>
                  <div className="text-xl mb-1">{a.e}</div>
                  <div className={`text-xs font-bold ${a.txt}`}>{a.t}</div>
                  <div className="text-[10px] text-gray-500 mt-0.5">{a.d}</div>
                </div>
              ))}
            </div>
          </motion.section>
        )}
      </div>
    </div>
  );
}

// ─── Shared analysis params ────────────────────────────────────────────────────
function AnalysisParams({
  amount, setAmount,
  riskTolerance, setRiskTolerance,
  timeHorizon, setTimeHorizon,
}: {
  amount: string; setAmount: (v: string) => void;
  riskTolerance: string; setRiskTolerance: (v: string) => void;
  timeHorizon: string; setTimeHorizon: (v: string) => void;
}) {
  return (
    <div className="grid grid-cols-3 gap-2">
      <div>
        <label className="text-[10px] text-gray-500 uppercase tracking-widest mb-1 block font-semibold">Amount</label>
        <div className="relative">
          <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400 text-xs">$</span>
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className="w-full bg-white border border-gray-200 rounded-lg pl-6 pr-2 py-2 text-xs text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 tabular-nums"
          />
        </div>
      </div>
      <div>
        <label className="text-[10px] text-gray-500 uppercase tracking-widest mb-1 block font-semibold">Risk</label>
        <select
          value={riskTolerance}
          onChange={(e) => setRiskTolerance(e.target.value)}
          className="w-full bg-white border border-gray-200 rounded-lg px-2 py-2 text-xs text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500/30"
        >
          <option value="conservative">Low</option>
          <option value="moderate">Mid</option>
          <option value="aggressive">High</option>
        </select>
      </div>
      <div>
        <label className="text-[10px] text-gray-500 uppercase tracking-widest mb-1 block font-semibold">Horizon</label>
        <select
          value={timeHorizon}
          onChange={(e) => setTimeHorizon(e.target.value)}
          className="w-full bg-white border border-gray-200 rounded-lg px-2 py-2 text-xs text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500/30"
        >
          <option value="3 months">3 mo</option>
          <option value="6 months">6 mo</option>
          <option value="1 year">1 yr</option>
          <option value="3 years">3 yr</option>
          <option value="5+ years">5+ yr</option>
        </select>
      </div>
    </div>
  );
}
