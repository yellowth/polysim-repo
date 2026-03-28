/** Structured discourse environment for downstream agent simulation */
export interface PolicyContext {
  summary: string;
  positive_narratives: string[];
  negative_narratives: string[];
  neutral_facts: string[];
  raw_opinions: string[];
  sentiment_score: number;
  controversy_score: number;
}
