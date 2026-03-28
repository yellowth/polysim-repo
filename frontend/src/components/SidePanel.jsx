import { useState } from "react";
import DemographicBreakdown from "./DemographicBreakdown";
import AgentVoice from "./AgentVoice";
import LeverControls from "./LeverControls";
import VotePrediction from "./VotePrediction";
import LiveMarketChart from "./LiveMarketChart";
import AgentStreamFeed from "./AgentStreamFeed";
import AgentDiscourse from "./AgentDiscourse";
import {
  Radio,
  ChevronRight,
  Search,
  CheckCircle2,
  Loader2,
  TrendingUp,
  Bot,
  MessageCircle,
  Users,
} from "lucide-react";

function PredictionLogLine({ entry }) {
  if (entry.type === "market_update") {
    return (
      <div className="flex gap-2 text-xs items-start">
        <TrendingUp className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
        <span className="text-emerald-300">
          Initial market set at {((entry.market?.market_price || 0) * 100).toFixed(1)}%
          {" "}
          ({entry.market?.call || "PENDING"})
        </span>
      </div>
    );
  }

  if (entry.type === "live_sentiment") {
    const data = entry.data || {};
    return (
      <div className="space-y-1.5">
        <div className="flex gap-2 text-xs items-start">
          <Search className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5 animate-pulse" />
          <span className="text-amber-300">
            TinyFish scraped {data.sources_scraped || 0} live sentiment source{data.sources_scraped === 1 ? "" : "s"}
            {" "}
            and adjusted the market by{" "}
            <span className={data.price_adjustment > 0 ? "text-emerald-400" : "text-red-400"}>
              {data.price_adjustment > 0 ? "+" : ""}
              {((data.price_adjustment || 0) * 100).toFixed(1)}%
            </span>
            .
          </span>
        </div>
        {(data.sentiments || []).slice(0, 5).map((s, i) => (
          <div key={i} className="flex gap-2 text-xs items-start ml-5">
            <CheckCircle2 className="w-3 h-3 text-amber-500 shrink-0 mt-0.5" />
            <span className="text-slate-400">
              [{s.source}] {s.text}
            </span>
          </div>
        ))}
      </div>
    );
  }

  if (entry.type === "discourse_start") {
    return (
      <div className="flex gap-2 text-xs items-start">
        <MessageCircle className="w-3.5 h-3.5 text-violet-400 shrink-0 mt-0.5" />
        <span className="text-violet-300">
          Discourse phase started — agents communicating over {entry.data?.total_rounds || 3} rounds.
        </span>
      </div>
    );
  }

  if (entry.type === "discourse_round_start") {
    return (
      <div className="flex gap-2 text-xs items-start">
        <MessageCircle className="w-3.5 h-3.5 text-violet-400 shrink-0 mt-0.5 animate-pulse" />
        <span className="text-violet-300">
          Discourse round {entry.round + 1} — agents posting, replying, and shifting positions…
        </span>
      </div>
    );
  }

  if (entry.type === "contagion_round") {
    return (
      <div className="flex gap-2 text-xs items-start">
        <Loader2 className="w-3.5 h-3.5 text-sky-400 shrink-0 mt-0.5" />
        <span className="text-sky-300">
          Market round {entry.round + 1} cleared at {((entry.market?.market_price || 0) * 100).toFixed(1)}%
          {entry.market?.discourse_stats ? ` (${entry.market.discourse_stats.messages_this_round} messages)` : ""}.
        </span>
      </div>
    );
  }

  if (entry.type === "vote_prediction") {
    const data = entry.data || {};
    return (
      <div className="flex gap-2 text-xs items-start">
        <Bot className="w-3.5 h-3.5 text-purple-400 shrink-0 mt-0.5" />
        <span className="text-purple-300">
          Final call: {data.call || "PENDING"} with {data.for_pct?.toFixed?.(1) ?? data.for_pct}% for and {data.against_pct?.toFixed?.(1) ?? data.against_pct}% against.
        </span>
      </div>
    );
  }

  return null;
}

