import { useNavigate } from "react-router-dom";
import { TrendingUp, AlertTriangle, Target, Scale, CheckCircle2, AlertCircle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { mockResults as data } from "@/lib/mockData";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell, Tooltip } from "recharts";

const Results = () => {
  const navigate = useNavigate();

  const confidenceData = Object.entries(data.confidence).map(([key, val]) => ({
    name: key.replace(/([A-Z])/g, " $1").trim(),
    value: val,
  }));

  const breakdownData = Object.entries(data.recommendation.confidenceBreakdown).map(([k, v]) => ({
    name: k,
    value: v,
  }));

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="container mx-auto flex items-center justify-between px-6 py-4">
          <div>
            <h2 className="text-xl font-bold text-primary tracking-tight">InvestiGate</h2>
          </div>
          <button onClick={() => navigate("/")} className="text-sm font-medium text-accent hover:text-accent/80 transition-colors">
            ← New Analysis
          </button>
        </div>
      </header>

      <main className="container mx-auto max-w-6xl px-6 py-8 animate-fade-in">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground">{data.ticker}</h1>
          <p className="text-muted-foreground">{data.companyName} · ${data.currentPrice}</p>
        </div>

        {/* Agent Cards */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-8">
          {/* Bull */}
          <Card className="border-l-4 border-l-bull shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-full bg-bull flex items-center justify-center">
                    <TrendingUp className="text-white" size={14} />
                  </div>
                  <span className="font-semibold text-foreground">Bull Analyst</span>
                </div>
                <span className="text-xs font-semibold bg-bull/10 text-bull px-2 py-1 rounded-full">{data.bull.score}/10</span>
              </div>
              <div className="h-1 w-full rounded-full bg-secondary mb-5">
                <div className="h-full rounded-full bg-bull" style={{ width: `${data.bull.score * 10}%` }} />
              </div>
              <p className="text-xs text-muted-foreground mb-1">Best Case Target</p>
              <p className="text-2xl font-bold text-foreground mb-0.5">${data.bull.bestCaseTarget.toLocaleString()}</p>
              <p className="text-xs text-muted-foreground mb-5">{data.bull.timeframe}</p>
              <p className="text-sm font-semibold text-foreground mb-3">Key Advantages</p>
              <ul className="space-y-2">
                {data.bull.advantages.map((a, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                    <CheckCircle2 className="text-bull shrink-0 mt-0.5" size={14} />
                    {a}
                  </li>
                ))}
              </ul>
              <p className="text-xs font-semibold text-foreground mt-5 mb-2">Growth Catalysts</p>
              <ul className="space-y-1">
                {data.bull.catalysts.map((c, i) => (
                  <li key={i} className="text-xs text-muted-foreground">• {c}</li>
                ))}
              </ul>
            </CardContent>
          </Card>

          {/* Bear */}
          <Card className="border-l-4 border-l-bear shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-full bg-bear flex items-center justify-center">
                    <AlertTriangle className="text-white" size={14} />
                  </div>
                  <span className="font-semibold text-foreground">Bear Analyst</span>
                </div>
                <span className="text-xs font-semibold bg-bear/10 text-bear px-2 py-1 rounded-full">{data.bear.score}/10</span>
              </div>
              <div className="h-1 w-full rounded-full bg-secondary mb-5">
                <div className="h-full rounded-full bg-bear" style={{ width: `${data.bear.score * 10}%` }} />
              </div>
              <p className="text-xs text-muted-foreground mb-1">Worst Case Target</p>
              <p className="text-2xl font-bold text-foreground mb-0.5">${data.bear.worstCaseTarget.toLocaleString()}</p>
              <p className="text-xs text-muted-foreground mb-5">{data.bear.timeframe}</p>
              <p className="text-sm font-semibold text-foreground mb-3">Key Risks</p>
              <ul className="space-y-2">
                {data.bear.risks.map((r, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                    <AlertCircle className="text-bear shrink-0 mt-0.5" size={14} />
                    {r}
                  </li>
                ))}
              </ul>
              <div className="mt-5 p-3 bg-secondary rounded-lg">
                <p className="text-xs font-semibold text-foreground mb-1">Valuation Concerns</p>
                <p className="text-xs text-muted-foreground leading-relaxed">{data.bear.valuationConcerns}</p>
              </div>
            </CardContent>
          </Card>

          {/* Strategist */}
          <Card className="border-l-4 border-l-strategist shadow-sm">
            <CardContent className="p-6">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-7 h-7 rounded-full bg-strategist flex items-center justify-center">
                  <Target className="text-white" size={14} />
                </div>
                <span className="font-semibold text-foreground">Portfolio Strategist</span>
              </div>
              <p className="text-xs text-muted-foreground mb-1">Current Exposure</p>
              <p className="text-xl font-bold text-foreground mb-3">{data.strategist.currentExposure}</p>
              <div className="flex items-center gap-2 mb-5">
                <span className="text-xs text-muted-foreground">Concentration Risk:</span>
                <span className="text-xs font-semibold bg-bear/10 text-bear px-2 py-0.5 rounded-full">{data.strategist.concentrationRisk}</span>
              </div>
              <p className="text-xs text-muted-foreground mb-1">Recommended Allocation</p>
              <p className="text-2xl font-bold text-foreground mb-1">${data.strategist.recommendedAllocation.toLocaleString()}</p>
              <p className="text-xs text-muted-foreground mb-5">Max: {data.strategist.maxAllocation} of portfolio</p>
              <p className="text-sm text-muted-foreground leading-relaxed">{data.strategist.reasoning}</p>
            </CardContent>
          </Card>
        </div>

        {/* Confidence Chart */}
        <Card className="shadow-sm mb-8">
          <CardContent className="p-6">
            <h3 className="text-lg font-semibold text-foreground mb-1">Confidence Analysis</h3>
            <p className="text-sm text-muted-foreground mb-6">AI confidence scores across key dimensions</p>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={confidenceData} layout="vertical" margin={{ left: 20 }}>
                  <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 12, fill: "hsl(220 9% 46%)" }} />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 12, fill: "hsl(220 13% 13%)" }} width={120} />
                  <Tooltip
                    contentStyle={{ borderRadius: 8, border: "1px solid hsl(220 13% 91%)", boxShadow: "0 1px 3px rgba(0,0,0,0.08)" }}
                  />
                  <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={20}>
                    {confidenceData.map((_, i) => (
                      <Cell key={i} fill={`hsl(239 84% ${67 - i * 5}%)`} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Final Recommendation */}
        <Card className="border-l-4 border-l-accent shadow-sm mb-12">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <Scale className="text-accent" size={20} />
                <h3 className="text-lg font-semibold text-foreground">Final Recommendation</h3>
              </div>
              <span className="text-3xl font-bold text-accent">{data.recommendation.overallConfidence}%</span>
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed mb-6">{data.recommendation.reasoning}</p>

            {/* Metric grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
              {[
                { label: "Action", value: data.recommendation.action, accent: true },
                { label: "Amount", value: data.recommendation.amount },
                { label: "Entry", value: data.recommendation.entry },
                { label: "Risk", value: data.recommendation.risk },
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
              {data.recommendation.factors.map((f, i) => (
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
      </main>
    </div>
  );
};

export default Results;
