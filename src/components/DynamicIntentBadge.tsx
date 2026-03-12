import { motion } from "framer-motion";
import { Radar, Sparkles } from "lucide-react";

interface Props {
  scenarios: string[];
}

export default function DynamicIntentBadge({ scenarios }: Props) {
  if (!scenarios.length) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="rounded-2xl border border-blue-200 bg-gradient-to-r from-blue-50 via-white to-slate-50 p-4 shadow-sm"
    >
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-600 text-white shadow-sm">
          <Radar size={18} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="text-sm font-semibold text-slate-900">Detected Stress Tests</p>
            <Sparkles size={14} className="text-blue-600" />
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Tier 2 intent routing matched these scenarios from your query.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {scenarios.map((scenario, index) => (
              <motion.span
                key={`${scenario}-${index}`}
                initial={{ opacity: 0, scale: 0.92 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.08 * index, duration: 0.2 }}
                className="rounded-full border border-blue-200 bg-white px-3 py-1 text-xs font-medium text-blue-700"
              >
                {scenario}
              </motion.span>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
