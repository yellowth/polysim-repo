/** When true, TinyFish/OpenAI failures fall back to mock chunks / mock PolicyContext (dev only). */
export function allowPolicyExtractMock(): boolean {
  const v = process.env.POLICY_EXTRACT_ALLOW_MOCK?.trim().toLowerCase();
  return v === "1" || v === "true" || v === "yes";
}
