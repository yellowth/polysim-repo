import { Activity, RotateCcw } from "lucide-react";

export default function Header({ onReset }) {
  return (
    <header className="flex items-center gap-3 px-6 py-3 border-b border-slate-800 bg-slate-950">
      <Activity className="w-6 h-6 text-emerald-400" />
      <h1 className="text-xl font-semibold tracking-tight">
        Poly<span className="text-emerald-400">sim</span>
      </h1>
      <span className="text-xs text-slate-500 ml-2">Prediction Market in Silico</span>
      {onReset && (
        <button
          onClick={onReset}
          className="ml-auto flex items-center gap-1.5 text-xs text-slate-600 hover:text-slate-400 transition-colors"
        >
          <RotateCcw className="w-3.5 h-3.5" /> New simulation
        </button>
      )}
    </header>
  );
}
