import DemographicBreakdown from "./DemographicBreakdown";
import AgentVoice from "./AgentVoice";
import LeverControls from "./LeverControls";
import VotePrediction from "./VotePrediction";
import LiveMarketChart from "./LiveMarketChart";
import AgentStreamFeed from "./AgentStreamFeed";
import { Radio, ChevronRight } from "lucide-react";

export default function SidePanel({
  provisions, scenarioFrame, selectedGrc, grcSentiment,
  votePrediction, marketPrice, priceHistory, liveSentiment,
  onLeverChange, className,
  // new props
  chartData, agentHistory, status, agentCount, totalAgents, contagionRound,
}) {
  const grcData = selectedGrc ? grcSentiment[selectedGrc] : null;

  return (
    <div className={`${className} flex flex-col border-l border-slate-800 overflow-hidden`}>

      {/* ── Live Market Chart (top ~38%) ─────────────────────────── */}
      <div className="shrink-0" style={{ height: "38%" }}>
        <LiveMarketChart
          chartData={chartData}
          marketPrice={marketPrice}
          status={status}
          contagionRound={contagionRound}
        />
      </div>

      {/* ── Agent Stream Feed (middle ~30%) ───────────────────────── */}
      <div className="shrink-0" style={{ height: "30%" }}>
        <AgentStreamFeed
          agentHistory={agentHistory}
          status={status}
          agentCount={agentCount}
          totalAgents={totalAgents}
        />
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

        {/* Live Sentiment (TinyFish) */}
        {liveSentiment && (
          <div className="bg-slate-900 rounded-xl p-3 border border-amber-500/20">
            <h3 className="text-[10px] font-semibold text-amber-400 uppercase tracking-widest mb-2 flex items-center gap-1.5">
              <Radio className="w-3 h-3" /> Live Sentiment
            </h3>
            <div className="text-[10px] text-slate-400">
              {liveSentiment.sources_scraped} sources scraped
              <span className={`ml-2 font-mono ${liveSentiment.price_adjustment > 0 ? "text-emerald-400" : "text-red-400"}`}>
                {liveSentiment.price_adjustment > 0 ? "+" : ""}{(liveSentiment.price_adjustment * 100).toFixed(1)}%
              </span>
            </div>
            {liveSentiment.sentiments?.slice(0, 3).map((s, i) => (
              <div key={i} className="mt-1.5 text-[10px] text-slate-500 truncate">
                <span className={`inline-block w-1.5 h-1.5 rounded-full mr-1.5 ${
                  s.sentiment === "positive" ? "bg-emerald-500" :
                  s.sentiment === "negative" ? "bg-red-500" : "bg-amber-500"
                }`} />
                [{s.source}] {s.text}
              </div>
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
