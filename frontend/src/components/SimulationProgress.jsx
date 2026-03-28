import { Play, Loader2, CheckCircle2, Users, Zap } from "lucide-react";

export default function SimulationProgress({ status, agentCount, contagionRound, onSimulate, latestAgent }) {
  return (
    <div className="px-6 py-2 border-b border-slate-800 bg-slate-900/50">
      <div className="flex items-center gap-4">
        {status === "idle" && (
          <button
            onClick={onSimulate}
            className="flex items-center gap-2 px-4 py-1.5 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-medium rounded-lg text-sm transition-colors"
          >
            <Play className="w-4 h-4" /> Run Simulation
          </button>
        )}
        {status === "connecting" && (
          <span className="text-sm text-slate-400">Connecting to simulation engine...</span>
        )}
        {status === "simulating" && (
          <>
            <Loader2 className="w-4 h-4 animate-spin text-emerald-400 shrink-0" />
            {contagionRound >= 0 ? (
              <div className="flex items-center gap-2">
                <Zap className="w-3.5 h-3.5 text-amber-400" />
                <span className="text-sm text-amber-400">
                  Social contagion propagation — round {contagionRound + 1}/3
                </span>
                <span className="text-xs text-slate-500">
                  (sentiment rippling through communities)
                </span>
              </div>
            ) : (
              <div className="flex items-center gap-2 min-w-0">
                <Users className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                <span className="text-sm text-slate-300">
                  Agent <span className="text-emerald-400 font-mono">{agentCount}</span>/40 evaluated
                </span>
                {/* Progress bar */}
                <div className="w-24 h-1.5 bg-slate-800 rounded-full overflow-hidden shrink-0">
                  <div
                    className="h-full bg-emerald-500 transition-all duration-300"
                    style={{ width: `${(agentCount / 40) * 100}%` }}
                  />
                </div>
              </div>
            )}
          </>
        )}
        {status === "complete" && (
          <>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span className="text-sm text-emerald-400">
              {agentCount} agents evaluated · Simulation complete
            </span>
          </>
        )}
      </div>

      {/* Live agent feed during simulation */}
      {status === "simulating" && latestAgent && contagionRound < 0 && (
        <div className="mt-1.5 flex items-center gap-2 text-xs text-slate-500 overflow-hidden">
          <span className={`inline-block w-2 h-2 rounded-full shrink-0 ${
            latestAgent.sentiment === "support" ? "bg-emerald-500" :
            latestAgent.sentiment === "reject" ? "bg-red-500" : "bg-amber-500"
          }`} />
          <span className="text-slate-400 shrink-0">
            {latestAgent.persona?.race} {latestAgent.persona?.age} · {latestAgent.persona?.grc}
          </span>
          <span className="truncate italic text-slate-600">
            "{latestAgent.reason?.slice(0, 80)}..."
          </span>
        </div>
      )}
    </div>
  );
}
