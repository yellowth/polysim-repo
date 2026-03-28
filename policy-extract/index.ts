import "./loadEnv.js";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";

import { fetchWebData } from "./tinyfish.js";
import { structureDiscourse } from "./summarizer.js";
import { buildAgentPrompt } from "./agentPrompt.js";
import type { PolicyContext } from "./types.js";

export type { PolicyContext } from "./types.js";
export { fetchWebData, pingTinyFish, runDiscourseSourceProbe, getFetchTimeoutMs } from "./tinyfish.js";
export { getAllCandidateSources, getActiveDiscourseSources } from "./discourseSources.js";
export { structureDiscourse } from "./summarizer.js";
export { buildAgentPrompt } from "./agentPrompt.js";

/**
 * End-to-end: TinyFish (or mock) web chunks → OpenAI structured PolicyContext.
 */
export async function extractPolicyContext(policy: string): Promise<PolicyContext> {
  const chunks = await fetchWebData(policy);
  return structureDiscourse(policy, chunks);
}

async function main() {
  const topic = process.argv[2] || "increase GST Singapore";
  console.log(`Policy topic: ${topic}\n`);

  const context = await extractPolicyContext(topic);

  console.log("=== PolicyContext (JSON) ===");
  console.log(JSON.stringify(context, null, 2));

  const examplePersona =
    "35-year-old Chinese nurse living in Ang Mo Kio, middle income, follows local news and Reddit";
  const prompt = buildAgentPrompt(examplePersona, context);

  console.log("\n=== Example agent prompt ===");
  console.log(prompt);
}

const isMain =
  typeof process !== "undefined" &&
  process.argv[1] &&
  resolve(fileURLToPath(import.meta.url)) === resolve(process.argv[1]);

if (isMain) {
  main().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
