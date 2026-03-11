import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { GitCompare, Loader2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { compareAnalyses, type AnalysisResponse } from "@/services/api";

const ComparePage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const ids = searchParams.get("ids")?.split(",").filter(Boolean) ?? [];

  const [results, setResults] = useState<Record<string, AnalysisResponse> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (ids.length < 2) {
      setError("Provide at least 2 analysis IDs in ?ids=id1,id2");
      setLoading(false);
      return;
    }
    compareAnalyses(ids)
      .then((data) => setResults(data as Record<string, AnalysisResponse>))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card">
        <div className="container mx-auto flex items-center justify-between px-6 py-4">
          <h2 className="text-xl font-bold text-primary tracking-tight">InvestiGate</h2>
          <div className="flex gap-4">
            <button onClick={() => navigate("/history")} className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              History
            </button>
            <button onClick={() => navigate("/")} className="text-sm font-medium text-accent hover:text-accent/80 transition-colors">
              ← New Analysis
            </button>
          </div>
        </div>
      </header>

      <main className="container mx-auto max-w-6xl px-6 py-8 animate-fade-in">
        <div className="mb-8 flex items-center gap-3">
          <GitCompare className="text-accent" size={24} />
          <h1 className="text-2xl font-bold text-foreground">Compare Analyses</h1>
        </div>

        {loading && (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="animate-spin text-accent" size={32} />
          </div>
        )}

        {error && <p className="text-bear text-sm">{error}</p>}

        {results && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {Object.entries(results).map(([id, analysis]) => (
              <Card key={id} className="shadow-sm">
                <CardContent className="p-6">
                  <div className="mb-4">
                    <h2 className="text-xl font-bold text-foreground">{analysis.ticker}</h2>
                    <p className="text-xs text-muted-foreground">{analysis.timestamp}</p>
                  </div>

                  <div className="space-y-3 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Action</span>
                      <span className="font-semibold text-foreground">
                        {analysis.final_recommendation.action.toUpperCase()}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Recommended Amount</span>
                      <span className="font-semibold text-foreground">
                        ${analysis.final_recommendation.recommended_amount.toLocaleString()}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Overall Confidence</span>
                      <span className="font-semibold text-accent">
                        {analysis.final_recommendation.confidence_overall}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Bull Target</span>
                      <span className="font-semibold text-bull">
                        ${analysis.bull_analysis.best_case_target.toLocaleString()}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Bear Target</span>
                      <span className="font-semibold text-bear">
                        ${analysis.bear_analysis.worst_case_target.toLocaleString()}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Concentration Risk</span>
                      <span className="font-semibold text-foreground">
                        {analysis.strategist_analysis.concentration_risk}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Allocation</span>
                      <span className="font-semibold text-foreground">
                        ${analysis.strategist_analysis.recommended_allocation.toLocaleString()}
                      </span>
                    </div>
                  </div>

                  <div className="mt-4 pt-4 border-t border-border">
                    <p className="text-xs text-muted-foreground leading-relaxed line-clamp-3">
                      {analysis.final_recommendation.reasoning}
                    </p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  );
};

export default ComparePage;