export default function SidePanel({
  provisions, scenarioFrame, selectedGrc, grcSentiment,
  votePrediction, marketPrice, priceHistory, liveSentiment,
  onLeverChange, className,
  chartData, agentHistory, status, agentCount, totalAgents, contagionRound, predictionLog,
  discourseMessages, discourseRound,
}) {
  const grcData = selectedGrc ? grcSentiment[selectedGrc] : null;
  const [feedTab, setFeedTab] = useState("agents"); // agents | discourse

  return (
    <div className={`${className} flex flex-col border-l border-slate-800 overflow-hidden`}>

      {/* ── Live Market Chart (top ~35%) ─────────────────────────── */}
      <div className="shrink-0" style={{ height: "35%" }}>
        <LiveMarketChart
          chartData={chartData}
          marketPrice={marketPrice}
          status={status}
          contagionRound={contagionRound}
        />
      </div>

      {/* ── Tabbed feed: Agent Stream / Agent Discourse (middle ~35%) ── */}
      <div className="shrink-0 flex flex-col" style={{ height: "35%" }}>
        {/* Tab bar */}
        <div className="flex border-b border-slate-800/70 shrink-0">
          <button
            onClick={() => setFeedTab("agents")}
            className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-widest transition-colors ${
              feedTab === "agents"
                ? "text-emerald-400 border-b-2 border-emerald-500 bg-slate-900/50"
                : "text-slate-600 hover:text-slate-400"
            }`}
          >
            <Users className="w-3 h-3" />
            Agents ({agentCount})
          </button>
          <button
            onClick={() => setFeedTab("discourse")}
            className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-widest transition-colors ${
              feedTab === "discourse"
                ? "text-violet-400 border-b-2 border-violet-500 bg-slate-900/50"
                : "text-slate-600 hover:text-slate-400"
            }`}
          >
            <MessageCircle className="w-3 h-3" />
            Discourse ({discourseMessages?.length || 0})
          </button>
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-hidden">
          {feedTab === "agents" ? (
            <AgentStreamFeed
              agentHistory={agentHistory}
              status={status}
              agentCount={agentCount}
              totalAgents={totalAgents}
            />
          ) : (
            <AgentDiscourse
              discourseMessages={discourseMessages || []}
              discourseRound={discourseRound ?? -1}
              status={status}
            />
          )}
        </div>
      </div>

      {/* ── Scrollable details (bottom ~32%) ─────────────────────── */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">

        {/* Scenario frame */}
        {scenarioFrame && (
          <div className="space-y-1.5">
            <h3 className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest">
              Scenario
            </h3>
            <p className="text-sm font-medium text-slate-200 leading-snug">{scenarioFrame.title}</p>
            {scenarioFrame.context && (
              <p className="text-xs text-slate-500 leading-relaxed">{scenarioFrame.context}</p>
            )}
            <div className="grid grid-cols-2 gap-1.5 mt-2">
              <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-lg px-2.5 py-2">
                <p className="text-[10px] font-medium text-emerald-400 mb-0.5">YES</p>
                <p className="text-[10px] text-slate-400 leading-relaxed">{scenarioFrame.yes_definition}</p>
              </div>
              <div className="bg-red-500/5 border border-red-500/20 rounded-lg px-2.5 py-2">
                <p className="text-[10px] font-medium text-red-400 mb-0.5">NO</p>
                <p className="text-[10px] text-slate-400 leading-relaxed">{scenarioFrame.no_definition}</p>
              </div>
            </div>
          </div>
        )}

        {/* Policy Provisions */}
        <div>
          <h3 className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest mb-2">
            {scenarioFrame ? "Provisions" : "Policy Provisions"}
          </h3>
          <div className="space-y-1">
            {provisions.length === 0 && (
              <p className="text-xs text-slate-600 italic">Upload a policy to see provisions</p>
            )}
            {provisions.map((p, i) => (
              <div key={i} className="flex gap-2 text-xs text-slate-300 bg-slate-900/80 rounded-lg px-3 py-2 border border-slate-800/50">
                <ChevronRight className="w-3 h-3 text-emerald-500/60 shrink-0 mt-0.5" />
                <span>{p.title}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Prediction console */}
        {predictionLog?.length > 0 && (
          <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-2 font-mono">
            <h3 className="text-[10px] font-semibold text-amber-400 uppercase tracking-widest mb-2 flex items-center gap-1.5 font-sans">
              <Radio className="w-3 h-3" /> Prediction Console
            </h3>
            {predictionLog.map((entry, i) => (
              <PredictionLogLine key={i} entry={entry} />
            ))}
          </div>
        )}

        {/* Selected GRC Detail */}
        {grcData && (
          <>
            <div>
              <h3 className="text-[10px] font-semibold text-slate-500 uppercase tracking-widest mb-2 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-sky-500 shrink-0" />
                {selectedGrc}
              </h3>
              {grcData.market_price != null && (
                <div className="text-xs text-slate-400 mb-2">
                  Market price:{" "}
                  <span className={`font-mono font-medium ${grcData.market_price >= 0.5 ? "text-emerald-400" : "text-red-400"}`}>
                    {(grcData.market_price * 100).toFixed(1)}%
                  </span>
                </div>
              )}
              <DemographicBreakdown data={grcData} />
            </div>
            <AgentVoice agents={grcData.agents || []} />
          </>
        )}

        {/* Levers */}
        <LeverControls onLeverChange={onLeverChange} />

        {/* Vote Prediction */}
        {votePrediction && <VotePrediction data={votePrediction} />}
      </div>
    </div>
  );
}
