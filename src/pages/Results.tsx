import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { TrendingUp, AlertTriangle, Target, Scale, CheckCircle2, AlertCircle, FileDown, Loader2, Info, FlaskConical, Trophy, ChevronDown, ChevronUp } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { useAnalysis } from "@/context/AnalysisContext";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Cell, Tooltip } from "recharts";
import { TrafficLight } from "@/components/TrafficLight";
import { PortfolioExposure, ExposureData } from "@/components/PortfolioExposure";
import DynamicIntentBadge from "@/components/DynamicIntentBadge";
import EvaluatedScenariosMatrix from "@/components/EvaluatedScenariosMatrix";
import CitationModal from "@/components/CitationModal";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type {
  AgentEvidenceScore,
  BearAnalysis,
  BullAnalysis,
  EvidenceAssessment,
  SecFiling,
  StrategistAnalysis,
  VerifiedClaim,
} from "@/services/api";

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

const AGENT_ROLES_TAB = [
  {
    key: "bull",
    title: "Bull Analyst",
    subtitle: "Senior Equity Analyst",
    accent: "text-bull bg-bull/10",
    role:
      "Builds the strongest upside case for the stock using growth quality, competitive moats, and valuation support.",
    focusesOn: [
      "Competitive advantages and defensibility",
      "Growth catalysts and earnings momentum",
      "Best-case target price and timeline",
    ],
  },
  {
    key: "bear",
    title: "Bear Analyst",
    subtitle: "Veteran Short Seller",
    accent: "text-bear bg-bear/10",
    role:
      "Builds the strongest downside case by stress-testing assumptions and identifying structural risks.",
    focusesOn: [
      "Valuation concerns and downside asymmetry",
      "Competitive and execution threats",
      "Worst-case target price and timeline",
    ],
  },
  {
    key: "strategist",
    title: "Portfolio Strategist",
    subtitle: "Head of Portfolio Construction",
    accent: "text-strategist bg-strategist/10",
    role:
      "Translates the debate into position sizing and portfolio fit while managing concentration risk.",
    focusesOn: [
      "Current and indirect exposure",
      "Diversification and concentration limits",
      "Recommended allocation and alternatives",
    ],
  },
  {
    key: "cio",
    title: "CIO / Judge",
    subtitle: "Chief Investment Officer",
    accent: "text-accent bg-accent/10",
    role:
      "Makes the final decision by weighing conviction against evidence quality across all agents.",
    focusesOn: [
      "Evidence-weighted winner selection",
      "Final action, amount, and confidence",
      "Entry strategy, risk management, and key factors",
    ],
  },
] as const;

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
function AgentRolesTab() {
  return (
    <Card className="shadow-sm mb-8">
      <CardContent className="p-6">
        <h3 className="text-lg font-semibold text-foreground mb-2">What Each Agent Does</h3>
        <p className="text-sm text-muted-foreground mb-5">
          Bull, Bear, Strategist, and CIO each have distinct mandates so the final call is made after structured debate.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {AGENT_ROLES_TAB.map((agent) => (
            <div key={agent.key} className="rounded-lg border border-border p-4">
              <div className="flex items-center justify-between mb-2 gap-2">
                <h4 className="text-sm font-semibold text-foreground">{agent.title}</h4>
                <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${agent.accent}`}>
                  {agent.subtitle}
                </span>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed mb-3">{agent.role}</p>
              <p className="text-xs font-semibold text-foreground mb-1.5">Primary Focus</p>
              <ul className="space-y-1">
                {agent.focusesOn.map((line) => (
                  <li key={line} className="text-xs text-muted-foreground">• {line}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

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

function countSpeculativeClaims(claims: VerifiedClaim[]): number {
  return claims.filter((claim) => claim.is_speculative).length;
}

function ClaimList({
  claims,
  icon,
  iconColor,
  ticker,
  secFiling,
}: {
  claims: VerifiedClaim[];
  icon: React.ReactNode;
  iconColor: string;
  ticker?: string;
  secFiling?: SecFiling | null;
}) {
  const [citation, setCitation] = useState<{ claim: VerifiedClaim } | null>(null);

  return (
    <>
      <ul className="space-y-2">
        {claims.map((item, index) => (
          <li key={`${item.claim}-${index}`} className="flex items-start gap-2 text-sm text-muted-foreground">
            <span className={`shrink-0 mt-0.5 ${iconColor}`}>{icon}</span>
            <div className="min-w-0">
              <span>{item.claim}</span>
              {item.is_speculative && (
                <span className="ml-2 inline-flex rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-700">
                  speculative
                </span>
              )}
              {item.sec_section && ticker && (
                <button
                  onClick={() => setCitation({ claim: item })}
                  className="ml-2 inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-blue-700 hover:bg-blue-200 transition-colors cursor-pointer"
                  title={`View SEC source: ${item.sec_section}`}
                >
                  SEC ↗
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>

      {citation && ticker && (
        <CitationModal
          ticker={ticker}
          secSection={citation.claim.sec_section!}
          claimText={citation.claim.claim}
          filingUrl={secFiling?.filing_url}
          onClose={() => setCitation(null)}
        />
      )}
    </>
  );
}

// ── Evidence Scoring Components ───────────────────────────────────────────────

function ScoreBar({ label, score, max }: { label: string; score: number; max: number }) {
  const pct = Math.round((score / max) * 100);
  const color =
    pct >= 80 ? "bg-bull" : pct >= 60 ? "bg-amber-400" : pct >= 40 ? "bg-orange-400" : "bg-bear";
  return (
    <div>
      <div className="flex items-center justify-between text-xs mb-1">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-semibold tabular-nums text-foreground">
          {score}/{max}
        </span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-secondary overflow-hidden">
        <div
          className={`h-full rounded-full ${color} transition-all duration-700`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function EvidenceScoreCard({
  scores,
  weightedScore,
  agentColor,
  hallucinationPenalty = 0,
  speculativeClaimsCount = 0,
}: {
  scores: AgentEvidenceScore;
  weightedScore: number;
  agentColor: string;
  hallucinationPenalty?: number;
  speculativeClaimsCount?: number;
}) {
  const totalPct = Math.round((scores.total / 40) * 100);
  const ringColor =
    totalPct >= 75 ? "text-bull" : totalPct >= 55 ? "text-amber-500" : "text-bear";

  return (
    <div className="mt-4 pt-4 border-t border-border">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
          <FlaskConical size={13} className="text-muted-foreground" />
          Evidence Quality
        </div>
        <span className={`text-lg font-bold tabular-nums ${ringColor}`}>
          {scores.total}/40
        </span>
      </div>
      <div className="space-y-2">
        <ScoreBar label="Data Citations" score={scores.data_citations} max={10} />
        <ScoreBar label="Calculation Rigor" score={scores.calculation_rigor} max={10} />
        <ScoreBar label="Historical Precedent" score={scores.historical_precedent} max={10} />
        <ScoreBar label="Counterarguments" score={scores.counterargument} max={10} />
      </div>
      {hallucinationPenalty < 0 && (
        <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
          Hallucination penalty {hallucinationPenalty} for {speculativeClaimsCount} speculative claim
          {speculativeClaimsCount === 1 ? "" : "s"}.
        </div>
      )}
      <div className={`mt-3 pt-3 border-t border-border flex items-center justify-between`}>
        <div>
          <p className="text-xs text-muted-foreground">Weighted Score</p>
          <p className="text-xs text-muted-foreground/70">Conviction × Evidence</p>
        </div>
        <span className={`text-xl font-bold tabular-nums ${agentColor}`}>
          {weightedScore.toFixed(1)}
        </span>
      </div>
    </div>
  );
}

function WeightedScoresPanel({ evidence }: { evidence: EvidenceAssessment }) {
  const agents = [
    { key: "bull", label: "🐂 Bull Analyst", weighted: evidence.bull_weighted, total: evidence.bull.total, color: "text-bull", bar: "bg-bull" },
    { key: "bear", label: "🐻 Bear Analyst", weighted: evidence.bear_weighted, total: evidence.bear.total, color: "text-bear", bar: "bg-bear" },
    { key: "strategist", label: "📊 Strategist", weighted: evidence.strategist_weighted, total: evidence.strategist.total, color: "text-strategist", bar: "bg-strategist" },
  ] as const;

  const maxWeighted = Math.max(evidence.bull_weighted, evidence.bear_weighted, evidence.strategist_weighted);

  return (
    <div className="mt-6 pt-6 border-t border-border">
      <div className="flex items-center gap-2 mb-4">
        <Trophy size={16} className="text-accent" />
        <h4 className="text-sm font-semibold text-foreground">Evidence-Weighted Decision</h4>
      </div>

      <div className="space-y-3 mb-4">
        {agents.map((a) => {
          const isWinner = a.key === evidence.winner;
          const barPct = maxWeighted > 0 ? (a.weighted / maxWeighted) * 100 : 0;
          return (
            <div key={a.key} className={`rounded-lg p-3 ${isWinner ? "bg-accent/8 border border-accent/20" : "bg-secondary/40"}`}>
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-foreground">{a.label}</span>
                  {isWinner && (
                    <span className="text-xs font-semibold bg-accent text-white px-1.5 py-0.5 rounded-full">
                      Winner
                    </span>
                  )}
                </div>
                <div className="text-right">
                  <span className={`text-base font-bold tabular-nums ${a.color}`}>
                    {a.weighted.toFixed(1)}
                  </span>
                  <span className="text-xs text-muted-foreground ml-1">
                    ({a.total}/40 evidence)
                  </span>
                </div>
              </div>
              <div className="h-1.5 w-full rounded-full bg-secondary overflow-hidden">
                <div
                  className={`h-full rounded-full ${a.bar} transition-all duration-700`}
                  style={{ width: `${barPct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {evidence.winner_reasoning && (
        <div className="text-xs text-muted-foreground leading-relaxed bg-secondary/40 rounded-lg p-3">
          <span className="font-semibold text-foreground">Judge's rationale: </span>
          {evidence.winner_reasoning}
        </div>
      )}
    </div>
  );
}

// ── Agent card sub-components (with evidence score accordion) ─────────────────

function BullCard({
  bull_analysis,
  evidence,
  ticker,
  secFiling,
}: {
  bull_analysis: BullAnalysis;
  evidence: EvidenceAssessment | null;
  ticker?: string;
  secFiling?: SecFiling | null;
}) {
  const [showEvidence, setShowEvidence] = useState(false);
  const speculativeClaimsCount =
    countSpeculativeClaims(bull_analysis.competitive_advantages) +
    countSpeculativeClaims(bull_analysis.growth_catalysts);
  const hallucinationPenalty = speculativeClaimsCount > 0 ? -20 : 0;
  return (
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
        <p className="text-2xl font-bold text-foreground mb-0.5 tabular-nums">
          ${bull_analysis.best_case_target.toLocaleString()}
        </p>
        <p className="text-xs text-muted-foreground mb-5">{bull_analysis.best_case_timeline}</p>
        <p className="text-sm font-semibold text-foreground mb-3">Key Advantages</p>
        <ClaimList
          claims={bull_analysis.competitive_advantages}
          icon={<CheckCircle2 size={14} />}
          iconColor="text-bull"
          ticker={ticker}
          secFiling={secFiling}
        />
        <p className="text-xs font-semibold text-foreground mt-5 mb-2">Growth Catalysts</p>
        <ClaimList
          claims={bull_analysis.growth_catalysts}
          icon={<TrendingUp size={13} />}
          iconColor="text-bull"
          ticker={ticker}
          secFiling={secFiling}
        />
        {bull_analysis.valuation_justification && (
          <div className="mt-4 p-3 bg-bull/5 rounded-lg">
            <p className="text-xs font-semibold text-foreground mb-1">Valuation Justification</p>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {bull_analysis.valuation_justification}
            </p>
          </div>
        )}
        {evidence && (
          <>
            <button
              onClick={() => setShowEvidence((v) => !v)}
              className="mt-4 flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              <FlaskConical size={12} />
              {showEvidence ? "Hide" : "Show"} evidence scores
              {showEvidence ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>
            {showEvidence && (
              <EvidenceScoreCard
                scores={evidence.bull}
                weightedScore={evidence.bull_weighted}
                agentColor="text-bull"
                hallucinationPenalty={hallucinationPenalty}
                speculativeClaimsCount={speculativeClaimsCount}
              />
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function BearCard({
  bear_analysis,
  evidence,
  ticker,
  secFiling,
}: {
  bear_analysis: BearAnalysis;
  evidence: EvidenceAssessment | null;
  ticker?: string;
  secFiling?: SecFiling | null;
}) {
  const [showEvidence, setShowEvidence] = useState(false);
  const speculativeClaimsCount =
    countSpeculativeClaims(bear_analysis.competition_threats) +
    countSpeculativeClaims(bear_analysis.cyclical_risks);
  const hallucinationPenalty = speculativeClaimsCount > 0 ? -20 : 0;
  return (
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
        <p className="text-2xl font-bold text-foreground mb-0.5 tabular-nums">
          ${bear_analysis.worst_case_target.toLocaleString()}
        </p>
        <p className="text-xs text-muted-foreground mb-5">{bear_analysis.worst_case_timeline}</p>
        <p className="text-sm font-semibold text-foreground mb-3">Key Risks</p>
        <ClaimList
          claims={bear_analysis.competition_threats}
          icon={<AlertCircle size={14} />}
          iconColor="text-bear"
          ticker={ticker}
          secFiling={secFiling}
        />
        <div className="mt-5 p-3 bg-secondary rounded-lg">
          <p className="text-xs font-semibold text-foreground mb-1">Valuation Concerns</p>
          <p className="text-xs text-muted-foreground leading-relaxed">
            {bear_analysis.valuation_concerns}
          </p>
        </div>
        {bear_analysis.cyclical_risks.length > 0 && (
          <div className="mt-4">
            <p className="text-xs font-semibold text-foreground mb-2">Cyclical Risks</p>
            <ClaimList
              claims={bear_analysis.cyclical_risks}
              icon={<AlertTriangle size={13} />}
              iconColor="text-bear"
              ticker={ticker}
              secFiling={secFiling}
            />
          </div>
        )}
        {evidence && (
          <>
            <button
              onClick={() => setShowEvidence((v) => !v)}
              className="mt-4 flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              <FlaskConical size={12} />
              {showEvidence ? "Hide" : "Show"} evidence scores
              {showEvidence ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>
            {showEvidence && (
              <EvidenceScoreCard
                scores={evidence.bear}
                weightedScore={evidence.bear_weighted}
                agentColor="text-bear"
                hallucinationPenalty={hallucinationPenalty}
                speculativeClaimsCount={speculativeClaimsCount}
              />
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function StrategistCard({
  strategist_analysis,
  evidence,
}: {
  strategist_analysis: StrategistAnalysis;
  evidence: EvidenceAssessment | null;
}) {
  const [showEvidence, setShowEvidence] = useState(false);
  return (
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
        <p className="text-2xl font-bold text-foreground mb-1 tabular-nums">
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
        {evidence && (
          <>
            <button
              onClick={() => setShowEvidence((v) => !v)}
              className="mt-4 flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              <FlaskConical size={12} />
              {showEvidence ? "Hide" : "Show"} evidence scores
              {showEvidence ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>
            {showEvidence && (
              <EvidenceScoreCard
                scores={evidence.strategist}
                weightedScore={evidence.strategist_weighted}
                agentColor="text-strategist"
              />
            )}
          </>
        )}
      </CardContent>
    </Card>
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
    intent,
    market_data,
    traffic_light,
    portfolio_exposure,
    sec_filing,
  } = analysisResult;

  const evidence = final_recommendation.evidence_assessment ?? null;

  const proposedAmount = formData.amount ? parseFloat(formData.amount.replace(/,/g, "")) : 0;

  const companyName = (market_data as Record<string, unknown>)?.longName as string | undefined;
  const currentPrice = (market_data as Record<string, unknown>)?.currentPrice as number | undefined;
  const routedScenarios =
    intent?.scenarios ?? final_recommendation.evaluated_scenarios.map((item) => item.scenario_name);

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
          <p className="text-muted-foreground tabular-nums">
            {companyName ?? ""}
            {currentPrice != null ? ` · $${currentPrice.toLocaleString()}` : ""}
          </p>
        </div>
        {/* ── Final Recommendation — shown FIRST ──────────────────────────── */}
        <Tabs defaultValue="analysis" className="mb-2">
          <TabsList className="mb-6">
            <TabsTrigger value="analysis">Analysis</TabsTrigger>
            <TabsTrigger value="roles">Agent Roles</TabsTrigger>
          </TabsList>
          <TabsContent value="roles">
            <AgentRolesTab />
          </TabsContent>
          <TabsContent value="analysis">
        <Card className="border-l-4 border-l-accent shadow-sm mb-8">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <Scale className="text-accent" size={20} />
                <h3 className="text-lg font-semibold text-foreground">Final Recommendation</h3>
              </div>
              <div className="flex items-center gap-3">
                <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${
                  final_recommendation.traffic_light_color === "green"
                    ? "bg-emerald-100 text-emerald-700"
                    : final_recommendation.traffic_light_color === "yellow"
                      ? "bg-amber-100 text-amber-700"
                      : "bg-rose-100 text-rose-700"
                }`}>
                  {final_recommendation.traffic_light_color}
                </span>
                <span className="text-3xl font-bold text-accent tabular-nums">
                  {final_recommendation.confidence_overall}%
                </span>
              </div>
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
                  <p className={`text-sm font-bold ${m.accent ? "text-bull" : "text-foreground"} ${m.label === "Amount" ? "tabular-nums" : ""}`}>{m.value}</p>
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
                    <span className="font-medium text-foreground tabular-nums">{d.value}%</span>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-secondary">
                    <div className="h-full rounded-full bg-accent transition-all" style={{ width: `${d.value}%` }} />
                  </div>
                </div>
              ))}
            </div>

            {/* Evidence-Weighted Decision Panel */}
            {evidence && <WeightedScoresPanel evidence={evidence} />}
          </CardContent>
        </Card>

        <WarningBanner
          trafficColor={traffic_light?.color}
          concentrationRisk={strategist_analysis.concentration_risk}
        />

        {traffic_light && (
          <div className="mb-6">
            <TrafficLight trafficLight={traffic_light} />
          </div>
        )}

        <div className="mb-6">
          <DynamicIntentBadge scenarios={routedScenarios} />
        </div>


        {final_recommendation.evaluated_scenarios.length > 0 && (
          <div className="mb-8">
            <EvaluatedScenariosMatrix scenarios={final_recommendation.evaluated_scenarios} />
          </div>
        )}

        {/* ── Agent Cards with role descriptions ───────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-8">
          {/* Bull */}
          <BullCard
            bull_analysis={bull_analysis}
            evidence={evidence}
            ticker={ticker}
            secFiling={sec_filing}
          />

          {/* Bear */}
          <BearCard
            bear_analysis={bear_analysis}
            evidence={evidence}
            ticker={ticker}
            secFiling={sec_filing}
          />

          {/* Strategist */}
          <StrategistCard strategist_analysis={strategist_analysis} evidence={evidence} />
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

        {/* Portfolio Hidden Exposure (moved to bottom) */}
        {portfolio_exposure && (
          <div className="mb-6">
            <PortfolioExposure
              exposure={portfolio_exposure as ExposureData}
              ticker={ticker}
              proposedAmount={proposedAmount}
            />
          </div>
        )}

          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
};

export default Results;
