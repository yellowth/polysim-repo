import { getActiveDiscourseSources, type DiscourseSource } from "./discourseSources.js";
import { allowPolicyExtractMock } from "./envFlags.js";
import { formatErrorChain, maskSecret, tinyfishDebug } from "./tinyfishDebug.js";

/** Official production API: https://docs.tinyfish.ai */
const DEFAULT_BASE = "https://agent.tinyfish.ai";
const AUTOMATION_RUN_PATH = "/v1/automation/run";

/** Per-run HTTP timeout (ms). Sync runs should stay scoped; use env for slow networks. */
export function getFetchTimeoutMs(): number {
  const raw = process.env.TINYFISH_FETCH_TIMEOUT_MS;
  const n = raw ? parseInt(raw, 10) : NaN;
  if (Number.isFinite(n) && n >= 30_000) return n;
  return 300_000; // 5 min — stealth / heavy pages often need >3 min
}

type TinyFishRunResponse = {
  status?: string;
  result?: unknown;
  error?: { message?: string } | null;
};

function resultToTextChunks(result: unknown): string[] {
  if (result == null) return [];
  if (typeof result === "string") return [result];
  if (Array.isArray(result)) {
    return result.flatMap((x) => resultToTextChunks(x));
  }
  if (typeof result === "object") {
    const o = result as Record<string, unknown>;
    if (Array.isArray(o.chunks)) {
      return o.chunks.flatMap((c) => {
        if (typeof c === "string") return [c];
        if (c && typeof c === "object" && "text" in c)
          return [String((c as { text: unknown }).text)];
        return [];
      });
    }
    if (Array.isArray(o.extracted_texts)) {
      return o.extracted_texts.map(String);
    }
    if (Array.isArray(o.text_chunks)) {
      return o.text_chunks.map(String);
    }
    if (Array.isArray(o.snippets)) {
      return o.snippets.map(String);
    }
    const parts: string[] = [];
    for (const k of ["articles", "posts", "threads", "pages"]) {
      const arr = o[k];
      if (Array.isArray(arr)) {
        for (const item of arr) {
          if (item && typeof item === "object") {
            const it = item as Record<string, unknown>;
            const t = it.summary ?? it.text ?? it.title ?? it.snippet;
            if (typeof t === "string" && t.length > 10) parts.push(t);
          }
        }
      }
    }
    if (parts.length) return parts;
    return [JSON.stringify(result).slice(0, 50_000)];
  }
  return [];
}

/**
 * Mock web snippets when TinyFish is unavailable — keeps the pipeline usable for demos.
 */
export function getMockWebChunks(policy: string): string[] {
  const p = policy.trim() || "policy";
  return [
    `[Mock news] Coverage of "${p}" highlights fiscal sustainability and support packages for lower-income households.`,
    `[Mock forum] Users debate whether the change is fair to middle-class families and small businesses.`,
    `[Mock commentary] Analysts note timing relative to inflation and wage growth; unions ask for clearer offsets.`,
    `[Mock social] Short takes: some welcome long-term planning; others call it regressive without stronger transfers.`,
    `[Mock blog] Opinion: trade-off between revenue needs and cost-of-living optics in an election cycle.`,
  ];
}

async function runOneSource(
  runUrl: string,
  apiKey: string,
  source: DiscourseSource,
  timeoutMs: number
): Promise<{ ok: boolean; result?: unknown; label: string; error?: string; tinyfishStatus?: string }> {
  tinyfishDebug("runOneSource start", { id: source.id, url: source.url.slice(0, 100) });

  try {
    const response = await fetch(runUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": apiKey,
      },
      body: JSON.stringify({
        url: source.url,
        goal: source.goal,
        browser_profile: source.browser_profile,
      }),
      signal: AbortSignal.timeout(timeoutMs),
    });

    if (!response.ok) {
      const errText = await response.text().catch(() => "");
      tinyfishDebug(`runOneSource ${source.id} HTTP`, response.status, errText.slice(0, 400));
      return { ok: false, label: source.id, error: `HTTP ${response.status}` };
    }

    const data = (await response.json()) as TinyFishRunResponse;
    const tinyfishStatus = typeof data.status === "string" ? data.status : undefined;
    if (data.status === "COMPLETED" && data.result != null) {
      tinyfishDebug(`runOneSource ${source.id} COMPLETED`, {
        keys: typeof data.result === "object" && data.result ? Object.keys(data.result as object) : [],
      });
      tinyfishDebug(`runOneSource ${source.id} raw result`, JSON.stringify(data.result, null, 2).slice(0, 3000));
      return { ok: true, result: data.result, label: source.id, tinyfishStatus };
    }

    const failMsg =
      (data.error as { message?: string } | null)?.message ?? tinyfishStatus ?? "not completed";
    tinyfishDebug(`runOneSource ${source.id} not completed`, data.status, data.error);
    tinyfishDebug(`runOneSource ${source.id} full response`, JSON.stringify(data, null, 2).slice(0, 1500));
    return { ok: false, label: source.id, error: failMsg, tinyfishStatus };
  } catch (e) {
    const msg = formatErrorChain(e);
    console.warn(`[tinyfish] Source "${source.id}" failed:`, msg);
    tinyfishDebug(`runOneSource ${source.id} threw`, e);
    return { ok: false, label: source.id, error: msg };
  }
}

/**
 * Single-source probe (timing + chunk count) — used by benchmark-sources.ts.
 */
