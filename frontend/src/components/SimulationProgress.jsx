import { Play, Loader2, CheckCircle2 } from "lucide-react";

export default function SimulationProgress({ status, agentCount, contagionRound, onSimulate }) {
  return (
    <div className="flex items-center gap-4 px-6 py-2 border-b border-slate-800 bg-slate-900/50">
      {status === "idle" && (
        <button
          onClick={onSimulate}
          className="flex items-center gap-2 px-4 py-1.5 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-medium rounded-lg text-sm transition-colors"
        >
          <Play className="w-4 h-4" /> Run Simulation
        </button>
      )}
      {status === "connecting" && (
        <span className="text-sm text-slate-400">Connecting...</span>
      )}
      {status === "simulating" && (
        <>
          <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
          <span className="text-sm text-slate-400">
            {contagionRound >= 0
              ? `Contagion propagation round ${contagionRound + 1}/3`
              : `Evaluating agents... ${agentCount} complete`}
          </span>
        </>
      )}
      {status === "complete" && (
        <>
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span className="text-sm text-emerald-400">{agentCount} agents evaluated · Simulation complete</span>
        </>
      )}
    </div>
  );
}
