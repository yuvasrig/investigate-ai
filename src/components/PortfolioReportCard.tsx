/**
 * PortfolioReportCard — Tier-1 portfolio analysis panel.
 *
 * Shows the automatic categorisation of every holding into:
 *   🟢 Long-term Core   — buy & hold forever
 *   🟡 Growth Positions — monitor closely
 *   🔴 Concentration Risks
 *   🛡  Missing Protections
 *
 * Clicking any holding fires onAnalyze(ticker) to trigger Tier-2 (4-agent) analysis.
 */

import { useState } from "react";
import { motion } from "framer-motion";
import CountUp from "react-countup";
import {
  ShieldAlert, TrendingUp, Target, Shield,
  ChevronDown, ChevronRight, AlertTriangle, Info,
  ArrowRight, Zap,
} from "lucide-react";

// ── Types matching backend response ───────────────────────────────────────────

export interface PortfolioHoldingEntry {
  ticker: string;
  name: string;
  value: number;
  percentage: number;
  reason: string;
}

export interface ConcentrationRisk {
  type: "single_stock" | "sector";
  ticker: string;
  name: string;
  exposure: number;
  limit: number;
  severity: "medium" | "high";
  message: string;
}

export interface MissingProtection {
  type: "bonds" | "international";
  current: number;
  recommended_min: number;
  recommended_max: number;
  message: string;
  tickers: string[];
}

export interface PortfolioSummary {
  total_holdings: number;
  long_term_pct: number;
  growth_pct: number;
  bond_pct: number;
  intl_pct: number;
  tech_pct: number;
  risk_level: "LOW" | "MODERATE" | "HIGH" | "VERY HIGH";
  risk_score: number;
}

export interface PortfolioReport {
  long_term_core: PortfolioHoldingEntry[];
  growth_positions: PortfolioHoldingEntry[];
  concentration_risks: ConcentrationRisk[];
  missing_protections: MissingProtection[];
  overall_risk_score: number;
  summary: PortfolioSummary;
}

interface Props {
  report: PortfolioReport;
  onAnalyze: (ticker: string) => void;
}

// ── Helpers ────────────────────────────────────────────────────────────────────

const RISK_CONFIG = {
  LOW:       { color: "text-emerald-400", bg: "bg-emerald-500/10", bar: "bg-emerald-500", label: "Low Risk" },
  MODERATE:  { color: "text-amber-400",   bg: "bg-amber-500/10",   bar: "bg-amber-500",   label: "Moderate Risk" },
  HIGH:      { color: "text-orange-400",  bg: "bg-orange-500/10",  bar: "bg-orange-500",  label: "High Risk" },
  "VERY HIGH":{ color: "text-rose-400",   bg: "bg-rose-500/10",    bar: "bg-rose-500",    label: "Very High Risk" },
};

function RiskScoreBar({ score }: { score: number }) {
  const level = score < 3 ? "LOW" : score < 5 ? "MODERATE" : score < 7 ? "HIGH" : "VERY HIGH";
  const cfg = RISK_CONFIG[level];
  const pct = (score / 10) * 100;

  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-1.5 bg-muted/40 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${cfg.bar}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`text-xs font-bold whitespace-nowrap ${cfg.color}`}>
        <CountUp end={score} duration={0.9} decimals={1} /> / 10
      </span>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SectionHeader({
  icon, label, count, pct, color, open, onToggle,
}: {
  icon: React.ReactNode;
  label: string;
  count: number;
  pct?: number;
  color: string;
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      onClick={onToggle}
      className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50 transition-colors text-left"
    >
      <span className="text-base leading-none">{icon}</span>
      <div className="flex-1 min-w-0">
        <span className={`text-sm font-bold ${color}`}>{label}</span>
        {pct !== undefined && (
          <span className="ml-2 text-xs text-gray-500">
            {pct.toFixed(1)}% of portfolio
          </span>
        )}
      </div>
      <span className={`text-xs font-semibold px-2 py-0.5 rounded-full bg-gray-100 text-gray-600`}>
        {count}
      </span>
      {open ? (
        <ChevronDown className="w-3.5 h-3.5 text-gray-400 shrink-0" />
      ) : (
        <ChevronRight className="w-3.5 h-3.5 text-gray-400 shrink-0" />
      )}
    </button>
  );
}

