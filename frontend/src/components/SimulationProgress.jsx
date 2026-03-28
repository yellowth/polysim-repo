import { Play, Loader2, CheckCircle2, Zap } from "lucide-react";

export default function SimulationProgress({
  status, agentCount, totalAgents, contagionRound,
  onSimulate, marketPrice, scenarioTitle,
}) {
  const total = totalAgents || 100;
  const pct = total > 0 ? Math.min(100, (agentCount / total) * 100) : 0;

  const phaseLabel = (() => {
    if (status === "idle") return null;
    if (status === "connecting") return "Connecting…";
    if (status === "complete") return "Complete";
    if (contagionRound >= 0) return `Contagion round ${contagionRound + 1}/3 — social cascade propagating`;
    return `Evaluating agents — ${agentCount}/${total}`;
  })();

  return (
    <div className="shrink-0 bg-slate-900/60 border-b border-slate-800 backdrop-blur-sm">
      {/* Main row */}
      <div className="flex items-center gap-4 px-5 py-2.5">

        {/* Left: action / status */}
        {status === "idle" && (
          <button
            onClick={onSimulate}
            className="flex items-center gap-2 px-4 py-1.5 bg-emerald-500 hover:bg-emerald-400 active:bg-emerald-600 text-slate-950 font-semibold rounded-lg text-sm transition-colors shadow-lg shadow-emerald-500/20"
          >
            <Play className="w-4 h-4 fill-current" /> Run Simulation
          </button>
        )}

        {status === "connecting" && (
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <Loader2 className="w-4 h-4 animate-spin" />
            Connecting…
          </div>
        )}

        {status === "simulating" && (
          <div className="flex items-center gap-2">
            {contagionRound >= 0 ? (
              <Zap className="w-4 h-4 text-indigo-400 shrink-0" style={{ animation: "pulse 1s infinite" }} />
            ) : (
              <Loader2 className="w-4 h-4 animate-spin text-emerald-400 shrink-0" />
            )}
          </div>
        )}

        {status === "complete" && (
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
        )}

        {/* Phase label */}
        <div className="flex-1 min-w-0">
          {scenarioTitle && status !== "idle" && (
            <div className="text-[10px] text-slate-600 truncate mb-0.5">{scenarioTitle}</div>
          )}
          {phaseLabel && (
            <div className={`text-xs font-medium truncate ${
              status === "complete" ? "text-emerald-400" :
              contagionRound >= 0 ? "text-indigo-400" :
              "text-slate-400"
            }`}>
              {phaseLabel}
            </div>
          )}
        </div>

        {/* Progress bar (agent phase only) */}
        {status === "simulating" && contagionRound < 0 && (
          <div className="flex items-center gap-2 shrink-0">
            <div className="w-32 h-1.5 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-emerald-500 rounded-full transition-all duration-300"
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="text-xs text-slate-500 font-mono w-8 text-right">{Math.round(pct)}%</span>
          </div>
        )}

        {/* Contagion dots */}
        {status === "simulating" && contagionRound >= 0 && (
          <div className="flex gap-1.5 shrink-0">
            {[0, 1, 2].map((r) => (
              <div
                key={r}
                className={`w-2 h-2 rounded-full transition-all duration-500 ${
                  r < contagionRound
                    ? "bg-indigo-400"
                    : r === contagionRound
                    ? "bg-indigo-400 animate-pulse"
                    : "bg-slate-700"
                }`}
              />
            ))}
          </div>
        )}

        {/* Final call badge when complete */}
        {status === "complete" && marketPrice && (
          <div className={`text-xs font-bold px-3 py-1 rounded-full border shrink-0 ${
            marketPrice.market_price >= 0.5
              ? "bg-emerald-500/10 border-emerald-500/40 text-emerald-400"
              : "bg-red-500/10 border-red-500/40 text-red-400"
          }`}>
            {marketPrice.market_price >= 0.5 ? "PASS" : "FAIL"} · {(marketPrice.market_price * 100).toFixed(1)}%
          </div>
        )}
      </div>

      {/* Progress stripe (agent phase) */}
      {status === "simulating" && contagionRound < 0 && (
        <div className="h-px bg-slate-800 mx-5 rounded-full overflow-hidden">
          <div
            className="h-full bg-emerald-500/40 transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>
      )}
    </div>
  );
}
