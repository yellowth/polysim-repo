/**
 * Registry of TinyFish discourse sources (one URL + goal per run).
 * Tune via TINYFISH_SOURCES=cna,reddit_search (comma-separated). Run npm run benchmark:sources to compare.
 */

export type DiscourseSource = {
  id: string;
  url: string;
  goal: string;
  browser_profile: "lite" | "stealth";
};

/** Benchmarked: cna + reddit_search complete reliably; reddit (main feed) often hits client timeout. */
const DEFAULT_ACTIVE_IDS = ["cna", "reddit_search"] as const;

/** All sources you can benchmark; not all are enabled by default. */
export function getAllCandidateSources(policy: string): DiscourseSource[] {
  const topic = policy.trim() || "policy";
  const cnaQuery = topic.replace(/ /g, "+");
  const redditQ = encodeURIComponent(topic);

  const cna: DiscourseSource = {
    id: "cna",
    url: `https://www.channelnewsasia.com/search?q=${cnaQuery}`,
    goal: `Topic: "${topic}".

You are on a news search results page ONLY. Do not open article pages.

Extract up to 6 items relevant to this policy topic. Return JSON only:
{
  "articles": [
    {
      "title": "headline",
      "summary": "one sentence",
      "url": "optional url from listing"
    }
  ]
}

If nothing relevant, return { "articles": [] }.`,
    browser_profile: "lite",
  };

  const reddit: DiscourseSource = {
    id: "reddit",
    url: `https://www.reddit.com/r/singapore/`,
    goal: `Topic: "${topic}".

Look at the visible posts on this subreddit page. Do NOT use the search bar or navigate away.

Find any posts whose title relates to this topic. Extract up to 6 relevant ones. Return JSON only:
{
  "posts": [
    {
      "title": "post title",
      "summary": "one line takeaway from visible info",
      "sentiment": "positive" | "negative" | "neutral"
    }
  ]
}

If nothing relevant is visible, return { "posts": [] }.`,
    browser_profile: "stealth",
  };

  const redditSearch: DiscourseSource = {
    id: "reddit_search",
    url: `https://www.reddit.com/r/singapore/search/?q=${redditQ}&restrict_sr=1`,
    goal: `Topic: "${topic}".

You are on subreddit search results ONLY. Do not open post threads.

Extract up to 6 relevant posts. Return JSON only:
{
  "posts": [
    {
      "title": "post title",
      "summary": "one line takeaway",
      "sentiment": "positive" | "negative" | "neutral"
    }
  ]
}

If none, return { "posts": [] }.`,
    browser_profile: "lite",
  };

  const hwz: DiscourseSource = {
    id: "hwz",
    url: "https://forums.hardwarezone.com.sg/forums/eat-drink-man-woman.16/",
    goal: `Topic: "${topic}".

You are on a forum listing page ONLY. Do not open threads.

Find up to 6 relevant thread titles. Return JSON only:
{
  "threads": [
    {
      "title": "thread title",
      "summary": "one line",
      "sentiment": "positive" | "negative" | "neutral"
    }
  ]
}

If none, return { "threads": [] }.`,
    browser_profile: "lite",
  };

  return [cna, reddit, redditSearch, hwz];
}

function parseActiveIds(): string[] {
  const raw = process.env.TINYFISH_SOURCES?.trim();
  if (!raw) {
    return [...DEFAULT_ACTIVE_IDS];
  }
  return raw
    .split(",")
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);
}

/**
 * Sources used by fetchWebData — filtered by TINYFISH_SOURCES (default: cna,reddit_search).
 */
export function getActiveDiscourseSources(policy: string): DiscourseSource[] {
  const catalog = new Map(getAllCandidateSources(policy).map((s) => [s.id, s]));
  const wanted = parseActiveIds();
  const out: DiscourseSource[] = [];
  for (const id of wanted) {
    const s = catalog.get(id);
    if (s) out.push(s);
    else {
      console.warn(`[tinyfish] Unknown TINYFISH_SOURCES id "${id}" — skipped. Valid: ${[...catalog.keys()].join(", ")}`);
    }
  }
  if (out.length === 0) {
    console.warn("[tinyfish] TINYFISH_SOURCES produced no sources — falling back to cna, reddit_search.");
    return [catalog.get("cna")!, catalog.get("reddit_search")!];
  }
  return out;
}
