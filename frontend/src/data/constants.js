// ── Product identity ─────────────────────────────────────────────────────
// The Stitch references carry a placeholder wordmark; this keeps the real
// project name. Change these two strings to rebrand the whole shell.
export const BRAND = "AI Detective";
export const TERMINAL_NAME = "Core Terminal";

// ── Palette shortcuts (mirror tailwind.config.js) ────────────────────────
export const C = {
  primary: "#b4c5ff",
  primaryContainer: "#2563eb",
  secondary: "#ddb8ff",
  secondaryContainer: "#7c03d3",
  tertiary: "#b3d17a",
  tertiaryContainer: "#5b762a",
  error: "#ffb4ab",
  outline: "#8d90a0",
  outlineVariant: "#434655",
  onSurface: "#e5e1e4",
  onSurfaceVariant: "#c3c6d7",
  surfaceHigh: "#2a2a2c",
};

// ── Navigation ───────────────────────────────────────────────────────────
// Matches the sidebar in the Stitch references, plus the overview that the
// existing /dashboard endpoint backs.
export const NAV = [
  { key: "dashboard", icon: "space_dashboard", label: "Overview", code: "SEC_00" },
  { key: "text", icon: "description", label: "Text", code: "SEC_01" },
  { key: "file", icon: "upload_file", label: "Upload File", code: "SEC_02" },
  { key: "code", icon: "code", label: "Code", code: "SEC_03" },
  { key: "image", icon: "image", label: "Image", code: "SEC_04" },
  { key: "summary", icon: "summarize", label: "Summary", code: "SEC_05" },
  { key: "history", icon: "history", label: "History", code: "SEC_06" },
];

export const NAV_BY_KEY = Object.fromEntries(NAV.map((n) => [n.key, n]));

// ── Semantics ────────────────────────────────────────────────────────────
// Electric purple = machine signature. Cyber lime = human origin.
// Tech blue = indeterminate / system-neutral.
export const TONE = {
  ai: { text: "text-secondary", bg: "bg-secondary-container/15", border: "border-secondary/40", hex: "#ddb8ff" },
  human: { text: "text-tertiary", bg: "bg-tertiary-container/15", border: "border-tertiary/40", hex: "#b3d17a" },
  neutral: { text: "text-primary", bg: "bg-primary-container/15", border: "border-primary/40", hex: "#b4c5ff" },
  muted: { text: "text-outline", bg: "bg-surface-high/40", border: "border-outline-variant/40", hex: "#8d90a0" },
  error: { text: "text-error", bg: "bg-error-container/20", border: "border-error/40", hex: "#ffb4ab" },
};

/** AI-likelihood score (0-100) → semantic tone. */
export function toneForScore(score) {
  if (score == null) return TONE.muted;
  if (score >= 60) return TONE.ai;
  if (score <= 40) return TONE.human;
  return TONE.neutral;
}

/** Similarity/overlap (0-100) → semantic tone. High overlap is the flag. */
export function toneForSimilarity(pct) {
  if (pct == null) return TONE.muted;
  if (pct >= 50) return TONE.ai;
  if (pct >= 25) return TONE.neutral;
  return TONE.human;
}

export const CONFIDENCE_TONE = {
  high: TONE.ai,
  High: TONE.ai,
  medium: TONE.neutral,
  Medium: TONE.neutral,
  low: TONE.muted,
  Low: TONE.muted,
};

export const IMAGE_CLASSIFICATION_META = {
  potentially_ai_generated: { label: "Potentially AI-generated", tone: TONE.ai },
  likely_real: { label: "Likely Real", tone: TONE.human },
  uncertain: { label: "Uncertain", tone: TONE.neutral },
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

// Chart series colours — drawn from the Deep Space accents so the summary
// visuals read as part of the same system.
export const CHART_COLORS = [
  "#b4c5ff", "#ddb8ff", "#b3d17a", "#7c9cf5",
  "#c79bf0", "#8fb85c", "#5b8de8", "#9d7ad6",
  "#d4e89a", "#6f86c9", "#b58fe0", "#7fa844",
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
