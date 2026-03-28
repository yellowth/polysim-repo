import { useEffect, useRef } from "react";

const SENTIMENT_STYLES = {
  support: {
    dot: "bg-emerald-500",
    badge: "bg-emerald-500/15 text-emerald-400 border-emerald-500/25",
    bar: "bg-emerald-500",
    border: "border-l-emerald-500/60",
  },
  reject: {
    dot: "bg-red-500",
    badge: "bg-red-500/15 text-red-400 border-red-500/25",
    bar: "bg-red-500",
    border: "border-l-red-500/60",
  },
  neutral: {
    dot: "bg-amber-500",
    badge: "bg-amber-500/15 text-amber-400 border-amber-500/25",
    bar: "bg-amber-500",
    border: "border-l-amber-500/60",
  },
};

function AgentCard({ agent, isLatest }) {
  const s = SENTIMENT_STYLES[agent.sentiment] || SENTIMENT_STYLES.neutral;
  const confidence = Math.round((agent.confidence || 0) * 100);
  const bet = agent.conviction_bet || 0;

  return (
    <div
      className={`
        flex gap-2.5 px-3 py-2.5 border-l-2 transition-all duration-300
        ${s.border}
        ${isLatest ? "bg-slate-800/70" : "bg-slate-900/50 hover:bg-slate-800/40"}
      `}
      style={{ animation: isLatest ? "slideIn 0.25s ease-out" : "none" }}
    >
      {/* Sentiment dot */}
      <div className="pt-1 shrink-0">
        <div className={`w-2 h-2 rounded-full ${s.dot} ${isLatest ? "shadow-lg" : ""}`}
          style={isLatest ? { boxShadow: `0 0 6px currentColor` } : {}} />
      </div>

      <div className="flex-1 min-w-0">
        {/* Persona line */}
        <div className="flex items-center gap-1.5 flex-wrap mb-0.5">
          <span className="text-[10px] font-medium text-slate-300 truncate">
            {agent.persona?.race} · {agent.persona?.age}
          </span>
          <span className="text-[9px] text-slate-600 truncate max-w-[100px]">
            {agent.persona?.grc?.replace(" GRC", "").replace(" SMC", "")}
          </span>
          <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded border ${s.badge} ml-auto shrink-0`}>
            {agent.sentiment}
          </span>
        </div>

        {/* Reason */}
        {agent.reason && (
          <p className="text-[10px] text-slate-500 leading-relaxed line-clamp-2 italic">
            "{agent.reason}"
          </p>
        )}

        {/* Confidence + bet bar */}
        <div className="flex items-center gap-2 mt-1.5">
          <div className="flex-1 h-0.5 bg-slate-800 rounded-full overflow-hidden">
            <div
              className={`h-full ${s.bar} transition-all duration-500`}
              style={{ width: `${confidence}%`, opacity: 0.7 }}
            />
          </div>
          <span className="text-[9px] text-slate-600 font-mono shrink-0">{confidence}% conf</span>
          {bet > 0 && (
            <span className="text-[9px] text-slate-600 font-mono shrink-0">
              ${bet.toFixed(0)}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export default function AgentStreamFeed({ agentHistory, status, agentCount, totalAgents }) {
  const scrollRef = useRef(null);
  const wasAtBottomRef = useRef(true);

  // Track scroll position to decide if we should auto-scroll
  const handleScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    // "at bottom" means within 60px of the bottom
    wasAtBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 60;
  };

  // For newest-first list, always scroll to top when new agent arrives
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = 0;
  }, [agentHistory.length]);

  const supportCount = agentHistory.filter((a) => a.sentiment === "support").length;
  const rejectCount = agentHistory.filter((a) => a.sentiment === "reject").length;
  const neutralCount = agentHistory.filter((a) => a.sentiment === "neutral").length;
  const total = agentHistory.length || 1;

  return (
    <div className="flex flex-col h-full bg-slate-950 border-b border-slate-800">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-slate-800/70 shrink-0">
        <div className="flex items-center gap-2">
          <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest">
            Agent Stream
          </div>
          {status === "simulating" && (
            <div className="flex gap-0.5">
              <div className="w-1 h-1 rounded-full bg-emerald-500 animate-bounce" style={{ animationDelay: "0ms" }} />
              <div className="w-1 h-1 rounded-full bg-emerald-500 animate-bounce" style={{ animationDelay: "150ms" }} />
              <div className="w-1 h-1 rounded-full bg-emerald-500 animate-bounce" style={{ animationDelay: "300ms" }} />
            </div>
          )}
        </div>

        {/* Mini sentiment breakdown */}
        {agentHistory.length > 0 && (
          <div className="flex items-center gap-2 text-[9px] font-mono">
            <span className="text-emerald-400">{Math.round((supportCount / total) * 100)}% ↑</span>
            <span className="text-amber-400">{Math.round((neutralCount / total) * 100)}% ~</span>
            <span className="text-red-400">{Math.round((rejectCount / total) * 100)}% ↓</span>
          </div>
        )}
      </div>

      {/* Progress bar */}
      {status === "simulating" && (
        <div className="h-0.5 bg-slate-800 shrink-0">
          <div
            className="h-full bg-emerald-500/60 transition-all duration-300"
            style={{ width: `${totalAgents > 0 ? (agentCount / totalAgents) * 100 : 0}%` }}
          />
        </div>
      )}

      {/* Stream */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto divide-y divide-slate-800/40"
        style={{ scrollbarWidth: "none" }}
      >
        {agentHistory.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-slate-700 text-xs text-center px-4">
              {status === "idle"
                ? "Press Run Simulation to start"
                : "Waiting for agents…"}
            </div>
          </div>
        ) : (
          agentHistory.map((agent, i) => (
            <AgentCard key={`${agent.persona?.grc}-${i}`} agent={agent} isLatest={i === 0} />
          ))
        )}
      </div>

      {/* Footer count */}
      {agentHistory.length > 0 && (
        <div className="px-3 py-1.5 border-t border-slate-800/70 shrink-0 flex justify-between text-[9px] text-slate-700">
          <span>{agentCount}/{totalAgents} evaluated</span>
          <span>showing last {agentHistory.length}</span>
        </div>
      )}
    </div>
  );
}
