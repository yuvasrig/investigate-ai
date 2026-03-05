import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { TrendingUp, AlertTriangle, Target } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAnalysis } from "@/context/AnalysisContext";

const timeHorizons = ["6 months", "1 year", "3 years", "5 years"];

const features = [
  { icon: TrendingUp, label: "Bull Analysis", desc: "Identifies growth potential and upside catalysts", color: "text-bull" },
  { icon: AlertTriangle, label: "Bear Analysis", desc: "Assesses downside risks and red flags", color: "text-bear" },
  { icon: Target, label: "Portfolio Fit", desc: "Evaluates fit within your portfolio strategy", color: "text-strategist" },
];

const Landing = () => {
  const navigate = useNavigate();
  const { setFormData } = useAnalysis();
  const [ticker, setTicker] = useState("");
  const [amount, setAmount] = useState("");
  const [portfolio, setPortfolio] = useState("");
  const [riskTolerance, setRiskTolerance] = useState("");
  const [timeHorizon, setTimeHorizon] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormData({ ticker, amount, portfolio, riskTolerance, timeHorizon });
    navigate("/loading");
  };

  const isValid = ticker && amount && portfolio && riskTolerance && timeHorizon;

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="container mx-auto flex items-center justify-between px-6 py-4">
          <div>
            <h2 className="text-xl font-bold text-primary tracking-tight">InvestiGate</h2>
            <p className="text-xs text-muted-foreground">Multi-Agent Investment Analysis</p>
          </div>
        </div>
      </header>

      <main className="container mx-auto max-w-2xl px-6 py-16 animate-fade-in">
        {/* Hero */}
        <div className="text-center mb-10">
          <h1 className="text-4xl font-bold text-foreground tracking-tight mb-3">Should You Invest?</h1>
          <p className="text-lg text-muted-foreground max-w-lg mx-auto">
            Get balanced analysis from three AI analysts who debate every investment
          </p>
        </div>

        {/* Form */}
        <Card className="shadow-sm mb-12">
          <CardContent className="p-8">
            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="text-sm font-medium text-foreground mb-1.5 block">Stock Ticker</label>
                <Input
                  placeholder="e.g. NVDA, AAPL, TSLA"
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value.toUpperCase())}
                  className="focus-visible:ring-accent"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-foreground mb-1.5 block">Investment Amount</label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">$</span>
                    <Input placeholder="25,000" value={amount} onChange={(e) => setAmount(e.target.value)} className="pl-7 focus-visible:ring-accent" />
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-foreground mb-1.5 block">Portfolio Value</label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">$</span>
                    <Input placeholder="500,000" value={portfolio} onChange={(e) => setPortfolio(e.target.value)} className="pl-7 focus-visible:ring-accent" />
                  </div>
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-foreground mb-1.5 block">Risk Tolerance</label>
                <Select value={riskTolerance} onValueChange={setRiskTolerance}>
                  <SelectTrigger className="focus:ring-accent">
                    <SelectValue placeholder="Select risk tolerance" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="conservative">Conservative</SelectItem>
                    <SelectItem value="moderate">Moderate</SelectItem>
                    <SelectItem value="aggressive">Aggressive</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-sm font-medium text-foreground mb-1.5 block">Time Horizon</label>
                <div className="flex gap-2">
                  {timeHorizons.map((h) => (
                    <button
                      key={h}
                      type="button"
                      onClick={() => setTimeHorizon(h)}
                      className={`flex-1 rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                        timeHorizon === h
                          ? "bg-accent text-accent-foreground border-accent"
                          : "border-border text-muted-foreground hover:border-accent/50"
                      }`}
                    >
                      {h}
                    </button>
                  ))}
                </div>
              </div>
              <Button
                type="submit"
                disabled={!isValid}
                className="w-full bg-accent text-accent-foreground hover:bg-accent/90 h-11 text-base font-semibold"
              >
                Analyze Investment
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Feature cards */}
        <div className="grid grid-cols-3 gap-4">
          {features.map((f) => (
            <div key={f.label} className="rounded-lg bg-secondary p-5 text-center">
              <f.icon className={`mx-auto mb-2 ${f.color}`} size={24} />
              <p className="text-sm font-semibold text-foreground">{f.label}</p>
              <p className="text-xs text-muted-foreground mt-1">{f.desc}</p>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
};

export default Landing;