export async function runDiscourseSourceProbe(
  source: DiscourseSource,
  timeoutMs = getFetchTimeoutMs()
): Promise<{
  ok: boolean;
  sourceId: string;
  durationMs: number;
  textChunks: number;
  tinyfishStatus?: string;
  error?: string;
}> {
  const baseUrl = (process.env.TINYFISH_BASE_URL || DEFAULT_BASE).replace(/\/$/, "");
  const apiKey = process.env.TINYFISH_API_KEY || "";
  const runUrl = `${baseUrl}${AUTOMATION_RUN_PATH}`;

  if (!apiKey) {
    return {
      ok: false,
      sourceId: source.id,
      durationMs: 0,
      textChunks: 0,
      error: "TINYFISH_API_KEY missing",
    };
  }

  const t0 = Date.now();
  const r = await runOneSource(runUrl, apiKey, source, timeoutMs);
  const durationMs = Date.now() - t0;
  const textChunks =
    r.ok && r.result != null ? resultToTextChunks(r.result).length : 0;

  return {
    ok: r.ok,
    sourceId: source.id,
    durationMs,
    textChunks,
    tinyfishStatus: r.tinyfishStatus,
    error: r.error,
  };
}

/**
 * Parallel small-scope runs → merged text chunks for the LLM summarizer.
 */
export async function fetchWebData(policy: string): Promise<string[]> {
  const baseUrl = (process.env.TINYFISH_BASE_URL || DEFAULT_BASE).replace(/\/$/, "");
  const apiKey = process.env.TINYFISH_API_KEY || "";
  const runUrl = `${baseUrl}${AUTOMATION_RUN_PATH}`;
  const timeoutMs = getFetchTimeoutMs();

  if (!apiKey) {
    if (allowPolicyExtractMock()) {
      console.warn("[tinyfish] TINYFISH_API_KEY missing — using mock web chunks (POLICY_EXTRACT_ALLOW_MOCK=1).");
      return getMockWebChunks(policy);
    }
    throw new Error(
      "[tinyfish] TINYFISH_API_KEY is required. Set it in .env or use POLICY_EXTRACT_ALLOW_MOCK=1 for offline dev."
    );
  }

  const sources = getActiveDiscourseSources(policy);

  tinyfishDebug("fetchWebData", {
    runUrl,
    apiKey: maskSecret(apiKey),
    timeoutMs,
    sources: sources.map((s) => s.id),
    policyPreview: policy.slice(0, 80),
  });

  const results = await Promise.all(
    sources.map((s) => runOneSource(runUrl, apiKey, s, timeoutMs))
  );

  const chunks: string[] = [];
  for (const r of results) {
    if (!r.ok || r.result == null) continue;
    const parts = resultToTextChunks(r.result);
    for (const p of parts) {
      chunks.push(`[${r.label}] ${p}`);
    }
  }

  if (chunks.length > 0) {
    tinyfishDebug("fetchWebData merged", { totalChunks: chunks.length });
    tinyfishDebug("fetchWebData chunks preview", chunks.map((c, i) => `[${i}] ${c.slice(0, 200)}`).join("\n"));
    return chunks;
  }

  if (allowPolicyExtractMock()) {
    console.warn("[tinyfish] All discourse sources empty or failed — using mock web chunks (POLICY_EXTRACT_ALLOW_MOCK=1).");
    return getMockWebChunks(policy);
  }

  throw new Error(
    `[tinyfish] All discourse sources failed or returned no text for "${policy.slice(0, 80)}". ` +
      `Try: TINYFISH_FETCH_TIMEOUT_MS=360000, adjust TINYFISH_SOURCES (see npm run benchmark:sources), or check agent.tinyfish.ai status.`
  );
}

/**
 * Minimal POST to verify connectivity + API key (fast goal).
 * Use: TINYFISH_DEBUG=1 npm run test:tinyfish
 */
export async function pingTinyFish(): Promise<{
  ok: boolean;
  endpoint: string;
  httpStatus?: number;
  tinyfishStatus?: string;
  error?: string;
  bodyPreview?: string;
}> {
  const baseUrl = (process.env.TINYFISH_BASE_URL || DEFAULT_BASE).replace(/\/$/, "");
  const apiKey = process.env.TINYFISH_API_KEY || "";
  const endpoint = `${baseUrl}${AUTOMATION_RUN_PATH}`;

  if (!apiKey) {
    return { ok: false, endpoint, error: "TINYFISH_API_KEY missing" };
  }

  tinyfishDebug("pingTinyFish", { endpoint, apiKey: maskSecret(apiKey) });

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": apiKey,
      },
      body: JSON.stringify({
        url: "https://example.com",
        goal:
          'Return JSON only: { "ok": true, "page_heading": "first visible h1 or title text" }',
        browser_profile: "lite",
      }),
      signal: AbortSignal.timeout(90_000),
    });

    const text = await response.text();
    tinyfishDebug("ping response", { status: response.status, bodyLength: text.length });

    let parsed: Record<string, unknown> | null = null;
    try {
      parsed = JSON.parse(text) as Record<string, unknown>;
    } catch {
      tinyfishDebug("ping body (non-JSON)", text.slice(0, 400));
    }

    const tinyfishStatus =
      parsed && typeof parsed.status === "string" ? parsed.status : undefined;

    if (!response.ok) {
      return {
        ok: false,
        endpoint,
        httpStatus: response.status,
        tinyfishStatus,
        error: `HTTP ${response.status}`,
        bodyPreview: text.slice(0, 500),
      };
    }

    const completed = tinyfishStatus === "COMPLETED";
    return {
      ok: completed,
      endpoint,
      httpStatus: response.status,
      tinyfishStatus,
      error: completed ? undefined : (parsed?.error as { message?: string })?.message ?? tinyfishStatus,
      bodyPreview: text.slice(0, 300),
    };
  } catch (e) {
    return {
      ok: false,
      endpoint,
      error: formatErrorChain(e),
    };
  }
}
