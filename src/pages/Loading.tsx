import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { TrendingUp, AlertTriangle, Target, Scale, CheckCircle2, Loader2 } from "lucide-react";
import { useAnalysis } from "@/context/AnalysisContext";
import { analyze } from "@/services/api";

// ── 4-agent definitions (matches v3 spec) ─────────────────────────────────────
const agents = [
  {
    key: "bull",
    name: "Bull Analyst",
    tagline: "Senior Equity Analyst",
    desc: "Building the strongest upside case…",
    doneDesc: "Upside thesis complete",
    icon: TrendingUp,
    color: "border-bull",
    bg: "bg-bull",
    barBg: "bg-bull",
    startDelay: 0,
  },
  {
    key: "bear",
    name: "Bear Analyst",
    tagline: "Veteran Short Seller",
    desc: "Stress-testing risks & downside…",
    doneDesc: "Bear thesis complete",
    icon: AlertTriangle,
    color: "border-bear",
    bg: "bg-bear",
    barBg: "bg-bear",
    startDelay: 600,
  },
  {
    key: "strategist",
    name: "Portfolio Strategist",
    tagline: "Head of Portfolio Construction",
    desc: "Analyzing concentration & ETF exposure…",
    doneDesc: "Portfolio analysis complete",
    icon: Target,
    color: "border-strategist",
    bg: "bg-strategist",
    barBg: "bg-strategist",
    startDelay: 1200,
  },
  {
    key: "judge",
    name: "Judge / CIO",
    tagline: "Chief Investment Officer",
    desc: "Waiting for analysts to finish…",
    doneDesc: "Final recommendation ready",
    icon: Scale,
    color: "border-accent",
    bg: "bg-accent",
    barBg: "bg-accent",
    startDelay: 2400,
  },
];

const Loading = () => {
  const navigate = useNavigate();
  const { formData, setAnalysisResult, plaidHoldings, analysisAction } = useAnalysis();
  // Per-agent progress 0-100
  const [progress, setProgress] = useState([0, 0, 0, 0]);
  // Which agents are "done" (progress snapped to 100)
  const [done, setDone] = useState([false, false, false, false]);
  const [error, setError] = useState<string | null>(null);
  const calledRef = useRef(false);

  useEffect(() => {
    // ── Animate progress bars independently of API ────────────────────────────
    const intervals: ReturnType<typeof setInterval>[] = [];
    const staggerTimers: ReturnType<typeof setTimeout>[] = [];

    agents.forEach((a, i) => {
      const t = setTimeout(() => {
        const iv = setInterval(() => {
          setProgress((prev) => {
            const next = [...prev];
            // Bull/Bear/Strategist crawl to 88%; Judge to 70% (waits for others)
            const cap = i === 3 ? 70 : 88;
            next[i] = Math.min(next[i] + Math.random() * (i === 3 ? 6 : 11), cap);
            return next;
          });
        }, 220);
        intervals.push(iv);
      }, a.startDelay);
      staggerTimers.push(t);
    });

    // Guard against React StrictMode double-invoke
    if (calledRef.current) return;
    calledRef.current = true;

    const portfolioValue = parseFloat(formData.portfolio.replace(/,/g, "")) || 0;
    const amount = parseFloat(formData.amount.replace(/,/g, "")) || 0;
    const API_BASE = (import.meta.env.VITE_API_URL as string) || "http://localhost:8000";

    const runAnalysis = async () => {
      // ── Prefer Plaid/voice holdings from context; only fetch demo as last resort
      let portfolioHoldings = plaidHoldings;
      if (!portfolioHoldings) {
        const demoPortfolio = await fetch(`${API_BASE}/api/portfolio/demo`)
          .then((r) => r.json())
          .catch(() => null);
        portfolioHoldings = demoPortfolio?.holdings?.map(
          (h: { ticker: string; value: number; name?: string; shares?: number }) => ({
            ticker: h.ticker,
            value: h.value,
            name: h.name,
            shares: h.shares,
          })
        ) ?? null;
      }

      const result = await analyze({
        ticker: formData.ticker,
        amount,
        portfolio: { total_value: portfolioValue },
        risk_tolerance: formData.riskTolerance,
        time_horizon: formData.timeHorizon,
        user_query: formData.userQuery || undefined,
        analysis_action: analysisAction,
        portfolio_holdings: portfolioHoldings ?? undefined,
      });

      // Snap all bars to 100% in staggered order then navigate
      intervals.forEach(clearInterval);
      staggerTimers.forEach(clearTimeout);

      for (let i = 0; i < 4; i++) {
        await new Promise<void>((res) =>
          setTimeout(() => {
            setProgress((prev) => {
              const next = [...prev];
              next[i] = 100;
              return next;
            });
            setDone((prev) => {
              const next = [...prev];
              next[i] = true;
              return next;
            });
            res();
          }, i * 300)
        );
      }

      setAnalysisResult(result);
      setTimeout(() => navigate("/results"), 600);
    };

    runAnalysis().catch((err: unknown) => {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      intervals.forEach(clearInterval);
      staggerTimers.forEach(clearTimeout);
    });

    return () => {
      intervals.forEach(clearInterval);
      staggerTimers.forEach(clearTimeout);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center px-6 animate-fade-in">
      <Loader2 className="text-accent animate-spin mb-6" size={40} />
      <h2 className="text-2xl font-bold text-foreground mb-2">Analyzing Investment…</h2>
      <p className="text-muted-foreground text-sm mb-10">
        4 AI agents are debating your investment in parallel
      </p>

      {/* ── Agent progress cards ────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 w-full max-w-5xl">
        {agents.map((a, i) => (
          <div
            key={a.key}
            className={`bg-card rounded-xl border-l-4 ${a.color} border border-border p-5 shadow-sm transition-all duration-300 ${done[i] ? "opacity-100" : progress[i] === 0 ? "opacity-40" : "opacity-80"
              }`}
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <div className={`w-8 h-8 rounded-full ${a.bg} flex items-center justify-center shrink-0`}>
                  <a.icon className="text-white" size={15} />
                </div>
                <div>
                  <p className="text-sm font-semibold text-foreground leading-tight">{a.name}</p>
                  <p className="text-[10px] text-muted-foreground">{a.tagline}</p>
                </div>
              </div>
              {done[i] && (
                <CheckCircle2 className="text-bull shrink-0" size={16} />
              )}
            </div>

            {/* Status */}
            <p className="text-xs text-muted-foreground mb-3">
              {done[i] ? a.doneDesc : progress[i] > 0 ? a.desc : "Queued…"}
            </p>

            {/* Progress bar */}
            <div className="h-1.5 w-full rounded-full bg-secondary overflow-hidden">
              <div
                className={`h-full rounded-full ${a.barBg} transition-all duration-300`}
                style={{ width: `${progress[i]}%` }}
              />
            </div>

            {/* Percentage */}
            <p className="text-right text-[10px] text-muted-foreground mt-1">
              {Math.round(progress[i])}%
            </p>
          </div>
        ))}
      </div>

      <p className="text-xs text-muted-foreground mt-8">~45–90 seconds with local Ollama</p>
    </div>
  );
};

export default Loading;
