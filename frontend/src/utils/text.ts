const INLINE_CITATION_PATTERNS = [
  /[（(]?\s*\[?\s*Document\s*\d+\s*,\s*Source\s*\d+\s*\]?\s*[)）]?/gi,
  /[（(]?\s*Document\s*\d+\s*,\s*Source\s*\d+\s*[)）]?/gi,
  /[（(]?\s*\[?\s*Source\s*\d+\s*\]?\s*[)）]?/gi,
  /\[\s*Document\s*\d+\s*\]/gi,
];

export function stripInlineCitations(text: string): string {
  let cleaned = text;
  for (const pattern of INLINE_CITATION_PATTERNS) {
    cleaned = cleaned.replace(pattern, "");
  }

  return cleaned
    .replace(/[ \t]{2,}/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .replace(/\s+([，。！？；：,.!?;:])/g, "$1")
    .trim();
}
