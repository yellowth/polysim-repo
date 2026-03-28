import { useState } from "react";
import { SlidersHorizontal } from "lucide-react";

const LEVERS = {
  income_threshold: { label: "Income Threshold", min: 2000, max: 15000, step: 500, default: 5000, unit: "SGD" },
  subsidy_amount: { label: "Subsidy Amount", min: 0, max: 50000, step: 5000, default: 10000, unit: "SGD" },
  rollout_months: { label: "Rollout Timeline", min: 3, max: 36, step: 3, default: 12, unit: "mo" },
};

export default function LeverControls({ onLeverChange }) {
  const [values, setValues] = useState(
    Object.fromEntries(Object.entries(LEVERS).map(([k, v]) => [k, v.default]))
  );

  const handleChange = (lever, val) => {
    const numVal = Number(val);
    setValues((prev) => ({ ...prev, [lever]: numVal }));
  };

  const handleApply = (lever) => {
    onLeverChange(lever, values[lever]);
  };

  return (
    <div>
      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
        <SlidersHorizontal className="w-3.5 h-3.5" /> Policy Levers
      </h3>
      <div className="space-y-3">
        {Object.entries(LEVERS).map(([key, config]) => (
          <div key={key} className="bg-slate-900 rounded-lg p-3">
            <div className="flex justify-between text-xs mb-1.5">
              <span className="text-slate-400">{config.label}</span>
              <span className="text-emerald-400 font-mono">
                {key === "rollout_months" ? `${values[key]} mo` : `$${values[key].toLocaleString()}`}
              </span>
            </div>
            <input
              type="range"
              min={config.min} max={config.max} step={config.step}
              value={values[key]}
              onChange={(e) => handleChange(key, e.target.value)}
              onMouseUp={() => handleApply(key)}
              onTouchEnd={() => handleApply(key)}
              className="w-full accent-emerald-500 h-1.5"
            />
          </div>
        ))}
      </div>
    </div>
  );
}
