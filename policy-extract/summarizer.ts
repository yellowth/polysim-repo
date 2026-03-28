import OpenAI from "openai";
import { allowPolicyExtractMock } from "./envFlags.js";
import type { PolicyContext } from "./types.js";

function createOpenAIClient() {
  return new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
}

function parsePolicyContext(raw: string): PolicyContext {
  const parsed = JSON.parse(raw) as Partial<PolicyContext>;
  return {
    summary: String(parsed.summary ?? ""),
    positive_narratives: Array.isArray(parsed.positive_narratives)
      ? parsed.positive_narratives.map(String)
      : [],
    negative_narratives: Array.isArray(parsed.negative_narratives)
      ? parsed.negative_narratives.map(String)
      : [],
    neutral_facts: Array.isArray(parsed.neutral_facts) ? parsed.neutral_facts.map(String) : [],
    raw_opinions: Array.isArray(parsed.raw_opinions) ? parsed.raw_opinions.map(String) : [],
    sentiment_score: typeof parsed.sentiment_score === "number" ? parsed.sentiment_score : 0,
    controversy_score:
      typeof parsed.controversy_score === "number" ? parsed.controversy_score : 0,
  };
}

/**
 * Turn raw page/snippet text into structured narratives + opinion snippets via OpenAI.
 */
export async function structureDiscourse(
  policy: string,
  textChunks: string[]
): Promise<PolicyContext> {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    if (allowPolicyExtractMock()) {
      console.warn("[summarizer] OPENAI_API_KEY missing — mock PolicyContext (POLICY_EXTRACT_ALLOW_MOCK=1).");
      return mockPolicyContext(policy, textChunks);
    }
    throw new Error(
      "[summarizer] OPENAI_API_KEY is required. Set it in .env or POLICY_EXTRACT_ALLOW_MOCK=1 for offline dev."
    );
  }

  const combined = textChunks.join("\n\n---\n\n").slice(0, 80_000);

  const system = `You are an analyst building an "information environment" for policy simulation.
Output valid JSON only. Be concise, diverse, non-repetitive. Ground claims in the provided text; you may infer tone of debate but do not invent specific statistics not implied by the text.

Requirements:
- summary: 2-4 sentences
- positive_narratives + negative_narratives + neutral_facts: together 5-10 items total (distribute as makes sense)
- raw_opinions: 10-20 short quoted-style lines (like real people — varied voice, no duplicates)
- sentiment_score: float -1 to 1 (overall lean of discourse)
- controversy_score: float 0 to 1 (how split / heated the discourse seems)`;

  const user = `Policy topic: ${policy}

Source text (from web extraction):
${combined}`;

  try {
    const completion = await createOpenAIClient().chat.completions.create({
      model: process.env.OPENAI_MODEL || "gpt-4o-mini",
      response_format: { type: "json_object" },
      messages: [
        { role: "system", content: system },
        { role: "user", content: user },
      ],
      temperature: 0.5,
    });

    const content = completion.choices[0]?.message?.content;
    if (!content) {
      if (allowPolicyExtractMock()) return mockPolicyContext(policy, textChunks);
      throw new Error("[summarizer] OpenAI returned empty content.");
    }
    return parsePolicyContext(content);
  } catch (e) {
    if (allowPolicyExtractMock()) {
      console.warn("[summarizer] OpenAI error — mock PolicyContext:", e instanceof Error ? e.message : e);
      return mockPolicyContext(policy, textChunks);
    }
    throw e instanceof Error ? e : new Error(String(e));
  }
}

function mockPolicyContext(policy: string, textChunks: string[]): PolicyContext {
  const preview = textChunks[0]?.slice(0, 200) || "(no web text)";
  return {
    summary: `Public discussion around "${policy}" mixes cost-of-living concerns with fiscal arguments. Below is a mock structure because OPENAI_API_KEY was missing or the call failed. Source preview: ${preview}…`,
    positive_narratives: [
      "Supports long-term fiscal sustainability if paired with offsets for vulnerable groups.",
    ],
    negative_narratives: [
      "Raises burden on households and SMEs already facing tight margins.",
    ],
    neutral_facts: [
      "Debate references timing, magnitude, and accompanying support measures.",
    ],
    raw_opinions: Array.from({ length: 12 }, (_, i) =>
      `[mock opinion ${i + 1}] People disagree on fairness; some focus on trust in how revenue is used.`
    ),
    sentiment_score: -0.1,
    controversy_score: 0.55,
  };
}
