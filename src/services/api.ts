/**
 * Centralized API client for the InvestiGate backend.
 * Set VITE_API_URL in .env to override the default (http://localhost:8000).
 */

const API_BASE = (import.meta.env.VITE_API_URL as string) || "http://localhost:8000";

// ── Types mirroring backend Pydantic schemas ──────────────────────────────────

export interface ConfidenceBreakdown {
  growth_potential: number;
  risk_level: number;
  portfolio_fit: number;
  timing: number;
  execution_clarity: number;
}

export interface BullAnalysis {
  competitive_advantages: string[];
  growth_catalysts: string[];
  valuation_justification: string;
  best_case_target: number;
  best_case_timeline: string;
  confidence: number;
  pe_ratio: number | null;
}

export interface BearAnalysis {
  competition_threats: string[];
  valuation_concerns: string;
  cyclical_risks: string[];
  worst_case_target: number;
  worst_case_timeline: string;
  confidence: number;
  pe_ratio: number | null;
}

export interface StrategistAnalysis {
  current_exposure: string;
  concentration_risk: "LOW" | "MODERATE" | "HIGH" | "VERY HIGH";
  concentration_explanation: string;
  recommended_allocation: number;
  reasoning: string;
  alternative_options: string[];
}

export interface JudgeRecommendation {
  action: string;
  recommended_amount: number;
  reasoning: string;
  confidence_overall: number;
  confidence_breakdown: ConfidenceBreakdown;
  entry_strategy: string;
  risk_management: string;
  key_factors: string[];
}

export interface TrafficLightResult {
  color: "green" | "yellow" | "red";
  message: string;
  conviction_diff: number;
  key_conflict: {
    topic: string;
    bull_view: string;
    bear_view: string;
    gap?: number | null;
  };
  bull_recommendation: string;
  bear_recommendation: string;
  bull_conviction: number;
  bear_conviction: number;
}

export interface IndirectHolding {
  source: string;
  amount: number;
  percentage: number;
  etf_value: number;
}

export interface ExposureData {
  current_exposure: {
    direct: number;
    indirect: IndirectHolding[];
    total_current: number;
    current_percentage: number;
  };
  proposed_exposure: {
    new_direct: number;
    total_indirect: number;
    total: number;
    percentage: number;
    portfolio_value: number;
  };
  warning: {
    exceeds_limit: boolean;
    limit: number;
    max_additional: number;
    risk_if_drops_20: number;
    portfolio_impact_pct: number;
  };
  has_hidden_exposure: boolean;
}

export interface AnalysisResponse {
  analysis_id: string;
  llm_provider: string;
  ticker: string;
  bull_analysis: BullAnalysis;
  bear_analysis: BearAnalysis;
  strategist_analysis: StrategistAnalysis;
  final_recommendation: JudgeRecommendation;
  market_data: Record<string, unknown> | null;
  rag_summary: { sec: number; news: number; cache_hit: boolean } | null;
  traffic_light: TrafficLightResult | null;
  portfolio_exposure: ExposureData | null;
  execution_time: number;
  timestamp: string;
}

export interface PortfolioHolding {
  ticker: string;
  value: number;
  name?: string;
  shares?: number;
}

export interface AnalyzeRequest {
  ticker: string;
  amount: number;
  portfolio: { total_value: number };
  risk_tolerance: string;
  time_horizon: string;
  portfolio_holdings?: PortfolioHolding[];
}

export interface HistoryItem {
  analysis_id: string;
  ticker: string;
  llm_provider: string;
  execution_time: number;
  timestamp: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

async function apiCall<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const raw = await res.text().catch(() => "");
    let detail = raw || res.statusText || `HTTP ${res.status}`;

    if (raw) {
      try {
        const parsed = JSON.parse(raw) as { detail?: unknown };
        if (typeof parsed.detail === "string") {
          detail = parsed.detail;
        } else if (parsed.detail != null) {
          detail = JSON.stringify(parsed.detail);
        }
      } catch {
        // Keep plain text fallback when response is not JSON.
      }
    }

    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

// ── Public API ────────────────────────────────────────────────────────────────

/** Run a full multi-agent analysis. */
export async function analyze(req: AnalyzeRequest): Promise<AnalysisResponse> {
  return apiCall<AnalysisResponse>("/analyze", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

/** Fetch a single analysis by UUID. */
export async function getAnalysis(id: string): Promise<AnalysisResponse> {
  return apiCall<AnalysisResponse>(`/analysis/${id}`);
}

/** Fetch paginated history (most recent first). */
export async function getHistory(
  limit = 20,
  offset = 0
): Promise<HistoryItem[]> {
  return apiCall<HistoryItem[]>(`/history?limit=${limit}&offset=${offset}`);
}

/** Fetch multiple analyses side-by-side for comparison. */
export async function compareAnalyses(
  ids: string[]
): Promise<Record<string, AnalysisResponse>> {
  return apiCall<Record<string, AnalysisResponse>>("/compare", {
    method: "POST",
    body: JSON.stringify(ids),
  });
}
