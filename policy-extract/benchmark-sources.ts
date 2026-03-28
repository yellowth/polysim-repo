/**
 * Run every registered discourse source once (sequential) and print a scoreboard.
 * Use this to decide TINYFISH_SOURCES=cna,reddit (comma-separated) in .env.
 *
 *   npx tsx benchmark-sources.ts "increase GST Singapore"
 */
import "./loadEnv.js";
import { getAllCandidateSources } from "./discourseSources.js";
import { getFetchTimeoutMs, runDiscourseSourceProbe } from "./tinyfish.js";

const topic = process.argv[2] || "increase GST Singapore";

console.log(`\nBenchmark policy topic: ${topic}`);
console.log(`Timeout per source: ${getFetchTimeoutMs()} ms\n`);

const sources = getAllCandidateSources(topic);
const rows: {
  id: string;
  ok: boolean;
  ms: number;
  chunks: number;
  error?: string;
}[] = [];

for (const s of sources) {
  process.stdout.write(`Running ${s.id}... `);
  const r = await runDiscourseSourceProbe(s);
  rows.push({
    id: r.sourceId,
    ok: r.ok,
    ms: r.durationMs,
    chunks: r.textChunks,
    error: r.error,
  });
  console.log(r.ok ? `OK (${r.durationMs}ms, ${r.textChunks} chunks)` : `FAIL — ${r.error ?? "unknown"}`);
}

console.log("\n--- Summary ---\n");
console.log(
  ["id".padEnd(14), "status".padEnd(8), "ms".padStart(8), "chunks".padStart(8)].join(" ")
);
for (const row of rows) {
  console.log(
    [
      row.id.padEnd(14),
      (row.ok ? "ok" : "fail").padEnd(8),
      String(row.ms).padStart(8),
      String(row.chunks).padStart(8),
    ].join(" ")
  );
}

const winners = rows.filter((r) => r.ok).map((r) => r.id);
if (winners.length) {
  console.log(`\nSuggested .env line:\n  TINYFISH_SOURCES=${winners.join(",")}\n`);
} else {
  console.log(
    "\nNo source returned chunks. Check API key, timeouts (TINYFISH_FETCH_TIMEOUT_MS), or try again later.\n"
  );
}
