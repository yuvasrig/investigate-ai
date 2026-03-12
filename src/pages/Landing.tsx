import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  TrendingUp, TrendingDown, Pause, Mic, MicOff,
  ChevronRight, Loader2, Search, Bell, BarChart2, X
} from "lucide-react";
import { useAnalysis, type AnalysisAction } from "@/context/AnalysisContext";

const API_BASE = (import.meta.env.VITE_API_URL as string) || "http://localhost:8000";

interface Holding {
  ticker: string;
  name?: string;
  value: number;
  cost_basis?: number;
  shares?: number;
  sector?: string;
}

interface Portfolio {
  holdings: Holding[];
  total_value: number;
  cash?: number;
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

  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [loading, setLoading] = useState(true);

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

  // Load portfolio
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
      })
      .catch(() => setPortfolio(null))
      .finally(() => setLoading(false));
  }, []);

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
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      {/* ── Top nav ──────────────────────────────────────────────────────────── */}
      <header className="sticky top-0 z-20 bg-background/95 backdrop-blur border-b border-border/50">
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center justify-between">
          <span className="font-bold text-lg tracking-tight">
            Investi<span className="text-accent">Gate</span>
          </span>
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate("/portfolio")}
              className="p-2 rounded-full hover:bg-muted/50 transition-colors text-muted-foreground hover:text-foreground"
              title="Portfolio Dashboard"
            >
              <BarChart2 className="w-4 h-4" />
            </button>
            <button className="p-2 rounded-full hover:bg-muted/50 transition-colors text-muted-foreground hover:text-foreground">
              <Bell className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-2xl mx-auto w-full px-4 pb-24 flex-1">

        {/* ── Portfolio hero ──────────────────────────────────────────────────── */}
        <section className="py-6 text-center">
          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <>
              <p className="text-xs text-muted-foreground uppercase tracking-widest mb-1 font-medium">
                Portfolio Value
              </p>
              <h1 className="text-5xl font-bold tracking-tight text-foreground mb-1">
                ${portfolio?.total_value.toLocaleString(undefined, { maximumFractionDigits: 0 }) ?? "—"}
              </h1>
              <div
                className={`inline-flex items-center gap-1.5 text-sm font-semibold mt-1 px-3 py-1 rounded-full ${totalGainPct >= 0
                    ? "text-emerald-400 bg-emerald-500/10"
                    : "text-rose-400 bg-rose-500/10"
                  }`}
              >
                {totalGainPct >= 0 ? (
                  <TrendingUp className="w-4 h-4" />
                ) : (
                  <TrendingDown className="w-4 h-4" />
                )}
                {totalGainPct >= 0 ? "+" : ""}
                {totalGainPct.toFixed(2)}%&nbsp; (
                {totalGain >= 0 ? "+" : ""}$
                {Math.abs(totalGain).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                )&nbsp; all‑time
              </div>
            </>
          )}
        </section>

        {/* ── Search / custom ticker ──────────────────────────────────────────── */}
        <div className="mb-4">
          {!showSearch ? (
            <button
              onClick={() => {
                setShowSearch(true);
                setExpandedTicker(null);
              }}
              className="w-full flex items-center gap-3 px-4 py-3 rounded-2xl bg-muted/30 border border-border/50 text-muted-foreground hover:border-accent/40 hover:text-foreground transition-all text-sm"
            >
              <Search className="w-4 h-4 shrink-0" />
              <span>Search or enter a new ticker to analyze…</span>
            </button>
          ) : (
            <div className="rounded-2xl bg-card border border-accent/40 overflow-hidden">
              <div className="flex items-center gap-3 px-4 py-3 border-b border-border/50">
                <Search className="w-4 h-4 text-muted-foreground shrink-0" />
                <input
                  autoFocus
                  type="text"
                  value={searchTicker}
                  onChange={(e) => setSearchTicker(e.target.value.toUpperCase())}
                  placeholder="NVDA, AAPL, BTC-USD…"
                  className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none font-mono"
                />
                <button
                  onClick={toggleVoice}
                  className={`p-1.5 rounded-full transition-colors ${listening ? "text-rose-400 bg-rose-500/10" : "text-muted-foreground hover:text-foreground"
                    }`}
                >
                  {listening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                </button>
                <button onClick={() => setShowSearch(false)} className="text-muted-foreground hover:text-foreground">
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

        {/* ── Holdings list ───────────────────────────────────────────────────── */}
        <section>
          <p className="text-xs uppercase tracking-widest text-muted-foreground font-medium px-1 mb-3">
            Holdings
          </p>

          {loading ? (
            <div className="space-y-3">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="h-16 rounded-2xl bg-muted/20 animate-pulse" />
              ))}
            </div>
          ) : portfolio ? (
            <div className="rounded-2xl bg-card border border-border/50 overflow-hidden divide-y divide-border/40">
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
                      className={`w-full flex items-center gap-3 px-4 py-4 hover:bg-muted/20 transition-colors text-left ${isExpanded ? "bg-muted/10" : ""
                        }`}
                    >
                      {/* Ticker badge */}
                      <div className="w-10 h-10 rounded-full bg-accent/10 border border-accent/20 flex items-center justify-center shrink-0">
                        <span className="text-[10px] font-bold text-accent">
                          {holding.ticker.slice(0, 3)}
                        </span>
                      </div>

                      {/* Name + sector */}
                      <div className="flex-1 min-w-0">
                        <div className="font-semibold text-sm text-foreground">{holding.ticker}</div>
                        <div className="text-xs text-muted-foreground truncate">
                          {holding.name ?? holding.sector ?? "—"}
                        </div>
                      </div>

                      {/* Sparkline */}
                      <Sparkline positive={positive} />

                      {/* Value + gain */}
                      <div className="text-right shrink-0">
                        <div className="font-semibold text-sm text-foreground">
                          ${holding.value.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                        </div>
                        {gainPct !== null ? (
                          <div
                            className={`text-xs font-medium ${gainPct >= 0 ? "text-emerald-400" : "text-rose-400"
                              }`}
                          >
                            {gainPct >= 0 ? "+" : ""}
                            {gainPct.toFixed(2)}%
                          </div>
                        ) : (
                          <div className="text-xs text-muted-foreground">
                            {holding.shares ? `${holding.shares} sh` : ""}
                          </div>
                        )}
                      </div>

                      <ChevronRight
                        className={`w-4 h-4 text-muted-foreground/50 shrink-0 transition-transform duration-200 ${isExpanded ? "rotate-90 text-accent" : ""
                          }`}
                      />
                    </button>

                    {/* ── Expanded action panel ── */}
                    {isExpanded && (
                      <div className="px-4 pb-5 pt-2 bg-muted/10 border-t border-border/30 space-y-4">
                        {/* Action selector */}
                        <div className="grid grid-cols-3 gap-2 mt-1">
                          {(Object.keys(ACTION_CONFIG) as AnalysisAction[]).map((a) => {
                            const cfg = ACTION_CONFIG[a];
                            const Icon = cfg.icon;
                            return (
                              <button
                                key={a}
                                onClick={() => setSelectedAction(a)}
                                className={`flex flex-col items-center gap-1.5 py-3 rounded-xl border font-semibold text-xs transition-all ${selectedAction === a
                                    ? `${cfg.color} ${cfg.border} bg-muted/40 shadow-sm`
                                    : "border-border/50 text-muted-foreground hover:text-foreground"
                                  }`}
                              >
                                <Icon className="w-4 h-4" />
                                {cfg.label}
                              </button>
                            );
                          })}
                        </div>

                        {/* Description */}
                        <p className="text-xs text-muted-foreground text-center">
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
                          className={`w-full py-3.5 rounded-xl font-bold text-sm text-white transition-all active:scale-[0.98] ${ACTION_CONFIG[selectedAction].bg
                            } hover:opacity-90`}
                        >
                          Investigate {holding.ticker} — {ACTION_CONFIG[selectedAction].label} →
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">
              Could not load portfolio.
            </p>
          )}
        </section>

        {/* ── 4-agent legend ───────────────────────────────────────────────────── */}
        {!expandedTicker && !showSearch && (
          <section className="mt-8 rounded-2xl bg-muted/10 border border-border/40 p-4">
            <p className="text-xs text-muted-foreground font-medium mb-3 text-center uppercase tracking-widest">
              4-Agent Debate Engine
            </p>
            <div className="grid grid-cols-4 gap-2 text-center">
              {[
                { e: "🐂", t: "Bull", d: "Upside case" },
                { e: "🐻", t: "Bear", d: "Risk case" },
                { e: "📊", t: "Strategist", d: "Portfolio fit" },
                { e: "⚖️", t: "CIO", d: "Final call" },
              ].map((a) => (
                <div key={a.t}>
                  <div className="text-xl mb-1">{a.e}</div>
                  <div className="text-xs font-semibold text-foreground">{a.t}</div>
                  <div className="text-[10px] text-muted-foreground mt-0.5">{a.d}</div>
                </div>
              ))}
            </div>
          </section>
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
        <label className="text-[10px] text-muted-foreground uppercase tracking-widest mb-1 block">Amount</label>
        <div className="relative">
          <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground text-xs">$</span>
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className="w-full bg-background border border-border rounded-lg pl-6 pr-2 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-accent"
          />
        </div>
      </div>
      <div>
        <label className="text-[10px] text-muted-foreground uppercase tracking-widest mb-1 block">Risk</label>
        <select
          value={riskTolerance}
          onChange={(e) => setRiskTolerance(e.target.value)}
          className="w-full bg-background border border-border rounded-lg px-2 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-accent"
        >
          <option value="conservative">Low</option>
          <option value="moderate">Mid</option>
          <option value="aggressive">High</option>
        </select>
      </div>
      <div>
        <label className="text-[10px] text-muted-foreground uppercase tracking-widest mb-1 block">Horizon</label>
        <select
          value={timeHorizon}
          onChange={(e) => setTimeHorizon(e.target.value)}
          className="w-full bg-background border border-border rounded-lg px-2 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-accent"
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
