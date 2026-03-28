/** Verbose TinyFish logs when TINYFISH_DEBUG=1 */
export function tinyfishDebugEnabled(): boolean {
  return process.env.TINYFISH_DEBUG === "1" || process.env.TINYFISH_DEBUG === "true";
}

export function tinyfishDebug(...args: unknown[]): void {
  if (tinyfishDebugEnabled()) {
    console.error("[tinyfish:debug]", ...args);
  }
}

export function formatErrorChain(err: unknown): string {
  if (!(err instanceof Error)) return String(err);
  const parts = [err.message];
  let c: unknown = err.cause;
  let depth = 0;
  while (c != null && depth < 5) {
    if (c instanceof Error) {
      parts.push(`cause: ${c.message}`);
      c = c.cause;
    } else {
      parts.push(`cause: ${String(c)}`);
      break;
    }
    depth += 1;
  }
  return parts.join(" → ");
}

/** Show first/last chars of a secret (never log full key). */
export function maskSecret(key: string): string {
  if (!key) return "(empty)";
  if (key.length <= 8) return `${key.slice(0, 2)}…(${key.length} chars)`;
  return `${key.slice(0, 4)}…${key.slice(-4)} (${key.length} chars)`;
}
