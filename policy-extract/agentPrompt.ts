import type { PolicyContext } from "./types.js";

/**
 * Builds a single agent system-style prompt grounded in extracted discourse.
 */
export function buildAgentPrompt(persona: string, context: PolicyContext): string {
  const posLines =
    context.positive_narratives.length > 0
      ? context.positive_narratives.map((n) => `  - ${n}`).join("\n")
      : "  - (None listed.)";
  const negLines =
    context.negative_narratives.length > 0
      ? context.negative_narratives.map((n) => `  - ${n}`).join("\n")
      : "  - (None listed.)";
  const neu =
    context.neutral_facts.length > 0
      ? context.neutral_facts.map((n) => `* ${n}`).join("\n")
      : "* (No separate neutral facts listed.)";

  const opinions = context.raw_opinions.map((o) => `* "${o}"`).join("\n");

  return `You are a ${persona}.

Here is what people are saying:

Summary:
${context.summary}

Key arguments:

* Positive:
${posLines}

* Negative:
${negLines}

Neutral / factual points:
${neu}

What individuals are saying:

${opinions || "* (No snippets.)"}

Update your belief (0–1) and confidence.`;
}
