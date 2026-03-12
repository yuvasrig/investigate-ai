import { ShieldCheck } from "lucide-react";

import type { EvaluatedScenario } from "@/services/api";

interface Props {
  scenarios: EvaluatedScenario[];
}

export default function EvaluatedScenariosMatrix({ scenarios }: Props) {
  if (!scenarios.length) return null;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 px-5 py-4">
        <div className="flex items-center gap-2">
          <ShieldCheck size={16} className="text-emerald-500" />
          <h3 className="text-sm font-semibold text-slate-900">Scenario Verification Matrix</h3>
        </div>
        <p className="mt-1 text-xs text-slate-500">
          Each stress test the judge evaluated and the historical analog used.
        </p>
      </div>
      <div className="divide-y divide-slate-100">
        {scenarios.map((scenario, index) => (
          <div key={`${scenario.scenario_name}-${index}`} className="grid gap-3 px-5 py-4 md:grid-cols-[1.1fr_1.9fr]">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                Scenario
              </p>
              <p className="mt-1 text-sm font-medium text-slate-900">
                {scenario.scenario_name}
              </p>
            </div>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                Verified Analog
              </p>
              <p className="mt-1 text-sm text-slate-600">
                {scenario.verified_analog_used}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
