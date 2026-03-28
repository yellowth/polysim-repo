/**
 * Quick connectivity test for TinyFish (no OpenAI).
 *
 * Usage:
 *   cd policy-extract && TINYFISH_DEBUG=1 npm run test:tinyfish
 */
import "./loadEnv.js";
import { pingTinyFish } from "./tinyfish.js";

const result = await pingTinyFish();

console.log("\n=== TinyFish ping result ===");
console.log(JSON.stringify(result, null, 2));

if (result.ok) {
  console.log("\nOK: TinyFish API responded with HTTP success. Check tinyfishStatus / body if needed.");
  process.exit(0);
}

console.error("\nFAIL: See error / bodyPreview above. Fix TINYFISH_BASE_URL, key, or network.");
process.exit(1);
