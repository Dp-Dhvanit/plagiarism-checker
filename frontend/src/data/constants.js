// ── Product identity ─────────────────────────────────────────────────────
// No text wordmark is shown in the UI — the sidebar uses a logo image
// instead (see layout/SideNav.jsx). These stay as internal fallbacks
// (page <title>, aria-labels) so removing the visible brand text didn't
// require touching every place a name might be read programmatically.
export const BRAND = "Analysis Terminal";
export const TERMINAL_NAME = "Overview";

// ── Palette shortcuts (mirror tailwind.config.js) ────────────────────────
export const C = {
  primary: "#7C6EEA",
  primaryContainer: "#7C6EEA",
  secondary: "#D97862",
  secondaryContainer: "#D97862",
  tertiary: "#6FAF7C",
  tertiaryContainer: "#6FAF7C",
  error: "#D6544A",
  outline: "#8F8A80",
  outlineVariant: "#C6BFAE",
  onSurface: "#2B2A27",
  onSurfaceVariant: "#6E6B64",
  surfaceHigh: "#E3DED0",
};

// ── Navigation ───────────────────────────────────────────────────────────
export const NAV = [
  { key: "dashboard", icon: "space_dashboard", label: "Overview" },
  { key: "text", icon: "description", label: "Text" },
  { key: "file", icon: "upload_file", label: "Upload File" },
  { key: "code", icon: "code", label: "Code" },
  { key: "image", icon: "image", label: "Image" },
  { key: "summary", icon: "summarize", label: "Summary" },
  { key: "history", icon: "history", label: "History" },
];

export const NAV_BY_KEY = Object.fromEntries(NAV.map((n) => [n.key, n]));

// ── Semantics ────────────────────────────────────────────────────────────
// Restrained, single-hue meanings: soft red for higher concern, soft green
// for lower concern, amber for genuinely uncertain. `neutral` is kept
// separate from `uncertain` on purpose — neutral is used for plain
// informational badges (a document-type tag, a content-type label), which
// have nothing to do with a score and shouldn't borrow the brand lavender
// used for buttons/navigation, nor the amber reserved for "the score sits
// in the middle and that itself is the finding".
export const TONE = {
  ai: { text: "text-secondary", bg: "bg-secondary-container/10", border: "border-secondary/35", hex: "#D97862" },
  human: { text: "text-tertiary", bg: "bg-tertiary-container/10", border: "border-tertiary/35", hex: "#6FAF7C" },
  uncertain: { text: "text-warning", bg: "bg-warning-container/10", border: "border-warning/35", hex: "#D99A3C" },
  neutral: { text: "text-primary", bg: "bg-primary-container/8", border: "border-primary/30", hex: "#7C6EEA" },
  muted: { text: "text-outline", bg: "bg-surface-high/60", border: "border-outline-variant/50", hex: "#8F8A80" },
  error: { text: "text-error", bg: "bg-error-container/10", border: "border-error/35", hex: "#D6544A" },
};

/** AI-likelihood score (0-100) → semantic tone. */
export function toneForScore(score) {
  if (score == null) return TONE.muted;
  if (score >= 60) return TONE.ai;
  if (score <= 40) return TONE.human;
  return TONE.uncertain;
}

/** Headline verdict → semantic tone (null for an unrecognised verdict). */
export function toneForVerdict(verdict) {
  if (verdict === "Likely AI") return TONE.ai;
  if (verdict === "Likely Human") return TONE.human;
  if (verdict === "Uncertain") return TONE.uncertain;
  return null;
}

/** Similarity/overlap (0-100) → semantic tone. High overlap is the flag. */
export function toneForSimilarity(pct) {
  if (pct == null) return TONE.muted;
  if (pct >= 50) return TONE.ai;
  if (pct >= 25) return TONE.uncertain;
  return TONE.human;
}

export const CONFIDENCE_TONE = {
  high: TONE.ai,
  High: TONE.ai,
  medium: TONE.uncertain,
  Medium: TONE.uncertain,
  low: TONE.muted,
  Low: TONE.muted,
};

export const IMAGE_CLASSIFICATION_META = {
  potentially_ai_generated: { label: "Potentially AI-generated", tone: TONE.ai },
  likely_real: { label: "Likely Real", tone: TONE.human },
  uncertain: { label: "Uncertain", tone: TONE.uncertain },
};

export const DOC_TYPE_META = {
  "Health Report": { icon: "monitor_heart" },
  "Business Report": { icon: "finance" },
  "Research Paper": { icon: "biotech" },
  Academic: { icon: "school" },
  "Code Document": { icon: "code_blocks" },
  "Dataset / Spreadsheet": { icon: "table_chart" },
  General: { icon: "description" },
};

export const LANG_ICON = {
  python: "code", javascript: "javascript", typescript: "code", java: "code",
  "c++": "code", c: "code", "c#": "code", php: "php", go: "code",
  ruby: "code", kotlin: "code", swift: "code", sql: "database", unknown: "code_off",
};

// Chart series colours — muted pastels drawn from the app's own accent
// family, so summary visuals read as part of the same clean system.
export const CHART_COLORS = [
  "#7C6EEA", "#6FAF7C", "#D99A3C", "#D97862",
  "#5FA8C7", "#9A8FF0", "#8CC49A", "#E0B968",
  "#E0947F", "#7FBFD6", "#B0A6F2", "#A9D4B3",
];

// ── Accepted inputs (kept in step with the backend) ──────────────────────
export const ACCEPT = {
  document: ".pdf,.ppt,.pptx,.docx,.txt",
  summary: ".pdf,.pptx,.ppt,.docx,.txt,.csv",
  image: ".jpg,.jpeg,.png,.webp",
  code: ".py,.js,.ts,.java,.cpp,.c,.cs,.php,.go,.rb,.kt,.swift,.sql,.pdf,.docx,.pptx,.ppt,.txt",
};

export const FORMAT_CHIPS = {
  document: ["PDF", "PPTX", "DOCX", "TXT"],
  summary: ["PDF", "PPTX", "DOCX", "TXT", "CSV"],
  image: ["JPG", "PNG", "WEBP"],
  code: ["PY", "JS", "TS", "JAVA", "C++", "C#", "PHP", "GO", "RB", "SQL", "PDF", "DOCX", "PPTX"],
};

export const SUPPORTED_LANGUAGES = [
  "Python", "JavaScript", "TypeScript", "Java", "C++", "C", "C#",
  "PHP", "Go", "Ruby", "Kotlin", "Swift", "SQL",
];
