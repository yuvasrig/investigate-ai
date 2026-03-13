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

export interface VerifiedClaim {
  claim: string;
  is_speculative: boolean;
  sec_section?: string | null;  // e.g. "Item 1A - Risk Factors"
}

export interface SecFiling {
  cik: string;
  ticker: string;
  accession_number: string;
  filing_date: string;
  filing_url: string;
  viewer_url: string;
  section_urls: {
    business: string;
    risk_factors: string;
    mda: string;
    financials: string;
  };
}

export interface SecExcerpt {
  ticker: string;
  section: string;
  section_label: string;
  filing_date: string;
  filing_url: string;
  text: string;
}

export interface BullAnalysis {
  competitive_advantages: VerifiedClaim[];
  growth_catalysts: VerifiedClaim[];
  valuation_justification: string;
  best_case_target: number;
  best_case_timeline: string;
  confidence: number;
  pe_ratio: number | null;
}

export interface BearAnalysis {
  competition_threats: VerifiedClaim[];
  valuation_concerns: string;
  cyclical_risks: VerifiedClaim[];
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

export interface AgentEvidenceScore {
  data_citations: number;      // 0-10
  calculation_rigor: number;   // 0-10
  historical_precedent: number; // 0-10
  counterargument: number;     // 0-10
  total: number;               // 0-40
}

export interface EvidenceAssessment {
  bull: AgentEvidenceScore;
  bear: AgentEvidenceScore;
  strategist: AgentEvidenceScore;
  bull_weighted: number;
  bear_weighted: number;
  strategist_weighted: number;
  winner: "bull" | "bear" | "strategist";
  winner_reasoning: string;
}

export interface EvaluatedScenario {
  scenario_name: string;
  verified_analog_used: string;
}

export interface IntentRouterResult {
  target_asset: string | null;
  scenarios: string[];
  requires_deep_dive: boolean;
}

export interface JudgeRecommendation {
  action: string;
  recommended_amount: number;
  reasoning: string;
  confidence_overall: number;
  confidence_breakdown: ConfidenceBreakdown;
  entry_strategy: string;
  risk_management: string;
  traffic_light_color: "red" | "yellow" | "green";
  evaluated_scenarios: EvaluatedScenario[];
  key_factors: string[];
  evidence_assessment?: EvidenceAssessment | null;
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
  intent: IntentRouterResult | null;
  market_data: Record<string, unknown> | null;
  rag_summary: { sec: number; news: number; cache_hit: boolean } | null;
  traffic_light: TrafficLightResult | null;
  portfolio_exposure: ExposureData | null;
  kelly_sizing?: {
    kelly_fraction: number;
    raw_kelly_amount: number;
    correlation_adjusted_amount: number;
    final_amount: number;
    sizing_rationale: string;
    scale_factor: number;
  } | null;
  sec_filing?: SecFiling | null;
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
  user_query?: string;
  analysis_action?: "buy" | "sell" | "hold";
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

export type StreamEvent =
  | { status: string }
  | { agent: string; status: "complete" }
  | { type: "result"; payload: AnalysisResponse }
  | { error: string };

/** 
 * Run an analysis via Server-Sent Events to get real-time progress.
 * Calls `onEvent` as updates stream in. The Promise resolves with the 
 * final AnalysisResponse.
 */
export async function streamAnalyze(
  req: AnalyzeRequest,
  onEvent: (event: StreamEvent) => void
): Promise<AnalysisResponse> {
  const response = await fetch(`${API_BASE}/analyze/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });

  if (!response.ok) {
    throw new Error(`Failed to start analysis: ${response.statusText}`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error("Stream not supported");

  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Process full SSE lines (ending in \n\n)
    const parts = buffer.split("\n\n");
    // Keep the last partial chunk in the buffer
    buffer = parts.pop() || "";

    for (const part of parts) {
      if (part.startsWith("data: ")) {
        const jsonStr = part.slice(6);
        try {
          const evt = JSON.parse(jsonStr) as StreamEvent;
          onEvent(evt);

          if ("type" in evt && evt.type === "result") {
            return evt.payload;
          }
          if ("error" in evt) {
            throw new Error(evt.error);
          }
        } catch (err) {
          console.warn("Failed to parse SSE chunk:", part, err);
        }
      }
    }
  }

  throw new Error("Stream ended before receiving final result.");
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

/** Fetch SEC 10-K filing metadata for a ticker. */
export async function getSecFiling(ticker: string): Promise<SecFiling> {
  return apiCall<SecFiling>(`/api/sec/${ticker}/filing`);
}

/** Fetch a plain-text excerpt from a specific 10-K section. */
export async function getSecExcerpt(
  ticker: string,
  section: "business" | "risk_factors" | "mda" | "financials"
): Promise<SecExcerpt> {
  return apiCall<SecExcerpt>(`/api/sec/${ticker}/excerpt?section=${section}`);
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
