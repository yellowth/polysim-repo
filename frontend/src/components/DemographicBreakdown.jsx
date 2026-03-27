export default function DemographicBreakdown({ data }) {
  // Group agents by race
  const byRace = {};
  (data.agents || []).forEach((a) => {
    const race = a.persona?.race || "Unknown";
    if (!byRace[race]) byRace[race] = { support: 0, neutral: 0, reject: 0, total: 0 };
    byRace[race][a.sentiment] += 1;
    byRace[race].total += 1;
  });

  return (
    <div className="space-y-2">
      {Object.entries(byRace).map(([race, counts]) => {
        const sPct = counts.total ? Math.round((counts.support / counts.total) * 100) : 0;
        return (
          <div key={race} className="flex items-center gap-3 text-sm">
            <span className="w-16 text-slate-400 text-xs">{race}</span>
            <div className="flex-1 h-3 bg-slate-800 rounded-full overflow-hidden flex">
              <div className="bg-emerald-500 h-full" style={{ width: `${sPct}%` }} />
              <div className="bg-amber-500 h-full" style={{ width: `${counts.total ? Math.round(counts.neutral / counts.total * 100) : 0}%` }} />
              <div className="bg-red-500 h-full" style={{ width: `${counts.total ? Math.round(counts.reject / counts.total * 100) : 0}%` }} />
            </div>
            <span className="text-xs text-slate-500 w-10 text-right">{sPct}%</span>
          </div>
        );
      })}
    </div>
  );
}
