import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { TrendingUp, AlertTriangle, Target, Scale, CheckCircle2, Loader2 } from "lucide-react";
import { useAnalysis } from "@/context/AnalysisContext";
import { analyze } from "@/services/api";

// ── Agent definitions ─────────────────────────────────────────────────────────
const analysts = [
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
];

const Loading = () => {
  const navigate = useNavigate();
  const { formData, setAnalysisResult, plaidHoldings, analysisAction } = useAnalysis();

  // [bull, bear, strategist, judge]
  const [progress, setProgress] = useState([0, 0, 0, 0]);
  const [done, setDone] = useState([false, false, false, false]);
  // How many analyst reports the Judge has received
  const [reportsReceived, setReportsReceived] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const calledRef = useRef(false);

  // Judge status text updates live as each analyst finishes
  const judgeDesc = done[3]
    ? "Final recommendation ready"
    : reportsReceived === 3
    ? "Synthesizing final recommendation…"
    : reportsReceived > 0
    ? `Received ${reportsReceived} of 3 analyses…`
    : progress[3] > 0
    ? "Waiting for analyst reports…"
    : "Queued…";

  useEffect(() => {
    // ── Independent progress animations (start regardless of API) ─────────────
    const intervals: ReturnType<typeof setInterval>[] = [];
    const staggerTimers: ReturnType<typeof setTimeout>[] = [];

    const allDelays  = [0, 600, 1200, 2400];
    const caps       = [88, 88, 88, 70];   // bull/bear/strategist cap 88%, judge 70%

    allDelays.forEach((delay, i) => {
      const t = setTimeout(() => {
        const iv = setInterval(() => {
          setProgress((prev) => {
            const next = [...prev];
            next[i] = Math.min(next[i] + Math.random() * (i === 3 ? 5 : 10), caps[i]);
            return next;
          });
        }, 220);
        intervals.push(iv);
      }, delay);
      staggerTimers.push(t);
    });

    // Guard against React StrictMode double-invoke
    if (calledRef.current) return;
    calledRef.current = true;

    const portfolioValue = parseFloat(formData.portfolio.replace(/,/g, "")) || 0;
    const amount         = parseFloat(formData.amount.replace(/,/g, ""))    || 0;
    const API_BASE       = (import.meta.env.VITE_API_URL as string) || "http://localhost:8000";

    const runAnalysis = async () => {
      // Prefer Plaid/voice holdings; fall back to demo portfolio
      let portfolioHoldings = plaidHoldings;
      if (!portfolioHoldings) {
        const demo = await fetch(`${API_BASE}/api/portfolio/demo`)
          .then((r) => r.json())
          .catch(() => null);
        portfolioHoldings =
          demo?.holdings?.map(
            (h: { ticker: string; value: number; name?: string; shares?: number }) => ({
              ticker: h.ticker,
              value:  h.value,
              name:   h.name,
              shares: h.shares,
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
      staggerTimers.forEach(clearTimeout);

      // Snap analysts to 100% one-by-one so the connector "sending" dots are
      // visible before the Judge finishes.
      // Incremental await delays → absolute ms after API returns:
      //   Bull @ 0 ms | Bear @ 500 ms | Strategist @ 1 000 ms | Judge @ 2 500 ms
      const snapDelays = [0, 500, 500, 1500];

      for (let i = 0; i < 4; i++) {
        await new Promise<void>((res) =>
          setTimeout(() => {
            setProgress((prev) => { const n = [...prev]; n[i] = 100; return n; });
            setDone   ((prev) => { const n = [...prev]; n[i] = true; return n; });
            if (i < 3) setReportsReceived((prev) => prev + 1);
            res();
          }, snapDelays[i])
        );
      }

      setAnalysisResult(result);
      setTimeout(() => navigate("/results"), 600);
    };

    runAnalysis().catch((err: unknown) => {
      setError(err instanceof Error ? err.message : String(err));
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
    <>
      {/* Flowing-dot keyframe — dots glide left → right along each connector */}
      <style>{`
        @keyframes flow-right {
          0%   { transform: translateX(0);    opacity: 0; }
          12%  { opacity: 1; }
          88%  { opacity: 1; }
          100% { transform: translateX(46px); opacity: 0; }
        }
      `}</style>

      <div className="min-h-screen bg-background flex flex-col items-center justify-center px-6 animate-fade-in">
        <Loader2 className="text-accent animate-spin mb-6" size={40} />
        <h2 className="text-2xl font-bold text-foreground mb-2">Analyzing Investment…</h2>
        <p className="text-muted-foreground text-sm mb-10">
          4 AI agents are debating your investment in parallel
        </p>

        {/* ── Main layout ────────────────────────────────────────────────────── */}
        {/* Desktop: [Bull / Bear / Strategist] → [animated connectors] → [Judge] */}
        {/* Mobile:  all four cards stacked vertically                            */}
        <div className="flex flex-col lg:flex-row gap-4 w-full max-w-5xl items-stretch">

          {/* ── Left: 3 analyst cards ─────────────────────────────────────── */}
          <div className="flex flex-col gap-3 flex-1 min-w-0">
            {analysts.map((a, i) => (
              <div
                key={a.key}
                className={`bg-card rounded-xl border-l-4 ${a.color} border border-border p-5 shadow-sm transition-all duration-300 ${
                  done[i] ? "opacity-100" : progress[i] === 0 ? "opacity-40" : "opacity-80"
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
                  {done[i] && <CheckCircle2 className="text-bull shrink-0" size={16} />}
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
                <p className="text-right text-[10px] text-muted-foreground mt-1">
                  {Math.round(progress[i])}%
                </p>
              </div>
            ))}
          </div>

          {/* ── Center: animated connectors (desktop only) ─────────────────── */}
          <div className="hidden lg:flex flex-col justify-around items-center w-16 shrink-0">
            {analysts.map((_, i) => (
              <div
                key={i}
                className="relative flex items-center"
                style={{ width: 52, height: 20 }}
              >
                {/* Static line */}
                <div
                  className={`h-px w-full transition-colors duration-500 ${
                    done[i] ? "bg-accent/70" : "bg-border"
                  }`}
                />

                {/* Arrowhead */}
                <span
                  className={`absolute right-0 text-[10px] leading-none select-none transition-colors duration-500 ${
                    done[i] ? "text-accent" : "text-border"
                  }`}
                >
                  ▶
                </span>

                {/* "sending…" label above the arrow */}
                {done[i] && !done[3] && (
                  <span className="absolute -top-4 left-1/2 -translate-x-1/2 text-[8px] font-medium text-accent whitespace-nowrap animate-pulse">
                    sending…
                  </span>
                )}

                {/* Three dots that travel along the wire */}
                {done[i] && !done[3] &&
                  [0, 1, 2].map((d) => (
                    <span
                      key={d}
                      className="absolute rounded-full bg-accent"
                      style={{
                        width: 7,
                        height: 7,
                        top: -3,
                        left: 0,
                        opacity: 0,
                        animation: "flow-right 1.2s ease-in-out infinite",
                        animationDelay: `${d * 0.4}s`,
                      }}
                    />
                  ))}
              </div>
            ))}
          </div>

          {/* ── Right: Judge card ──────────────────────────────────────────── */}
          <div
            className={`bg-card rounded-xl border-l-4 border-accent border border-border p-5 shadow-sm flex flex-col justify-between lg:w-64 shrink-0 transition-all duration-500 ${
              done[3] ? "opacity-100" : progress[3] === 0 ? "opacity-40" : "opacity-80"
            }`}
          >
            {/* Top */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-full bg-accent flex items-center justify-center shrink-0">
                    <Scale className="text-white" size={15} />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-foreground leading-tight">Judge / CIO</p>
                    <p className="text-[10px] text-muted-foreground">Chief Investment Officer</p>
                  </div>
                </div>
                {done[3] && <CheckCircle2 className="text-bull shrink-0" size={16} />}
              </div>

              <p className="text-xs text-muted-foreground mb-3">{judgeDesc}</p>

              {/* 3-segment inbox indicator — fills as each analyst report arrives */}
              {!done[3] && (
                <div className="flex gap-1.5 mb-4">
                  {[0, 1, 2].map((dot) => (
                    <div
                      key={dot}
                      className={`h-1.5 flex-1 rounded-full transition-all duration-500 ${
                        dot < reportsReceived ? "bg-accent" : "bg-secondary"
                      }`}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Bottom: progress bar */}
            <div>
              <div className="h-1.5 w-full rounded-full bg-secondary overflow-hidden">
                <div
                  className="h-full rounded-full bg-accent transition-all duration-300"
                  style={{ width: `${progress[3]}%` }}
                />
              </div>
              <p className="text-right text-[10px] text-muted-foreground mt-1">
                {Math.round(progress[3])}%
              </p>
            </div>
          </div>

        </div>
      </div>
    </>
  );
};

export default Loading;
