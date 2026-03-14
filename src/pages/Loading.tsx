import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  TrendingUp, AlertTriangle, Target, Scale, CheckCircle2,
  FileText, Newspaper, BookOpen, Database,
} from "lucide-react";
import { useAnalysis } from "@/context/AnalysisContext";
import { analyze } from "@/services/api";

// ── Pipeline stages ────────────────────────────────────────────────────────
const PIPELINE = [
  { label: "Market Data",     sub: "yfinance · options chain" },
  { label: "RAG & Grounding", sub: "SEC 10-K · news corpus"   },
  { label: "Agent Analysis",  sub: "3 parallel analysts"       },
  { label: "Judge Synthesis", sub: "CIO arbitration"           },
];

// ── Analyst sub-step labels ────────────────────────────────────────────────
const STEPS: Record<string, string[]> = {
  bull: [
    "Scanning SEC growth signals…",
    "Building revenue projections…",
    "Stress-testing bull thesis…",
    "Setting price targets…",
    "Finalizing upside case…",
  ],
  bear: [
    "Reviewing risk factors…",
    "Stress-testing financials…",
    "Modeling downside scenarios…",
    "Evaluating competitive threats…",
    "Finalizing bear thesis…",
  ],
  strategist: [
    "Analyzing portfolio concentration…",
    "Checking ETF overlap…",
    "Assessing sizing constraints…",
    "Mapping historical analogs…",
    "Finalizing allocation strategy…",
  ],
};

// How long (ms) each step lasts before advancing to the next
const STEP_DURATIONS: number[][] = [
  [5000, 9000, 11000, 10000, 99999], // bull
  [4500, 8500, 10500,  9500, 99999], // bear
  [6000, 9500, 12000, 10500, 99999], // strategist
];

// ── Analyst card config ────────────────────────────────────────────────────
const ANALYSTS = [
  {
    key: "bull", name: "Bull Analyst", tagline: "Senior Equity Analyst",
    icon: TrendingUp, border: "border-bull", bg: "bg-bull", bar: "bg-bull",
    doneDesc: "Upside thesis complete", startDelay: 0,
  },
  {
    key: "bear", name: "Bear Analyst", tagline: "Veteran Short Seller",
    icon: AlertTriangle, border: "border-bear", bg: "bg-bear", bar: "bg-bear",
    doneDesc: "Bear thesis complete", startDelay: 900,
  },
  {
    key: "strategist", name: "Portfolio Strategist", tagline: "Head of Portfolio Construction",
    icon: Target, border: "border-strategist", bg: "bg-strategist", bar: "bg-strategist",
    doneDesc: "Portfolio analysis complete", startDelay: 1800,
  },
];

// ── RAG data sources (staggered reveal) ──────────────────────────────────
const RAG_ITEMS = [
  { icon: FileText,  label: "SEC 10-K filing",    pending: "fetching…",          ready: "loaded · 2024 filing",   delay: 900  },
  { icon: Newspaper, label: "News corpus",         pending: "indexing…",          ready: "847 articles indexed",   delay: 5500 },
  { icon: BookOpen,  label: "Historical analogs",  pending: "loading…",           ready: "20 precedents ready",    delay: 10500 },
  { icon: Database,  label: "RAG vector store",    pending: "building context…",  ready: "context ready",          delay: 15500 },
];

// ── Easing: exponential approach to cap ───────────────────────────────────
// p(t) = cap × (1 − e^(−t/τ))   τ = time constant in seconds
function easedPct(startMs: number, tau: number, cap: number): number {
  const t = (Date.now() - startMs) / 1000;
  return cap * (1 - Math.exp(-t / tau));
}

const TAU  = [30, 34, 28, 22];  // time constants: bull, bear, strategist, judge
const CAPS = [93, 91, 93, 76];  // max before API returns

