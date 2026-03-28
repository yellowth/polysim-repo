import { useEffect, useRef, useState } from "react";
import { MessageCircle, Reply, ThumbsUp, ThumbsDown, ArrowRight, Minus } from "lucide-react";

const SENTIMENT_COLORS = {
  support: { bg: "bg-emerald-500/10", border: "border-emerald-500/30", text: "text-emerald-400", dot: "bg-emerald-500" },
  reject: { bg: "bg-red-500/10", border: "border-red-500/30", text: "text-red-400", dot: "bg-red-500" },
  neutral: { bg: "bg-amber-500/10", border: "border-amber-500/30", text: "text-amber-400", dot: "bg-amber-500" },
};

const SHIFT_STYLES = {
  more_supportive: { icon: ThumbsUp, color: "text-emerald-400", label: "shifted supportive" },
  more_opposed: { icon: ThumbsDown, color: "text-red-400", label: "shifted opposed" },
  unchanged: { icon: Minus, color: "text-slate-500", label: "unchanged" },
  less_certain: { icon: Minus, color: "text-amber-400", label: "less certain" },
};

const ACTION_ICONS = {
  post: MessageCircle,
  reply: Reply,
  agree: ThumbsUp,
  disagree: ThumbsDown,
  lurk: Minus,
};

function DiscourseCard({ message, isLatest }) {
  const sc = SENTIMENT_COLORS[message.sentiment] || SENTIMENT_COLORS.neutral;
  const shift = SHIFT_STYLES[message.sentiment_shift] || SHIFT_STYLES.unchanged;
  const ShiftIcon = shift.icon;
  const ActionIcon = ACTION_ICONS[message.action] || MessageCircle;
  const agent = message.agent || {};
  const changed = message.sentiment !== message.previous_sentiment;

  return (
    <div
      className={`px-3 py-2.5 border-l-2 ${sc.border} ${isLatest ? "bg-slate-800/60" : "bg-transparent hover:bg-slate-800/30"} transition-all duration-300`}
      style={{ animation: isLatest ? "slideIn 0.3s ease-out" : "none" }}
    >
      {/* Header: agent identity + action badge */}
      <div className="flex items-center gap-1.5 mb-1">
        <div className={`w-2 h-2 rounded-full ${sc.dot} shrink-0`} />
        <span className="text-[10px] font-medium text-slate-300">
          {agent.race} · {agent.age}
        </span>
        <span className="text-[9px] text-slate-600 truncate max-w-[90px]">
          {(agent.grc || "").replace(" GRC", "").replace(" SMC", "")}
        </span>
        <span className="ml-auto flex items-center gap-1">
          <ActionIcon className="w-3 h-3 text-slate-500" />
          <span className="text-[9px] text-slate-600 capitalize">{message.action}</span>
        </span>
      </div>

      {/* Post text */}
      <p className="text-[11px] text-slate-300 leading-relaxed mb-1">
        {message.post}
      </p>

      {/* Reply if present */}
      {message.reply && (
        <div className="ml-3 pl-2 border-l border-slate-700 mb-1.5">
          {message.reply_to && (
            <p className="text-[9px] text-slate-600 italic truncate mb-0.5">
              Re: "{message.reply_to}"
            </p>
          )}
          <p className="text-[10px] text-slate-400 leading-relaxed">
            {message.reply}
          </p>
        </div>
      )}

      {/* Influence indicator */}
      <div className="flex items-center gap-2 mt-1">
        {changed && (
          <div className="flex items-center gap-1 text-[9px]">
            <span className={SENTIMENT_COLORS[message.previous_sentiment]?.text || "text-slate-500"}>
              {message.previous_sentiment}
            </span>
            <ArrowRight className="w-2.5 h-2.5 text-slate-600" />
            <span className={sc.text}>{message.sentiment}</span>
          </div>
        )}
        <div className={`flex items-center gap-0.5 text-[9px] ${shift.color} ${changed ? "" : ""}`}>
          <ShiftIcon className="w-2.5 h-2.5" />
          <span>{shift.label}</span>
        </div>
        <span className="text-[9px] text-slate-700 ml-auto font-mono">
          R{message.round + 1}
        </span>
      </div>

      {/* Influence reason */}
      {message.influence_reason && (
        <p className="text-[9px] text-slate-600 italic mt-1 leading-relaxed">
          {message.influence_reason}
        </p>
      )}
    </div>
  );
}

