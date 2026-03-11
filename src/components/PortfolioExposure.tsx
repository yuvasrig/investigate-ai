import { useState } from "react";
import { AlertTriangle, TrendingDown, Info, ChevronDown, ChevronUp } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

export interface ExposureData {
  current_exposure: {
    direct: number;
    indirect: Array<{
      source: string;
      amount: number;
      percentage: number;
      etf_value: number;
    }>;
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

interface Props {
  exposure: ExposureData;
  ticker: string;
  proposedAmount: number;
}

export function PortfolioExposure({ exposure, ticker, proposedAmount }: Props) {
  const [showDetails, setShowDetails] = useState(false);
  const { current_exposure, proposed_exposure, warning } = exposure;

  if (!exposure.has_hidden_exposure && !warning.exceeds_limit) {
    // Minimal card — no significant hidden exposure
    return (
      <Card className="border-2 border-green-200 shadow-sm">
        <CardContent className="p-5 bg-green-50 flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-green-100 border border-green-400 flex items-center justify-center flex-shrink-0">
            <Info className="w-4 h-4 text-green-600" />
          </div>
          <div>
            <p className="font-semibold text-green-700 text-sm">No significant hidden {ticker} exposure</p>
            <p className="text-xs text-gray-500">Your ETF holdings don't have substantial {ticker} concentration.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const currentPct = (current_exposure.current_percentage * 100).toFixed(1);
  const proposedPct = (proposed_exposure.percentage * 100).toFixed(1);
  const limitPct = (warning.limit * 100).toFixed(0);

  return (
    <Card className="border-2 border-red-300 shadow-sm">
      <CardContent className="p-6 bg-red-50 space-y-5">
        {/* Header */}
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-6 h-6 text-red-500 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="text-xl font-bold text-red-700">
              Hidden {ticker} Exposure Detected
            </h3>
            <p className="text-sm text-gray-600 mt-1">
              You already own{" "}
              <span className="font-bold">${current_exposure.total_current.toLocaleString()}</span>{" "}
              in {ticker} through your index funds — before this purchase.
            </p>
          </div>
        </div>

        {/* Indirect holdings breakdown */}
        {current_exposure.indirect.length > 0 && (
          <div className="bg-white rounded-lg border border-red-200 p-4">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
              Your ETFs already own {ticker}:
            </p>
            <div className="space-y-2">
              {current_exposure.indirect.map((h) => (
                <div key={h.source} className="flex justify-between items-center text-sm">
                  <div className="flex items-center gap-2">
                    <span className="w-12 font-mono text-xs bg-gray-100 text-gray-700 px-1.5 py-0.5 rounded">
                      {h.source}
                    </span>
                    <span className="text-gray-500 text-xs">
                      ({h.percentage.toFixed(1)}% {ticker})
                    </span>
                  </div>
                  <span className="font-semibold text-gray-800">
                    ${h.amount.toLocaleString()}
                  </span>
                </div>
              ))}
              <div className="border-t border-gray-200 pt-2 mt-2 flex justify-between font-semibold text-sm">
                <span className="text-gray-700">Total hidden {ticker}:</span>
                <span className="text-gray-900">${current_exposure.total_current.toLocaleString()}</span>
              </div>
            </div>
          </div>
        )}

        {/* Before/After numbers */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <p className="text-xs text-gray-500 mb-1">Current {ticker} total</p>
            <p className="text-2xl font-bold text-gray-800">
              ${current_exposure.total_current.toLocaleString()}
            </p>
            <p className="text-xs text-gray-500 mt-1">{currentPct}% of portfolio</p>
          </div>
          <div className={`rounded-lg p-4 ${warning.exceeds_limit ? "bg-red-100 border-2 border-red-400" : "bg-white border border-gray-200"}`}>
            <p className={`text-xs mb-1 ${warning.exceeds_limit ? "text-red-600" : "text-gray-500"}`}>
              After +${proposedAmount.toLocaleString()}
            </p>
            <p className={`text-2xl font-bold ${warning.exceeds_limit ? "text-red-700" : "text-gray-800"}`}>
              ${proposed_exposure.total.toLocaleString()}
            </p>
            <p className={`text-xs mt-1 ${warning.exceeds_limit ? "text-red-600 font-semibold" : "text-gray-500"}`}>
              {proposedPct}% of portfolio{warning.exceeds_limit ? " ⚠️" : ""}
            </p>
          </div>
        </div>

        {/* Warning box */}
        {warning.exceeds_limit && (
          <div className="bg-red-100 border-2 border-red-400 rounded-lg p-4 space-y-3">
            <div className="flex items-start gap-2">
              <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-bold text-red-700">
                  Exceeds {limitPct}% single-stock limit
                </p>
                <p className="text-sm text-red-600 mt-0.5">
                  Your total {ticker} exposure would be {proposedPct}% — consider reducing.
                </p>
              </div>
            </div>
            <div className="flex items-center justify-between bg-white rounded p-3">
              <div className="flex items-center gap-1.5 text-sm text-gray-700">
                <TrendingDown className="w-4 h-4 text-red-500" />
                If {ticker} drops 20%:
              </div>
              <div className="text-right">
                <p className="font-bold text-red-700 text-lg">
                  −${warning.risk_if_drops_20.toLocaleString()}
                </p>
                <p className="text-xs text-gray-500">
                  = {warning.portfolio_impact_pct.toFixed(1)}% of your whole portfolio
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Recommended max */}
        <div className="bg-green-50 border-2 border-green-300 rounded-lg p-4">
          <p className="text-sm font-semibold text-green-700 mb-1">
            Recommended maximum to stay under {limitPct}% limit:
          </p>
          <p className="text-3xl font-bold text-green-700">
            ${warning.max_additional.toLocaleString()}
          </p>
          {warning.max_additional < proposedAmount && (
            <p className="text-xs text-gray-500 mt-1">
              (instead of the ${proposedAmount.toLocaleString()} you planned)
            </p>
          )}
        </div>

        {/* Learn more toggle */}
        <button
          onClick={() => setShowDetails((v) => !v)}
          className="flex items-center gap-1.5 text-xs text-blue-600 hover:text-blue-800 font-medium"
        >
          {showDetails ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          {showDetails ? "Hide" : "Learn more about"} concentration risk
        </button>

        {showDetails && (
          <div className="bg-blue-50 rounded-lg p-4 text-sm text-gray-700 space-y-2">
            <p>
              <strong>Why {limitPct}%?</strong> Financial advisors typically recommend
              limiting any single stock (including indirect ETF exposure) to 10-15% of
              your portfolio to reduce concentration risk.
            </p>
            <p>
              <strong>Hidden exposure</strong> occurs when you own the same stock
              indirectly through multiple ETFs. This tool calculates your true,
              total exposure so you can make informed decisions.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