// ── Component ─────────────────────────────────────────────────────────────
const Loading = () => {
  const navigate = useNavigate();
  const { formData, setAnalysisResult, plaidHoldings, analysisAction } = useAnalysis();

  const [progress,         setProgress]         = useState([0, 0, 0, 0]);
  const [done,             setDone]             = useState([false, false, false, false]);
  const [stepIdx,          setStepIdx]          = useState([0, 0, 0]);
  const [pipelineStage,    setPipelineStage]    = useState(0);
  const [reportsReceived,  setReportsReceived]  = useState(0);
  const [ragDone,          setRagDone]          = useState([false, false, false, false]);
  const [error,            setError]            = useState<string | null>(null);

  const calledRef  = useRef(false);
  const startTimes = useRef<number[]>([0, 0, 0, 0]);

  const ticker = formData?.ticker?.toUpperCase() ?? "…";

  const judgeLabel =
    done[3]              ? "Final recommendation ready" :
    reportsReceived === 3 ? "Synthesizing final recommendation…" :
    reportsReceived > 0   ? `Received ${reportsReceived}/3 analyst reports…` :
    progress[3] > 0       ? "Awaiting analyst reports…" :
                            "Queued…";

  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[]   = [];
    const intervals: ReturnType<typeof setInterval>[] = [];

    // ── Pipeline stage transitions ─────────────────────────────────────────
    timers.push(setTimeout(() => setPipelineStage(1), 2500));
    timers.push(setTimeout(() => setPipelineStage(2), 17000));
    // Stage 3 fires on API return below

    // ── RAG item reveals ──────────────────────────────────────────────────
    RAG_ITEMS.forEach((item, i) => {
      timers.push(setTimeout(() =>
        setRagDone(prev => { const n = [...prev]; n[i] = true; return n; }),
        item.delay
      ));
    });

    // ── Analyst step progression ──────────────────────────────────────────
    ANALYSTS.forEach((analyst, ai) => {
      let cum = analyst.startDelay;
      STEP_DURATIONS[ai].forEach((dur, si) => {
        const capSi = si;
        const capAi = ai;
        timers.push(setTimeout(() =>
          setStepIdx(prev => { const n = [...prev]; n[capAi] = capSi; return n; }),
          cum
        ));
        cum += dur;
      });
    });

    // ── Smooth eased progress per agent ──────────────────────────────────
    ANALYSTS.forEach((analyst, ai) => {
      timers.push(setTimeout(() => {
        startTimes.current[ai] = Date.now();
        const iv = setInterval(() =>
          setProgress(prev => {
            const n = [...prev];
            n[ai] = easedPct(startTimes.current[ai], TAU[ai], CAPS[ai]);
            return n;
          }), 180
        );
        intervals.push(iv);
      }, analyst.startDelay));
    });

    // Judge ticks slowly (waiting for reports)
    timers.push(setTimeout(() => {
      startTimes.current[3] = Date.now();
      const iv = setInterval(() =>
        setProgress(prev => {
          const n = [...prev];
          n[3] = easedPct(startTimes.current[3], TAU[3], CAPS[3]);
          return n;
        }), 180
      );
      intervals.push(iv);
    }, 4000));

    // ── API call ──────────────────────────────────────────────────────────
    if (calledRef.current) return;
    calledRef.current = true;

    const portfolioValue = parseFloat(formData.portfolio.replace(/,/g, "")) || 0;
    const amount         = parseFloat(formData.amount.replace(/,/g, ""))    || 0;
    const API_BASE       = (import.meta.env.VITE_API_URL as string) || "http://localhost:8000";

    const runAnalysis = async () => {
      let portfolioHoldings = plaidHoldings;
      if (!portfolioHoldings) {
        const demo = await fetch(`${API_BASE}/api/portfolio/demo`).then(r => r.json()).catch(() => null);
        portfolioHoldings = demo?.holdings?.map(
          (h: { ticker: string; value: number; name?: string; shares?: number }) => ({
            ticker: h.ticker, value: h.value, name: h.name, shares: h.shares,
          })
        ) ?? null;
      }

      const result = await analyze({
        ticker:             formData.ticker,
        amount,
        portfolio:          { total_value: portfolioValue },
        risk_tolerance:     formData.riskTolerance,
        time_horizon:       formData.timeHorizon,
        user_query:         formData.userQuery || undefined,
        analysis_action:    analysisAction,
        portfolio_holdings: portfolioHoldings ?? undefined,
      });

      // Stop all crawl animations
      intervals.forEach(clearInterval);
      timers.forEach(clearTimeout);

      // Advance to Judge Synthesis stage
      setPipelineStage(3);
      // Ensure all RAG items show done
      setRagDone([true, true, true, true]);

      // Snap analysts complete one-by-one, then Judge
      const snapDelays = [0, 400, 800, 2200];
      for (let i = 0; i < 4; i++) {
        await new Promise<void>(res => setTimeout(() => {
          setProgress(prev => { const n = [...prev]; n[i] = 100; return n; });
          setDone(prev    => { const n = [...prev]; n[i] = true; return n; });
          if (i < 3) setReportsReceived(prev => prev + 1);
          res();
        }, snapDelays[i]));
      }

      setAnalysisResult(result);
      setTimeout(() => navigate("/results"), 700);
    };

    runAnalysis().catch((err: unknown) => {
      setError(err instanceof Error ? err.message : String(err));
      intervals.forEach(clearInterval);
      timers.forEach(clearTimeout);
    });

    return () => {
      intervals.forEach(clearInterval);
      timers.forEach(clearTimeout);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Error state ───────────────────────────────────────────────────────────
  if (error) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center px-6 gap-4">
        <p className="text-bear font-semibold text-lg">Analysis failed</p>
        <p className="text-muted-foreground text-sm max-w-md text-center">{error}</p>
        <button
          onClick={() => navigate("/")}
          className="mt-4 text-sm font-medium text-accent hover:text-accent/80 transition-colors"
        >
          ← Try again
        </button>
      </div>
    );
  }

  // ── Main render ────────────────────────────────────────────────────────────
  return (
    <>
      <style>{`
        @keyframes flow-right {
          0%   { transform: translateX(0);    opacity: 0; }
          12%  { opacity: 1; }
          88%  { opacity: 1; }
          100% { transform: translateX(42px); opacity: 0; }
        }
        @keyframes rag-appear {
          from { opacity: 0; transform: translateY(4px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      <div className="min-h-screen bg-background flex flex-col items-center justify-center px-6 py-12 animate-fade-in">

        {/* ── Header ──────────────────────────────────────────────────────── */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 text-xs font-medium text-muted-foreground bg-secondary/60 px-3 py-1.5 rounded-full mb-5">
            <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
            InvestiGate AI · Equity Research
          </div>
          <h2 className="text-3xl font-bold text-foreground mb-1.5">
            Analyzing <span className="text-accent">{ticker}</span>
          </h2>
          <p className="text-muted-foreground text-sm">
            4 AI agents researching in parallel · typically 60–90 seconds
          </p>
        </div>

        {/* ── Pipeline progress strip ──────────────────────────────────────── */}
        <div className="flex items-center w-full max-w-2xl mb-8">
          {PIPELINE.map((stage, i) => {
            const isActive = pipelineStage === i;
            const isDone   = pipelineStage > i;
            return (
              <div key={i} className="flex items-center flex-1 min-w-0">
                <div className="flex flex-col items-center gap-1.5 flex-1 px-1">
                  {/* Circle */}
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0 transition-all duration-500 ${
                    isDone   ? "bg-accent text-white shadow-sm shadow-accent/30" :
                    isActive ? "bg-card border-2 border-accent text-accent ring-4 ring-accent/10" :
                               "bg-secondary text-muted-foreground"
                  }`}>
                    {isDone ? <CheckCircle2 size={14} /> : <span>{i + 1}</span>}
                  </div>
                  {/* Labels */}
                  <p className={`text-[10px] font-semibold text-center leading-tight transition-colors duration-300 ${
                    isDone || isActive ? "text-foreground" : "text-muted-foreground"
                  }`}>
                    {stage.label}
                  </p>
                  <p className="text-[9px] text-muted-foreground/70 text-center leading-tight hidden sm:block">
                    {stage.sub}
                  </p>
                </div>
                {/* Connector line */}
                {i < PIPELINE.length - 1 && (
                  <div className={`h-px w-6 sm:w-8 shrink-0 transition-all duration-700 ${
                    pipelineStage > i ? "bg-accent" : "bg-border"
                  }`} />
                )}
              </div>
            );
          })}
        </div>

        {/* ── RAG data sources strip ────────────────────────────────────────── */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 w-full max-w-2xl mb-8">
          {RAG_ITEMS.map((item, i) => {
            const Icon    = item.icon;
            const isReady = ragDone[i];
            return (
              <div
                key={i}
                className={`flex items-start gap-2.5 px-3 py-2.5 rounded-lg border transition-all duration-600 ${
                  isReady
                    ? "bg-accent/5 border-accent/25"
                    : "bg-secondary/30 border-border"
                }`}
                style={isReady ? { animation: "rag-appear 0.4s ease-out" } : {}}
              >
                <Icon
                  size={13}
                  className={`mt-0.5 shrink-0 ${isReady ? "text-accent" : "text-muted-foreground/40"}`}
                />
                <div className="min-w-0">
                  <p className={`text-[10px] font-semibold truncate ${isReady ? "text-foreground" : "text-muted-foreground/60"}`}>
                    {item.label}
                  </p>
                  <p className={`text-[9px] truncate ${isReady ? "text-accent" : "text-muted-foreground/40"}`}>
                    {isReady ? item.ready : item.pending}
                  </p>
                </div>
              </div>
            );
          })}
        </div>

        {/* ── Agent layout ──────────────────────────────────────────────────── */}
        <div className="flex flex-col lg:flex-row gap-4 w-full max-w-4xl items-stretch">

          {/* ── Left: 3 analyst cards ──────────────────────────────────────── */}
          <div className="flex flex-col gap-3 flex-1 min-w-0">
            {ANALYSTS.map((a, i) => {
              const steps      = STEPS[a.key];
              const curStep    = stepIdx[i];
              const statusText = done[i]
                ? a.doneDesc
                : progress[i] === 0
                ? "Queued…"
                : steps[curStep] ?? steps[steps.length - 1];

              return (
                <div
                  key={a.key}
                  className={`bg-card rounded-xl border-l-4 ${a.border} border border-border p-5 shadow-sm transition-all duration-500 ${
                    done[i]         ? "opacity-100" :
                    progress[i] > 0 ? "opacity-90"  :
                                      "opacity-35"
                  }`}
                >
                  {/* Header */}
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2.5">
                      <div className={`w-8 h-8 rounded-full ${a.bg} flex items-center justify-center shrink-0`}>
                        <a.icon className="text-white" size={15} />
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-foreground leading-tight">{a.name}</p>
                        <p className="text-[10px] text-muted-foreground">{a.tagline}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {!done[i] && progress[i] > 0 && (
                        <span className="text-[10px] text-muted-foreground tabular-nums">
                          {curStep + 1}/{steps.length}
                        </span>
                      )}
                      {done[i] && <CheckCircle2 className="text-bull" size={16} />}
                    </div>
                  </div>

                  {/* Status label */}
                  <p className="text-xs text-muted-foreground mb-3 min-h-[1rem] transition-all duration-400">
                    {statusText}
                  </p>

                  {/* Progress bar */}
                  <div className="h-1.5 w-full rounded-full bg-secondary overflow-hidden mb-2">
                    <div
                      className={`h-full rounded-full ${a.bar} transition-all duration-500`}
                      style={{ width: `${progress[i]}%` }}
                    />
                  </div>

                  {/* Step dots + percentage */}
                  <div className="flex items-center justify-between">
                    <div className="flex gap-1">
                      {steps.map((_, si) => (
                        <div
                          key={si}
                          className={`h-1 rounded-full transition-all duration-400 ${
                            done[i]
                              ? "w-5 bg-bull/50"
                              : si <= curStep && progress[i] > 0
                              ? `w-5 ${a.bar}`
                              : "w-3 bg-border"
                          }`}
                        />
                      ))}
                    </div>
                    <p className="text-[10px] text-muted-foreground tabular-nums">
                      {Math.round(progress[i])}%
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          {/* ── Center: animated connectors (desktop only) ────────────────── */}
          <div className="hidden lg:flex flex-col justify-around items-center w-14 shrink-0">
            {ANALYSTS.map((_, i) => (
              <div key={i} className="relative flex items-center" style={{ width: 46, height: 20 }}>
                {/* Line */}
                <div className={`h-px w-full transition-colors duration-500 ${done[i] ? "bg-accent/70" : "bg-border"}`} />
                {/* Arrow */}
                <span className={`absolute right-0 text-[10px] leading-none select-none transition-colors duration-500 ${done[i] ? "text-accent" : "text-border"}`}>
                  ▶
                </span>
                {/* "sending…" pulse */}
                {done[i] && !done[3] && (
                  <span className="absolute -top-4 left-1/2 -translate-x-1/2 text-[8px] font-medium text-accent whitespace-nowrap animate-pulse">
                    sending…
                  </span>
                )}
                {/* Traveling dots */}
                {done[i] && !done[3] &&
                  [0, 1, 2].map(d => (
                    <span
                      key={d}
                      className="absolute rounded-full bg-accent"
                      style={{
                        width: 6, height: 6, top: -2, left: 0, opacity: 0,
                        animation: "flow-right 1.2s ease-in-out infinite",
                        animationDelay: `${d * 0.4}s`,
                      }}
                    />
                  ))
                }
              </div>
            ))}
          </div>

          {/* ── Right: Judge / CIO card ────────────────────────────────────── */}
          <div className={`bg-card rounded-xl border-l-4 border-accent border border-border p-5 shadow-sm flex flex-col lg:w-64 shrink-0 transition-all duration-500 ${
            done[3]         ? "opacity-100" :
            progress[3] > 0 ? "opacity-90"  :
                              "opacity-35"
          }`}>
            {/* Header */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center shrink-0">
                  <Scale className="text-white" size={15} />
                </div>
                <div>
                  <p className="text-sm font-semibold text-foreground leading-tight">Judge / CIO</p>
                  <p className="text-[10px] text-muted-foreground">Chief Investment Officer</p>
                </div>
              </div>
              {done[3] && <CheckCircle2 className="text-bull" size={16} />}
            </div>

            {/* Status */}
            <p className="text-xs text-muted-foreground mb-4 min-h-[1rem]">{judgeLabel}</p>

            {/* Analyst report inbox (list with per-analyst status) */}
            {!done[3] && (
              <div className="space-y-2 mb-5">
                {ANALYSTS.map((a, i) => {
                  const sent     = reportsReceived > i;
                  const pending  = done[i] && !sent;
                  return (
                    <div key={a.key} className="flex items-center gap-2.5">
                      <div className={`w-2 h-2 rounded-full shrink-0 transition-all duration-500 ${
                        sent    ? "bg-bull" :
                        pending ? "bg-accent animate-pulse" :
                                  "bg-border"
                      }`} />
                      <p className={`text-[10px] flex-1 transition-colors duration-300 ${
                        sent || pending ? "text-foreground" : "text-muted-foreground/50"
                      }`}>
                        {a.name}
                      </p>
                      {sent && (
                        <span className="text-[9px] font-medium text-bull">✓ received</span>
                      )}
                      {pending && (
                        <span className="text-[9px] text-accent animate-pulse">transmitting…</span>
                      )}
                    </div>
                  );
                })}
              </div>
            )}

            {/* Progress bar */}
            <div className="mt-auto">
              <div className="h-1.5 w-full rounded-full bg-secondary overflow-hidden mb-1">
                <div
                  className="h-full rounded-full bg-accent transition-all duration-500"
                  style={{ width: `${progress[3]}%` }}
                />
              </div>
              <p className="text-right text-[10px] text-muted-foreground tabular-nums">
                {Math.round(progress[3])}%
              </p>
            </div>
          </div>

        </div>

        {/* ── Footer attribution ────────────────────────────────────────────── */}
        <p className="text-[10px] text-muted-foreground/40 mt-10 text-center">
          LangGraph multi-agent workflow · ChromaDB vector store · SEC EDGAR public API
        </p>

      </div>
    </>
  );
};

export default Loading;
