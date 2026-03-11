import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Clock, TrendingUp, Loader2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { getHistory, getAnalysis, type HistoryItem, type AnalysisResponse } from "@/services/api";
import { useAnalysis } from "@/context/AnalysisContext";

const HistoryPage = () => {
  const navigate = useNavigate();
  const { setAnalysisResult } = useAnalysis();
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loadingId, setLoadingId] = useState<string | null>(null);

  useEffect(() => {
    getHistory()
      .then(setItems)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, []);

  const openAnalysis = async (id: string) => {
    setLoadingId(id);
    try {
      const result = await getAnalysis(id) as unknown as AnalysisResponse;
      setAnalysisResult(result);
      navigate("/results");
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : String(e));
    } finally {
      setLoadingId(null);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card">
        <div className="container mx-auto flex items-center justify-between px-6 py-4">
          <h2 className="text-xl font-bold text-primary tracking-tight">InvestiGate</h2>
          <button onClick={() => navigate("/")} className="text-sm font-medium text-accent hover:text-accent/80 transition-colors">
            ← New Analysis
          </button>
        </div>
      </header>

      <main className="container mx-auto max-w-4xl px-6 py-8 animate-fade-in">
        <div className="mb-8 flex items-center gap-3">
          <Clock className="text-accent" size={24} />
          <h1 className="text-2xl font-bold text-foreground">Analysis History</h1>
        </div>

        {loading && (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="animate-spin text-accent" size={32} />
          </div>
        )}

        {error && (
          <p className="text-bear text-sm">{error}</p>
        )}

        {!loading && !error && items.length === 0 && (
          <p className="text-muted-foreground text-sm">No analyses yet. Run your first one!</p>
        )}

        <div className="space-y-3">
          {items.map((item) => (
            <Card
              key={item.analysis_id}
              className="shadow-sm hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => openAnalysis(item.analysis_id)}
            >
              <CardContent className="p-5 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-full bg-accent/10 flex items-center justify-center">
                    <TrendingUp className="text-accent" size={18} />
                  </div>
                  <div>
                    <p className="font-semibold text-foreground">{item.ticker}</p>
                    <p className="text-xs text-muted-foreground">
                      {item.timestamp ? new Date(item.timestamp).toLocaleString() : "—"}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-6 text-right">
                  <div>
                    <p className="text-xs text-muted-foreground">Provider</p>
                    <p className="text-sm font-medium text-foreground">{item.llm_provider}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Time</p>
                    <p className="text-sm font-medium text-foreground">{item.execution_time?.toFixed(1)}s</p>
                  </div>
                  {loadingId === item.analysis_id ? (
                    <Loader2 className="animate-spin text-accent" size={16} />
                  ) : (
                    <span className="text-xs text-accent">View →</span>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </main>
    </div>
  );
};

export default HistoryPage;
