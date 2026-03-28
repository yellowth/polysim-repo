import { Play, Loader2, CheckCircle2, Users, Zap, TrendingUp } from "lucide-react";

export default function SimulationProgress({ status, agentCount, totalAgents, contagionRound, onSimulate, latestAgent, marketPrice }) {
  const total = totalAgents || 100;

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
                  Market round {contagionRound + 1}/3
                </span>
                <span className="text-xs text-slate-500">
                  (information cascading through social networks)
                </span>
                {marketPrice && (
                  <span className="text-xs text-emerald-400 font-mono ml-2">
                    <TrendingUp className="w-3 h-3 inline mr-1" />
                    {(marketPrice.market_price * 100).toFixed(1)}%
                  </span>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2 min-w-0">
                <Users className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                <span className="text-sm text-slate-300">
                  Agent <span className="text-emerald-400 font-mono">{agentCount}</span>/{total} evaluated
                </span>
                <div className="w-24 h-1.5 bg-slate-800 rounded-full overflow-hidden shrink-0">
                  <div
                    className="h-full bg-emerald-500 transition-all duration-300"
                    style={{ width: `${(agentCount / total) * 100}%` }}
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
            {marketPrice && (
              <span className="text-sm text-slate-400 ml-2">
                Market price: <span className="text-emerald-400 font-mono">{(marketPrice.market_price * 100).toFixed(1)}%</span>
              </span>
            )}
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
          {latestAgent.conviction_bet > 0 && (
            <span className="text-emerald-500/60 shrink-0 font-mono">
              ${latestAgent.conviction_bet.toFixed(0)} bet
            </span>
          )}
          <span className="truncate italic text-slate-600">
            &ldquo;{latestAgent.reason?.slice(0, 80)}...&rdquo;
          </span>
        </div>
      )}
    </div>
  );
}
