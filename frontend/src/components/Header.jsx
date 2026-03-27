import { Activity } from "lucide-react";

export default function Header() {
  return (
    <header className="flex items-center gap-3 px-6 py-3 border-b border-slate-800 bg-slate-950">
      <Activity className="w-6 h-6 text-emerald-400" />
      <h1 className="text-xl font-semibold tracking-tight">
        Poly<span className="text-emerald-400">sim</span>
      </h1>
      <span className="text-xs text-slate-500 ml-2">Prediction Market in Silico</span>
    </header>
  );
}
