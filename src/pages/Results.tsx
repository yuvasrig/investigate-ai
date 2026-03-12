import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { TrendingUp, AlertTriangle, Target, Scale, CheckCircle2, AlertCircle, FileDown, Loader2, Info } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { useAnalysis } from "@/context/AnalysisContext";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell, Tooltip } from "recharts";
import { TrafficLight } from "@/components/TrafficLight";
import { PortfolioExposure, ExposureData } from "@/components/PortfolioExposure";

const API_BASE = (import.meta.env.VITE_API_URL as string) || "http://localhost:8000";

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

// ── Warning banner ────────────────────────────────────────────────────────────
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

const Results = () => {
  const navigate = useNavigate();
  const { analysisResult, formData } = useAnalysis();
  const [exporting, setExporting] = useState(false);

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
    bull_analysis,
    bear_analysis,
    strategist_analysis,
    final_recommendation,
    market_data,
    traffic_light,
    portfolio_exposure,
  } = analysisResult;

  const proposedAmount = formData.amount ? parseFloat(formData.amount.replace(/,/g, "")) : 0;

  const companyName = (market_data as Record<string, unknown>)?.longName as string | undefined;
  const currentPrice = (market_data as Record<string, unknown>)?.currentPrice as number | undefined;

  const breakdownData = Object.entries(final_recommendation.confidence_breakdown).map(([k, v]) => ({
    name: k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
    value: v as number,
  }));

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
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
        {/* Stock header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground">{ticker}</h1>
          <p className="text-muted-foreground">
            {companyName ?? ""}
            {currentPrice != null ? ` · $${currentPrice.toLocaleString()}` : ""}
          </p>
        </div>

        {/* ── ⚠️ Risk / Concentration Warning ─────────────────────────────── */}
        <WarningBanner
          trafficColor={traffic_light?.color}
          concentrationRisk={strategist_analysis.concentration_risk}
        />

        {/* ── Traffic Light ────────────────────────────────────────────────── */}
        {traffic_light && (
          <div className="mb-6">
            <TrafficLight trafficLight={traffic_light} />
          </div>
        )}

        {/* ── Final Recommendation — shown FIRST ──────────────────────────── */}
        <Card className="border-l-4 border-l-accent shadow-sm mb-8">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <Scale className="text-accent" size={20} />
                <h3 className="text-lg font-semibold text-foreground">Final Recommendation</h3>
              </div>
              <span className="text-3xl font-bold text-accent">{final_recommendation.confidence_overall}%</span>
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed mb-6">{final_recommendation.reasoning}</p>

            {/* Metric grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
              {[
                { label: "Action", value: final_recommendation.action.toUpperCase(), accent: true },
                { label: "Amount", value: `$${final_recommendation.recommended_amount.toLocaleString()}` },
                { label: "Entry", value: final_recommendation.entry_strategy },
                { label: "Risk Mgmt", value: final_recommendation.risk_management },
              ].map((m) => (
                <div key={m.label} className="rounded-lg border border-border p-3 text-center">
                  <p className="text-xs text-muted-foreground mb-1">{m.label}</p>
                  <p className={`text-sm font-bold ${m.accent ? "text-bull" : "text-foreground"}`}>{m.value}</p>
                </div>
              ))}
            </div>

            {/* Key Decision Factors */}
            <p className="text-sm font-semibold text-foreground mb-3">Key Decision Factors</p>
            <ol className="space-y-2 mb-6">
              {final_recommendation.key_factors.map((f, i) => (
                <li key={i} className="text-sm text-muted-foreground flex gap-2">
                  <span className="text-accent font-semibold">{i + 1}.</span> {f}
                </li>
              ))}
            </ol>

            {/* Confidence Breakdown */}
            <p className="text-sm font-semibold text-foreground mb-3">Confidence Breakdown</p>
            <div className="space-y-3">
              {breakdownData.map((d) => (
                <div key={d.name}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-muted-foreground">{d.name}</span>
                    <span className="font-medium text-foreground">{d.value}%</span>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-secondary">
                    <div className="h-full rounded-full bg-accent transition-all" style={{ width: `${d.value}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* ── Portfolio Hidden Exposure ──────────────────────────────────────── */}
        {portfolio_exposure && (
          <div className="mb-6">
            <PortfolioExposure
              exposure={portfolio_exposure as ExposureData}
              ticker={ticker}
              proposedAmount={proposedAmount}
            />
          </div>
        )}

        {/* ── Agent Cards with role descriptions ───────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-8">
          {/* Bull */}
          <Card className="border-l-4 border-l-bull shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-full bg-bull flex items-center justify-center">
                    <TrendingUp className="text-white" size={14} />
                  </div>
                  <span className="font-semibold text-foreground">Bull Analyst</span>
                </div>
                <span className="text-xs font-semibold bg-bull/10 text-bull px-2 py-1 rounded-full">
                  {bull_analysis.confidence}/10
                </span>
              </div>
              <AnalystAbout role="bull" />
              <div className="h-1 w-full rounded-full bg-secondary mb-5">
                <div className="h-full rounded-full bg-bull" style={{ width: `${bull_analysis.confidence * 10}%` }} />
              </div>
              <p className="text-xs text-muted-foreground mb-1">Best Case Target</p>
              <p className="text-2xl font-bold text-foreground mb-0.5">
                ${bull_analysis.best_case_target.toLocaleString()}
              </p>
              <p className="text-xs text-muted-foreground mb-5">{bull_analysis.best_case_timeline}</p>
              <p className="text-sm font-semibold text-foreground mb-3">Key Advantages</p>
              <ul className="space-y-2">
                {bull_analysis.competitive_advantages.map((a, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                    <CheckCircle2 className="text-bull shrink-0 mt-0.5" size={14} />
                    {a}
                  </li>
                ))}
              </ul>
              <p className="text-xs font-semibold text-foreground mt-5 mb-2">Growth Catalysts</p>
              <ul className="space-y-1">
                {bull_analysis.growth_catalysts.map((c, i) => (
                  <li key={i} className="text-xs text-muted-foreground">• {c}</li>
                ))}
              </ul>
              {bull_analysis.valuation_justification && (
                <div className="mt-4 p-3 bg-bull/5 rounded-lg">
                  <p className="text-xs font-semibold text-foreground mb-1">Valuation Justification</p>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {bull_analysis.valuation_justification}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Bear */}
          <Card className="border-l-4 border-l-bear shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-full bg-bear flex items-center justify-center">
                    <AlertTriangle className="text-white" size={14} />
                  </div>
                  <span className="font-semibold text-foreground">Bear Analyst</span>
                </div>
                <span className="text-xs font-semibold bg-bear/10 text-bear px-2 py-1 rounded-full">
                  {bear_analysis.confidence}/10
                </span>
              </div>
              <AnalystAbout role="bear" />
              <div className="h-1 w-full rounded-full bg-secondary mb-5">
                <div className="h-full rounded-full bg-bear" style={{ width: `${bear_analysis.confidence * 10}%` }} />
              </div>
              <p className="text-xs text-muted-foreground mb-1">Worst Case Target</p>
              <p className="text-2xl font-bold text-foreground mb-0.5">
                ${bear_analysis.worst_case_target.toLocaleString()}
              </p>
              <p className="text-xs text-muted-foreground mb-5">{bear_analysis.worst_case_timeline}</p>
              <p className="text-sm font-semibold text-foreground mb-3">Key Risks</p>
              <ul className="space-y-2">
                {bear_analysis.competition_threats.map((r, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                    <AlertCircle className="text-bear shrink-0 mt-0.5" size={14} />
                    {r}
                  </li>
                ))}
              </ul>
              <div className="mt-5 p-3 bg-secondary rounded-lg">
                <p className="text-xs font-semibold text-foreground mb-1">Valuation Concerns</p>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {bear_analysis.valuation_concerns}
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Strategist */}
          <Card className="border-l-4 border-l-strategist shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center gap-2 mb-1">
                <div className="w-7 h-7 rounded-full bg-strategist flex items-center justify-center">
                  <Target className="text-white" size={14} />
                </div>
                <span className="font-semibold text-foreground">Portfolio Strategist</span>
              </div>
              <AnalystAbout role="strategist" />
              <p className="text-xs text-muted-foreground mb-1">Current Exposure</p>
              <p className="text-xl font-bold text-foreground mb-3">{strategist_analysis.current_exposure}</p>
              <div className="flex items-center gap-2 mb-5">
                <span className="text-xs text-muted-foreground">Concentration Risk:</span>
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${riskColor[strategist_analysis.concentration_risk] ?? "text-muted-foreground bg-secondary"}`}>
                  {strategist_analysis.concentration_risk}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mb-1">Recommended Allocation</p>
              <p className="text-2xl font-bold text-foreground mb-1">
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
            </CardContent>
          </Card>
        </div>

        {/* ── Confidence Chart ─────────────────────────────────────────────── */}
        <Card className="shadow-sm mb-12">
          <CardContent className="p-6">
            <h3 className="text-lg font-semibold text-foreground mb-1">Confidence Analysis</h3>
            <p className="text-sm text-muted-foreground mb-6">AI confidence scores across key dimensions</p>
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
      </main>
    </div>
  );
};

export default Results;