const HOLDING_GRADIENTS = [
  "from-blue-500 to-indigo-600", "from-violet-500 to-purple-600",
  "from-emerald-500 to-teal-600", "from-orange-500 to-amber-600",
  "from-sky-500 to-cyan-600", "from-lime-500 to-green-600",
];

function HoldingRow({
  holding,
  onAnalyze,
  accentColor,
}: {
  holding: PortfolioHoldingEntry;
  onAnalyze: (t: string) => void;
  accentColor: string;
}) {
  const idx = holding.ticker.charCodeAt(0) % HOLDING_GRADIENTS.length;
  return (
    <div className="flex items-center gap-3 px-4 py-3 hover:bg-gray-50 transition-colors group cursor-default">
      {/* Gradient avatar */}
      <div className={`w-8 h-8 rounded-full bg-gradient-to-br ${HOLDING_GRADIENTS[idx]} flex items-center justify-center shrink-0 shadow-sm`}>
        <span className="text-[9px] font-bold text-white">
          {holding.ticker.slice(0, 2)}
        </span>
      </div>

      {/* Name + reason */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-bold text-gray-900">{holding.ticker}</span>
          <span className={`text-xs font-semibold ${accentColor}`}>
            {holding.percentage.toFixed(1)}%
          </span>
        </div>
        <div className="text-[10px] text-gray-500 truncate">{holding.reason}</div>
      </div>

      {/* Value */}
      <div className="text-xs font-semibold text-gray-700 tabular-nums shrink-0">
        ${holding.value.toLocaleString(undefined, { maximumFractionDigits: 0 })}
      </div>

      {/* Analyse CTA — appears on hover */}
      <button
        onClick={() => onAnalyze(holding.ticker)}
        className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 text-[10px] font-bold text-blue-600 bg-blue-50 hover:bg-blue-100 px-2.5 py-1 rounded-lg shrink-0 shadow-sm"
        title={`Run 4-agent analysis on ${holding.ticker}`}
      >
        <Zap className="w-3 h-3" />
        Analyse
      </button>
    </div>
  );
}

function RiskCard({
  risk,
  onFix,
}: {
  risk: ConcentrationRisk;
  onFix: (t: string) => void;
}) {
  const isHigh = risk.severity === "high";
  return (
    <div className={`mx-4 mb-2 rounded-r-xl border-l-4 p-4 ${
      isHigh
        ? "border-red-500 bg-red-50"
        : "border-orange-400 bg-orange-50"
    }`}>
      <div className="flex items-start gap-3">
        <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
          isHigh ? "bg-red-100" : "bg-orange-100"
        }`}>
          <AlertTriangle className={`w-4 h-4 ${isHigh ? "text-red-600" : "text-orange-600"}`} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-sm font-bold ${isHigh ? "text-gray-900" : "text-gray-900"}`}>
              {risk.name}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
              isHigh ? "bg-red-100 text-red-700" : "bg-orange-100 text-orange-700"
            }`}>
              {risk.exposure.toFixed(1)}% (limit {risk.limit}%)
            </span>
          </div>
          <p className="text-xs text-gray-600 mt-1 leading-relaxed">
            {risk.message}
          </p>
          {risk.type === "single_stock" && (
            <button
              onClick={() => onFix(risk.ticker)}
              className={`mt-2 text-xs font-semibold flex items-center gap-1 ${
                isHigh ? "text-red-600 hover:text-red-700" : "text-orange-600 hover:text-orange-700"
              }`}
            >
              Fix This Risk →
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function ProtectionCard({ protection, onAnalyze }: { protection: MissingProtection; onAnalyze: (t: string) => void }) {
  const isbonds = protection.type === "bonds";
  return (
    <div className="mx-4 mb-2 rounded-r-xl border-l-4 border-amber-400 bg-amber-50 p-4">
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-full bg-amber-100 flex items-center justify-center shrink-0">
          <span className="text-base">{isbonds ? "📉" : "🌍"}</span>
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-bold text-gray-900">
              {isbonds ? "No Bond Buffer" : "No International Exposure"}
            </span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 font-semibold">
              {protection.current.toFixed(1)}% / {protection.recommended_min}%+ needed
            </span>
          </div>
          <p className="text-xs text-gray-600 mt-1 leading-relaxed">
            {protection.message}
          </p>
          <div className="flex gap-1.5 mt-2 flex-wrap">
            {protection.tickers.map((t) => (
              <button
                key={t}
                onClick={() => onAnalyze(t)}
                className="text-xs font-mono font-bold px-2.5 py-1 rounded-lg bg-white border border-amber-300 text-amber-700 hover:bg-amber-100 transition-colors shadow-sm"
              >
                {t}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function PortfolioReportCard({ report, onAnalyze }: Props) {
  const [open, setOpen] = useState(true);
  const [openCore, setOpenCore]       = useState(true);
  const [openGrowth, setOpenGrowth]   = useState(true);
  const [openRisks, setOpenRisks]     = useState(true);
  const [openMissing, setOpenMissing] = useState(true);

  const { summary, concentration_risks, missing_protections } = report;
  const riskCfg = RISK_CONFIG[summary.risk_level];
  const alertCount = concentration_risks.length + missing_protections.length;

  return (
    <div className="rounded-2xl bg-white shadow-sm border border-gray-100 overflow-hidden mb-4">
      {/* ── Header ── */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-3 px-4 py-4 hover:bg-gray-50 transition-colors text-left"
      >
        <Target className="w-4 h-4 text-accent shrink-0" />
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-foreground">Portfolio Analysis</span>
            {alertCount > 0 && (
              <span className="flex items-center gap-1 text-[10px] font-semibold text-rose-400 bg-rose-500/10 px-1.5 py-0.5 rounded-full">
                <ShieldAlert className="w-3 h-3" />
                {alertCount} alert{alertCount !== 1 ? "s" : ""}
              </span>
            )}
          </div>
          <div className="mt-1 w-48">
            <RiskScoreBar score={report.overall_risk_score} />
          </div>
        </div>
        <div className="flex flex-col items-end gap-1 shrink-0">
          <span className={`text-xs font-bold ${riskCfg.color}`}>
            {riskCfg.label}
          </span>
          {open ? (
            <ChevronDown className="w-4 h-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="w-4 h-4 text-muted-foreground" />
          )}
        </div>
      </button>

      {open && (
        <>
          {/* ── Summary strip ── */}
          <div className="px-4 pb-3 grid grid-cols-3 gap-2 border-t border-border/30 pt-3">
            {[
              { label: "Core", value: summary.long_term_pct, color: "text-emerald-400" },
              { label: "Growth", value: summary.growth_pct, color: "text-amber-400" },
              { label: "Tech", value: summary.tech_pct, color: summary.tech_pct > 40 ? "text-rose-400" : "text-muted-foreground" },
            ].map(({ label, value, color }) => (
              <div key={label} className="text-center">
                <div className={`text-sm font-bold ${color}`}>{value.toFixed(0)}%</div>
                <div className="text-[10px] text-muted-foreground">{label}</div>
              </div>
            ))}
          </div>

          <div className="border-t border-gray-100 divide-y divide-gray-100">
            {/* ── Long-term Core ── */}
            {report.long_term_core.length > 0 && (
              <div>
                <SectionHeader
                  icon="🟢"
                  label="Long-Term Core"
                  count={report.long_term_core.length}
                  pct={summary.long_term_pct}
                  color="text-emerald-400"
                  open={openCore}
                  onToggle={() => setOpenCore((v) => !v)}
                />
                {openCore && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    transition={{ duration: 0.2 }}
                    className="pb-1"
                  >
                    <p className="px-4 pb-2 text-[10px] text-muted-foreground italic">
                      Strategy: Buy &amp; hold through market cycles — don&apos;t overthink these
                    </p>
                    {report.long_term_core.map((h) => (
                      <HoldingRow
                        key={h.ticker}
                        holding={h}
                        onAnalyze={onAnalyze}
                        accentColor="text-emerald-400"
                      />
                    ))}
                  </motion.div>
                )}
              </div>
            )}

            {/* ── Growth Positions ── */}
            {report.growth_positions.length > 0 && (
              <div>
                <SectionHeader
                  icon="🟡"
                  label="Growth Positions"
                  count={report.growth_positions.length}
                  pct={summary.growth_pct}
                  color="text-amber-400"
                  open={openGrowth}
                  onToggle={() => setOpenGrowth((v) => !v)}
                />
                {openGrowth && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    transition={{ duration: 0.2 }}
                    className="pb-1"
                  >
                    <p className="px-4 pb-2 text-[10px] text-muted-foreground italic">
                      Strategy: Monitor closely — click any holding to run a 4-agent deep analysis
                    </p>
                    {report.growth_positions.map((h) => (
                      <HoldingRow
                        key={h.ticker}
                        holding={h}
                        onAnalyze={onAnalyze}
                        accentColor="text-amber-400"
                      />
                    ))}
                  </motion.div>
                )}
              </div>
            )}

            {/* ── Concentration Risks ── */}
            {concentration_risks.length > 0 && (
              <div>
                <SectionHeader
                  icon="🔴"
                  label="Concentration Risks"
                  count={concentration_risks.length}
                  color="text-rose-400"
                  open={openRisks}
                  onToggle={() => setOpenRisks((v) => !v)}
                />
                {openRisks && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    transition={{ duration: 0.2 }}
                    className="pt-2 pb-1"
                  >
                    {concentration_risks.map((r, i) => (
                      <RiskCard
                        key={i}
                        risk={r}
                        onFix={onAnalyze}
                      />
                    ))}
                  </motion.div>
                )}
              </div>
            )}

            {/* ── Missing Protections ── */}
            {missing_protections.length > 0 && (
              <div>
                <SectionHeader
                  icon="🛡️"
                  label="Missing Protections"
                  count={missing_protections.length}
                  color="text-amber-400"
                  open={openMissing}
                  onToggle={() => setOpenMissing((v) => !v)}
                />
                {openMissing && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    transition={{ duration: 0.2 }}
                    className="pt-2 pb-1"
                  >
                    {missing_protections.map((p, i) => (
                      <ProtectionCard
                        key={i}
                        protection={p}
                        onAnalyze={onAnalyze}
                      />
                    ))}
                  </motion.div>
                )}
              </div>
            )}

            {/* ── All clear ── */}
            {concentration_risks.length === 0 && missing_protections.length === 0 && (
              <div className="px-4 py-4 flex items-center gap-2 text-emerald-400">
                <Info className="w-4 h-4 shrink-0" />
                <span className="text-xs">
                  No major risks detected — your portfolio looks well-diversified!
                </span>
              </div>
            )}
          </div>

          {/* ── Footer CTA ── */}
          <div className="border-t border-gray-100 px-4 py-3 flex items-center justify-between bg-gray-50">
            <span className="text-[10px] text-gray-500">
              Hover any holding to run a deep 4-agent analysis
            </span>
            <div className="flex items-center gap-1 text-[10px] text-accent font-semibold">
              <TrendingUp className="w-3 h-3" />
              <Shield className="w-3 h-3" />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
