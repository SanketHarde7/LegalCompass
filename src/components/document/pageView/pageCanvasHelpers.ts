import type { Clause } from '../../../types/contract';

export interface TextSpan {
  start: number;
  end: number;
}

/**
 * Normalizes text by converting to lowercase and collapsing consecutive whitespace characters
 * into a single space, while recording the exact mapping from normalized character positions back to original text indices.
 */
export function normalizeWithMapping(text: string): { normalized: string; mapping: number[] } {
  const normChars: string[] = [];
  const mapping: number[] = [];
  let inSpace = false;

  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (/\s/.test(ch)) {
      if (!inSpace) {
        normChars.push(' ');
        mapping.push(i);
        inSpace = true;
      }
    } else {
      normChars.push(ch.toLowerCase());
      mapping.push(i);
      inSpace = false;
    }
  }

  return {
    normalized: normChars.join(''),
    mapping,
  };
}

/**
 * Verifies that a text slice from the page plausibly matches the clause text.
 * Uses normalized comparison to be tolerant of whitespace/newline variations.
 */
export function isPlausiblyMatching(pageSlice: string, clauseText: string): boolean {
  if (!pageSlice || !clauseText) return false;

  const normSlice = pageSlice.toLowerCase().replace(/\s+/g, ' ').trim();
  const normClause = clauseText.toLowerCase().replace(/\s+/g, ' ').trim();

  if (normSlice.length === 0 || normClause.length === 0) return false;

  // 1. Direct normalized equality
  if (normSlice === normClause) return true;

  // 2. Either starts with the other (e.g. multi-page clause truncated at page break or header inclusion)
  const minLen = Math.min(normSlice.length, normClause.length);
  const sampleLen = Math.min(minLen, 50);

  if (sampleLen >= 15) {
    const slicePrefix = normSlice.slice(0, sampleLen);
    const clausePrefix = normClause.slice(0, sampleLen);
    if (slicePrefix === clausePrefix) return true;
  }

  // 3. Significant word overlap for legal covenant bodies
  const sliceWords = normSlice.split(' ').filter((w) => w.length > 3);
  const clauseWords = normClause.split(' ').filter((w) => w.length > 3);
  if (sliceWords.length >= 3 && clauseWords.length >= 3) {
    const commonWords = sliceWords.filter((w) => clauseWords.includes(w));
    const overlapRatio = commonWords.length / Math.min(sliceWords.length, clauseWords.length);
    if (overlapRatio >= 0.7) return true;
  }

  return false;
}

/**
 * Validates backend-provided character offsets.
 * Requires:
 *  - Both offsets are integers
 *  - startOffset >= 0
 *  - endOffset > startOffset
 *  - endOffset <= pageText.length
 *  - pageText.slice(startOffset, endOffset) plausibly resembles clause.originalText
 */
export function validateOffsets(
  startOffset: number | undefined | null,
  endOffset: number | undefined | null,
  pageText: string,
  clauseText: string
): boolean {
  if (
    startOffset === undefined ||
    startOffset === null ||
    endOffset === undefined ||
    endOffset === null
  ) {
    return false;
  }

  if (
    !Number.isInteger(startOffset) ||
    !Number.isInteger(endOffset) ||
    startOffset < 0 ||
    endOffset <= startOffset ||
    endOffset > pageText.length
  ) {
    return false;
  }

  // Offset plausibility check: verify slice resembles clause originalText
  const slice = pageText.slice(startOffset, endOffset);
  return isPlausiblyMatching(slice, clauseText);
}

/**
 * Priority 2 Safe Normalized Matcher:
 * Requires that the complete normalized clause appears uniquely on the page.
 * If ambiguous (appears multiple times) or incomplete, returns null.
 */
export function findSafeNormalizedSpan(pageText: string, clauseText: string): TextSpan | null {
  if (!pageText || !clauseText) return null;

  const { normalized: normPage, mapping: pageMapping } = normalizeWithMapping(pageText);
  const normClause = normalizeWithMapping(clauseText).normalized.trim();

  // Guard: require substantive clause text to prevent accidental short matches
  if (normClause.length < 15 || normPage.length < 15) return null;

  // Check occurrences of the complete normalized clause on this page
  let occurrences = 0;
  let firstIdx = -1;
  let searchPos = 0;

  while (searchPos < normPage.length) {
    const found = normPage.indexOf(normClause, searchPos);
    if (found === -1) break;
    occurrences++;
    if (firstIdx === -1) firstIdx = found;
    searchPos = found + 1;

    // Test G: Repeated text / ambiguous match -> reject! Do not guess an arbitrary occurrence.
    if (occurrences > 1) {
      return null;
    }
  }

  // Test F: If full clause is not present (occurrences === 0), do NOT fuzzy match!
  if (occurrences === 1 && firstIdx !== -1) {
    const endNormIdx = firstIdx + normClause.length - 1;
    if (endNormIdx < pageMapping.length) {
      const origStart = pageMapping[firstIdx];
      const origEnd = pageMapping[endNormIdx] + 1;
      if (origStart >= 0 && origEnd > origStart && origEnd <= pageText.length) {
        return { start: origStart, end: origEnd };
      }
    }
  }

  return null;
}

/**
 * Determines exact source highlighting span for a clause on a specific page.
 * Strictly enforces Priority 1 -> Priority 2 -> Priority 3 (No Highlight).
 *
 * NOTE (Issue 7 - Multi-Page Clauses):
 * For clauses that span across page boundaries, pageNumber represents the starting page.
 * Highlighting is performed strictly for the reliable source range on that page.
 * Risky cross-page heuristics are avoided.
 */
export function resolveClauseHighlightSpan(
  clause: Clause,
  pageText: string
): TextSpan | null {
  if (!pageText || !clause) return null;

  // Priority 1: Valid backend startOffset/endOffset with plausibility check
  if (validateOffsets(clause.startOffset, clause.endOffset, pageText, clause.originalText)) {
    return {
      start: clause.startOffset as number,
      end: clause.endOffset as number,
    };
  }

  // Priority 2: Safe normalized exact source match
  const safeSpan = findSafeNormalizedSpan(pageText, clause.originalText);
  if (safeSpan) {
    return safeSpan;
  }

  // Priority 3: No reliable location -> DO NOT HIGHLIGHT
  return null;
}