function RoundSummary({ round, messages }) {
  const shifts = { more_supportive: 0, more_opposed: 0, unchanged: 0, less_certain: 0 };
  const sentimentChanges = 0;
  let changed = 0;
  messages.forEach((m) => {
    shifts[m.sentiment_shift] = (shifts[m.sentiment_shift] || 0) + 1;
    if (m.sentiment !== m.previous_sentiment) changed++;
  });

  return (
    <div className="px-3 py-2 bg-slate-900/80 border-y border-slate-800/60 flex items-center gap-3">
      <span className="text-[10px] font-semibold text-sky-400 uppercase tracking-wider">
        Round {round + 1}
      </span>
      <span className="text-[9px] text-slate-500">
        {messages.length} messages
      </span>
      {changed > 0 && (
        <span className="text-[9px] text-amber-400">
          {changed} shifted
        </span>
      )}
      <div className="ml-auto flex items-center gap-2 text-[9px] font-mono">
        {shifts.more_supportive > 0 && <span className="text-emerald-400">+{shifts.more_supportive}</span>}
        {shifts.more_opposed > 0 && <span className="text-red-400">-{shifts.more_opposed}</span>}
      </div>
    </div>
  );
}

export default function AgentDiscourse({ discourseMessages, discourseRound, status }) {
  const scrollRef = useRef(null);
  const [filter, setFilter] = useState("all"); // all | shifted | replies

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = 0;
  }, [discourseMessages.length]);

  const filtered = discourseMessages.filter((m) => {
    if (filter === "shifted") return m.sentiment_shift !== "unchanged";
    if (filter === "replies") return m.action === "reply" || m.reply;
    return true;
  });

  const roundGroups = {};
  filtered.forEach((m) => {
    const r = m.round ?? 0;
    if (!roundGroups[r]) roundGroups[r] = [];
    roundGroups[r].push(m);
  });

  const totalShifted = discourseMessages.filter((m) => m.sentiment !== m.previous_sentiment).length;
  const totalMessages = discourseMessages.length;

  return (
    <div className="flex flex-col h-full bg-slate-950 border-b border-slate-800">
      {/* Header */}
      <div className="px-3 py-2 border-b border-slate-800/70 shrink-0">
        <div className="flex items-center justify-between mb-1.5">
          <div className="flex items-center gap-2">
            <MessageCircle className="w-3.5 h-3.5 text-violet-400" />
            <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest">
              Agent Discourse
            </span>
            {status === "simulating" && (
              <div className="flex gap-0.5">
                <div className="w-1 h-1 rounded-full bg-violet-500 animate-bounce" style={{ animationDelay: "0ms" }} />
                <div className="w-1 h-1 rounded-full bg-violet-500 animate-bounce" style={{ animationDelay: "150ms" }} />
                <div className="w-1 h-1 rounded-full bg-violet-500 animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            )}
          </div>
          {totalMessages > 0 && (
            <div className="flex items-center gap-2 text-[9px] font-mono">
              <span className="text-slate-500">{totalMessages} msgs</span>
              {totalShifted > 0 && <span className="text-amber-400">{totalShifted} shifted</span>}
            </div>
          )}
        </div>
        {/* Filter tabs */}
        <div className="flex gap-1">
          {[
            ["all", "All"],
            ["shifted", "Shifted"],
            ["replies", "Replies"],
          ].map(([key, label]) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className={`px-2 py-0.5 rounded text-[9px] font-medium transition-colors ${
                filter === key
                  ? "bg-violet-500/20 text-violet-300 border border-violet-500/30"
                  : "text-slate-600 hover:text-slate-400 border border-transparent"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Messages */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto divide-y divide-slate-800/30"
        style={{ scrollbarWidth: "none" }}
      >
        {filtered.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center px-4">
              <MessageCircle className="w-6 h-6 text-slate-800 mx-auto mb-2" />
              <p className="text-slate-700 text-xs">
                {status === "simulating" || status === "connecting"
                  ? "Agents will begin discussing after initial evaluation…"
                  : status === "complete"
                  ? "No discourse messages match this filter."
                  : "Run a simulation to see agent discourse."}
              </p>
            </div>
          </div>
        ) : (
          Object.keys(roundGroups)
            .sort((a, b) => Number(b) - Number(a))
            .map((roundKey) => (
              <div key={roundKey}>
                <RoundSummary round={Number(roundKey)} messages={roundGroups[roundKey]} />
                {roundGroups[roundKey].map((msg, i) => (
                  <DiscourseCard
                    key={`${roundKey}-${i}`}
                    message={msg}
                    isLatest={Number(roundKey) === discourseRound && i === roundGroups[roundKey].length - 1}
                  />
                ))}
              </div>
            ))
        )}
      </div>

      {/* Footer */}
      {discourseRound >= 0 && (
        <div className="px-3 py-1.5 border-t border-slate-800/70 shrink-0 flex justify-between text-[9px] text-slate-700">
          <span>Round {discourseRound + 1} of 3</span>
          <span>{filtered.length} shown</span>
        </div>
      )}
    </div>
  );
}
