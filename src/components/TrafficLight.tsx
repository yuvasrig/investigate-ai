import { CheckCircle, AlertTriangle, AlertCircle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

export interface TrafficLightData {
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

interface Props {
  trafficLight: TrafficLightData;
}

const config = {
  green: {
    Icon: CheckCircle,
    border: "border-green-500",
    bg: "bg-green-50",
    ring: "bg-green-100 border-green-400",
    iconColor: "text-green-500",
    label: "LOW RISK",
    labelColor: "text-green-700",
    badge: "bg-green-100 text-green-700",
    barBull: "bg-green-500",
    barBear: "bg-green-300",
  },
  yellow: {
    Icon: AlertCircle,
    border: "border-yellow-500",
    bg: "bg-yellow-50",
    ring: "bg-yellow-100 border-yellow-400",
    iconColor: "text-yellow-500",
    label: "CAUTION",
    labelColor: "text-yellow-700",
    badge: "bg-yellow-100 text-yellow-700",
    barBull: "bg-green-500",
    barBear: "bg-red-400",
  },
  red: {
    Icon: AlertTriangle,
    border: "border-red-500",
    bg: "bg-red-50",
    ring: "bg-red-100 border-red-400",
    iconColor: "text-red-500",
    label: "HIGH RISK",
    labelColor: "text-red-700",
    badge: "bg-red-100 text-red-700",
    barBull: "bg-red-300",
    barBear: "bg-red-600",
  },
};

export function TrafficLight({ trafficLight }: Props) {
  const { color, message, conviction_diff, key_conflict,
          bull_conviction, bear_conviction } = trafficLight;
  const cfg = config[color];
  const { Icon } = cfg;

  return (
    <Card className={`border-2 ${cfg.border} shadow-sm`}>
      <CardContent className={`p-6 ${cfg.bg} space-y-5`}>
        {/* Light + Label */}
        <div className="flex items-center gap-5">
          <div className={`w-20 h-20 rounded-full border-4 ${cfg.ring} flex items-center justify-center flex-shrink-0`}>
            <Icon className={`w-10 h-10 ${cfg.iconColor}`} />
          </div>
          <div>
            <span className={`text-xs font-bold tracking-widest ${cfg.labelColor} uppercase`}>
              {cfg.label}
            </span>
            <h3 className={`text-xl font-bold ${cfg.labelColor} mt-0.5`}>{message}</h3>
            <p className="text-xs text-gray-500 mt-1">
              Conviction gap: {conviction_diff.toFixed(0)} pts
            </p>
          </div>
        </div>

        {/* Agent Conviction Bars */}
        <div className="space-y-3">
          {[
            { label: "Bull Analyst → BUY", score: bull_conviction, bar: cfg.barBull },
            { label: "Bear Analyst → SELL", score: bear_conviction, bar: cfg.barBear },
          ].map(({ label, score, bar }) => (
            <div key={label}>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-gray-600 font-medium">{label}</span>
                <span className="font-bold text-gray-800">{score.toFixed(0)}/100</span>
              </div>
              <div className="h-2 w-full rounded-full bg-gray-200">
                <div
                  className={`h-full rounded-full ${bar} transition-all duration-700`}
                  style={{ width: `${score}%` }}
                />
              </div>
            </div>
          ))}
        </div>

        {/* Key Conflict */}
        <div className="border-t border-gray-200 pt-4">
          <p className="text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wide">
            Key Disagreement: {key_conflict.topic}
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-green-50 border border-green-200 rounded-lg p-3">
              <p className="text-xs font-semibold text-green-700 mb-0.5">Bull View</p>
              <p className="text-xs text-gray-600">{key_conflict.bull_view}</p>
            </div>
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-xs font-semibold text-red-700 mb-0.5">Bear View</p>
              <p className="text-xs text-gray-600">{key_conflict.bear_view}</p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
