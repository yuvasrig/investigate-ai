import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { TrendingUp, AlertTriangle, Target, Loader2 } from "lucide-react";
import { useAnalysis } from "@/context/AnalysisContext";
import { analyze } from "@/services/api";

const agents = [
  { name: "Bull Analyst", desc: "Finding growth potential...", icon: TrendingUp, color: "border-bull", bg: "bg-bull", barBg: "bg-bull" },
  { name: "Bear Analyst", desc: "Assessing risks...", icon: AlertTriangle, color: "border-bear", bg: "bg-bear", barBg: "bg-bear" },
  { name: "Portfolio Strategist", desc: "Analyzing portfolio fit...", icon: Target, color: "border-strategist", bg: "bg-strategist", barBg: "bg-strategist" },
];

const Loading = () => {
  const navigate = useNavigate();
  const { formData, setAnalysisResult } = useAnalysis();
  const [progress, setProgress] = useState([0, 0, 0]);
  const [error, setError] = useState<string | null>(null);
  const calledRef = useRef(false);

  useEffect(() => {
    // Animate progress bars independently of API call
    const intervals: ReturnType<typeof setInterval>[] = [];
    const staggerTimers = agents.map((_, i) =>
      setTimeout(() => {
        const iv = setInterval(() => {
          setProgress((prev) => {
            const next = [...prev];
            next[i] = Math.min(next[i] + Math.random() * 12, 90);
            return next;
          });
        }, 200);
        intervals.push(iv);
      }, i * 600)
    );

    // Guard against React StrictMode double-invoke
    if (calledRef.current) return;
    calledRef.current = true;

    const portfolioValue = parseFloat(formData.portfolio.replace(/,/g, "")) || 0;
    const amount = parseFloat(formData.amount.replace(/,/g, "")) || 0;

    const API_BASE = (import.meta.env.VITE_API_URL as string) || "http://localhost:8000";

    const runAnalysis = async () => {
      // Fetch demo portfolio for hidden-exposure calculation
      const demoPortfolio = await fetch(`${API_BASE}/api/portfolio/demo`)
        .then((r) => r.json())
        .catch(() => null);

      const portfolioHoldings = demoPortfolio?.holdings?.map(
        (h: { ticker: string; value: number; name?: string; shares?: number }) => ({
          ticker: h.ticker,
          value: h.value,
          name: h.name,
          shares: h.shares,
        })
      ) ?? undefined;

      const result = await analyze({
        ticker: formData.ticker,
        amount,
        portfolio: { total_value: portfolioValue },
        risk_tolerance: formData.riskTolerance,
        time_horizon: formData.timeHorizon,
        portfolio_holdings: portfolioHoldings,
      });

      setAnalysisResult(result);
      setProgress([100, 100, 100]);
      setTimeout(() => navigate("/results"), 400);
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
      <h2 className="text-2xl font-bold text-foreground mb-2">Analyzing Investment...</h2>
      <p className="text-muted-foreground text-sm mb-10">Our AI agents are debating your investment</p>

      <div className="flex flex-col sm:flex-row gap-4 w-full max-w-3xl">
        {agents.map((a, i) => (
          <div key={a.name} className={`flex-1 bg-card rounded-lg border-l-4 ${a.color} border border-border p-5 shadow-sm`}>
            <div className="flex items-center gap-2 mb-3">
              <div className={`w-8 h-8 rounded-full ${a.bg} flex items-center justify-center`}>
                <a.icon className="text-white" size={16} />
              </div>
              <span className="text-sm font-semibold text-foreground">{a.name}</span>
            </div>
            <p className="text-xs text-muted-foreground mb-3">{a.desc}</p>
            <div className="h-1.5 w-full rounded-full bg-secondary overflow-hidden">
              <div
                className={`h-full rounded-full ${a.barBg} transition-all duration-300`}
                style={{ width: `${progress[i]}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      <p className="text-xs text-muted-foreground mt-8">~10-15 seconds</p>
    </div>
  );
};

export default Loading;
