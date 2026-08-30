/**
 * Analysis stage scripts.
 *
 * Each entry describes a step the backend genuinely performs for that
 * endpoint — nothing here claims work that does not happen. `ms` is only a
 * pacing hint for the visual sequence; the run always waits on the real
 * request before it can finish (see lib/useAnalysisRun.js).
 *
 * Backend references:
 *   text     → POST /analyze          (classify → quality → scorer →
 *                                      AI-indicator check → similarity → log)
 *   document → POST /upload           (extract → build_units → detection
 *                                      pipeline → AI-indicator → similarity)
 *   code     → POST /detect-code[-text]
 *   image    → POST /analyze/image    (validate → multimodal visual analysis)
 *   summary  → POST /summarize        (extract → summarize → optional
 *                                      semantic enhancement)
 */

export const TEXT_STAGES = [
  { id: "read", label: "Preparing text", note: "Reading input stream", ms: 500 },
  { id: "features", label: "Extracting linguistic features", note: "Sentence segmentation & tokenizing", ms: 900 },
  { id: "patterns", label: "Analyzing writing patterns", note: "Perplexity & burstiness scoring", ms: 2200 },
  { id: "indicators", label: "Checking AI indicators", note: "Marker density & style uniformity", ms: 1800 },
  { id: "similarity", label: "Comparing similarity signals", note: "Matching against stored corpus", ms: 1600 },
  { id: "final", label: "Generating final assessment", note: "Combining signals", ms: 900 },
];

export const DOCUMENT_STAGES = [
  { id: "upload", label: "Transferring document", note: "Secure upload to analysis node", ms: 700 },
  { id: "extract", label: "Extracting document text", note: "Reading pages, slides & paragraphs", ms: 1600 },
  { id: "segment", label: "Segmenting content blocks", note: "Separating prose from code", ms: 1200 },
  { id: "patterns", label: "Analyzing writing patterns", note: "Perplexity & burstiness scoring", ms: 2400 },
  { id: "indicators", label: "Checking AI indicators", note: "Marker density & style uniformity", ms: 1800 },
  { id: "similarity", label: "Comparing similarity signals", note: "Matching against stored corpus", ms: 1600 },
  { id: "report", label: "Compiling analysis report", note: "Assembling result", ms: 900 },
];

export const CODE_STAGES = [
  { id: "read", label: "Reading source", note: "Buffering input", ms: 600 },
  { id: "blocks", label: "Extracting code blocks", note: "Locating fenced & inline regions", ms: 1100 },
  { id: "language", label: "Identifying programming language", note: "Syntax fingerprinting", ms: 1000 },
  { id: "structure", label: "Analyzing code structure", note: "Naming, docstrings & function shape", ms: 1900 },
  { id: "signals", label: "Evaluating AI characteristics", note: "Cleanness, edge cases, line uniformity", ms: 1700 },
  { id: "final", label: "Preparing result", note: "Aggregating chunk scores", ms: 800 },
];

export const IMAGE_STAGES = [
  { id: "load", label: "Loading image", note: "Transferring payload", ms: 700 },
  { id: "validate", label: "Validating image data", note: "Format, integrity & size checks", ms: 900 },
  { id: "inspect", label: "Inspecting visual characteristics", note: "Texture, lighting & structure", ms: 2400 },
  { id: "indicators", label: "Evaluating AI-generation indicators", note: "Artifacting & synthesis marks", ms: 2200 },
  { id: "confidence", label: "Calculating confidence", note: "Aggregating into a likelihood estimate", ms: 1000 },
];

export const SUMMARY_STAGES = [
  { id: "upload", label: "Transferring document", note: "Secure upload to analysis node", ms: 700 },
  { id: "extract", label: "Extracting readable content", note: "Pages, slides, rows & columns", ms: 1600 },
  { id: "classify", label: "Classifying document type", note: "Structure & vocabulary profile", ms: 1000 },
  { id: "points", label: "Ranking key passages", note: "Scoring sentences for salience", ms: 2000 },
  { id: "figures", label: "Extracting figures & series", note: "Detecting chartable data", ms: 1600 },
  { id: "compose", label: "Composing summary", note: "Assembling takeaways", ms: 1100 },
];

export const STAGES_BY_KIND = {
  text: TEXT_STAGES,
  document: DOCUMENT_STAGES,
  code: CODE_STAGES,
  image: IMAGE_STAGES,
  summary: SUMMARY_STAGES,
};

/** Header copy for each analysis surface. */
export const RUN_COPY = {
  text: { title: "Scanning your content", subtitle: "Processing linguistic structures", code: "SEC_ANALYZE" },
  document: { title: "Analyzing document", subtitle: "Deep content extraction protocol", code: "SYS_PROC" },
  code: { title: "Analyzing code", subtitle: "Static structure & authorship signals", code: "SEC_CODE" },
  image: { title: "Analyzing image", subtitle: "Visual authenticity assessment", code: "SYS_ACT" },
  summary: { title: "Summarizing document", subtitle: "Semantic extraction protocol", code: "SEC_SUM" },
};
