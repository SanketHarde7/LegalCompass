/**
 * Regression Test Suite for LegalCompass Source-Location & Highlighting Pipeline.
 *
 * Covers:
 * TEST A — API MAPPING (backend snake_case & camelCase to frontend Clause/Document)
 * TEST B — VALID OFFSET (exact range highlighted when offsets are valid)
 * TEST C — INVALID OFFSET (negative startOffset rejected)
 * TEST D — END OUT OF RANGE (endOffset exceeding page length rejected)
 * TEST E — NORMALIZED MATCH (safe normalized mapping handles whitespace and newlines)
 * TEST F — UNSAFE FUZZY MATCH (incomplete clause is never partially highlighted)
 * TEST G — REPEATED TEXT (ambiguous duplicates are not arbitrarily highlighted)
 */

import { mapBackendClause, mapBackendContractDocument } from '../src/services/api';
import {
  validateOffsets,
  findSafeNormalizedSpan,
  resolveClauseHighlightSpan,
  normalizeWithMapping,
} from '../src/components/document/pageView/pageCanvasHelpers';
import type { Clause } from '../src/types/contract';

function assert(condition: boolean, message: string) {
  if (!condition) {
    console.error(`[FAIL] ${message}`);
    throw new Error(message);
  }
}

console.log('================================================================');
console.log('RUNNING SOURCE-LOCATION & HIGHLIGHTING REGRESSION TEST SUITE');
console.log('================================================================');

// -----------------------------------------------------------------------------
// TEST A — API MAPPING
// -----------------------------------------------------------------------------
console.log('\n--- TEST A: API Mapping (Backend snake_case & camelCase to Frontend Clause) ---');
const backendClauseA = {
  id: 'clause_17',
  text: 'Client may terminate this Agreement upon written notice.',
  page_number: 4,
  start_offset: 820,
  end_offset: 1240,
  risk_level: 'HIGH',
  category: 'TERMINATION',
  unfairness_score: 85,
  plain_english_summary: 'Client can terminate at will.',
  suggested_pushback: 'Require 30-day cure period.',
};

const frontendClauseA = mapBackendClause(backendClauseA);
assert(frontendClauseA.id === 'clause_17', 'Expected id clause_17');
assert(frontendClauseA.pageNumber === 4, 'Expected pageNumber 4');
assert(frontendClauseA.startOffset === 820, 'Expected startOffset 820');
assert(frontendClauseA.endOffset === 1240, 'Expected endOffset 1240');
assert(frontendClauseA.riskLevel === 'HIGH', 'Expected riskLevel HIGH');
console.log('  [PASS] Backend snake_case offsets correctly mapped to camelCase frontend Clause.');

// Also test camelCase backend variant
const backendClauseCamel = {
  id: 'clause_18',
  originalText: 'Mutual confidentiality obligations.',
  pageNumber: 5,
  startOffset: 100,
  endOffset: 250,
  riskLevel: 'LOW',
};
const frontendClauseCamel = mapBackendClause(backendClauseCamel);
assert(frontendClauseCamel.id === 'clause_18', 'Expected id clause_18');
assert(frontendClauseCamel.pageNumber === 5, 'Expected pageNumber 5');
assert(frontendClauseCamel.startOffset === 100, 'Expected startOffset 100');
assert(frontendClauseCamel.endOffset === 250, 'Expected endOffset 250');
console.log('  [PASS] Backend camelCase offsets correctly preserved.');

// Test documentTitle preservation in mapBackendContractDocument
const uploadResponseData = {
  session_id: 'sess_test_123',
  filename: 'Airtight_MSA.pdf',
  document_title: 'AIRTIGHT COMMERCIAL MASTER SERVICES AGREEMENT',
  overall_fairness_score: 38,
  total_pages: 8,
  clauses: [backendClauseA],
};
const mappedDoc = mapBackendContractDocument(uploadResponseData);
assert(mappedDoc.documentTitle === 'AIRTIGHT COMMERCIAL MASTER SERVICES AGREEMENT', 'Expected documentTitle preserved');
assert(mappedDoc.clauses[0].startOffset === 820, 'Expected clause startOffset in document');
console.log('  [PASS] ContractDocument preserves documentTitle and clause offsets.');

// -----------------------------------------------------------------------------
// TEST B — VALID OFFSET
// -----------------------------------------------------------------------------
console.log('\n--- TEST B: Valid Offset (Exact highlighted range) ---');
const clauseBText = 'Contractor shall indemnify Client against all third-party intellectual property infringement claims.';
const pageTextB = 'A'.repeat(500) + clauseBText + 'B'.repeat(2000 - 500 - clauseBText.length);
const clauseB: Clause = {
  id: 'clause_b',
  title: 'Indemnity',
  originalText: clauseBText,
  plainSummary: 'Indemnity clause',
  riskLevel: 'HIGH',
  category: 'LIABILITY',
  unfairnessScore: 88,
  pageNumber: 1,
  startOffset: 500,
  endOffset: 500 + clauseBText.length,
};

assert(pageTextB.length === 2000, `Expected page length 2000, got ${pageTextB.length}`);
assert(
  validateOffsets(clauseB.startOffset, clauseB.endOffset, pageTextB, clauseB.originalText),
  'Offsets should be validated as true'
);

const spanB = resolveClauseHighlightSpan(clauseB, pageTextB);
assert(spanB !== null, 'Expected highlight span to be resolved');
assert(spanB?.start === 500, `Expected start 500, got ${spanB?.start}`);
assert(spanB?.end === 500 + clauseBText.length, `Expected end ${500 + clauseBText.length}, got ${spanB?.end}`);
console.log(`  [PASS] Exact highlighted range [${spanB?.start}..${spanB?.end}] resolved via valid offsets.`);

// -----------------------------------------------------------------------------
// TEST C — INVALID OFFSET (Negative Start)
// -----------------------------------------------------------------------------
console.log('\n--- TEST C: Invalid Offset (startOffset = -1) ---');
const clauseC: Clause = {
  id: 'clause_c',
  title: 'Termination',
  originalText: 'Unrelated clause text that does not exist anywhere on this page.',
  plainSummary: 'Termination',
  riskLevel: 'HIGH',
  category: 'TERMINATION',
  unfairnessScore: 80,
  pageNumber: 1,
  startOffset: -1,
  endOffset: 500,
};

assert(!validateOffsets(clauseC.startOffset, clauseC.endOffset, pageTextB, clauseC.originalText), 'Negative offset must be rejected');
const spanC = resolveClauseHighlightSpan(clauseC, pageTextB);
assert(spanC === null, 'Clause with invalid offsets and missing text must NOT be highlighted');
console.log('  [PASS] Negative startOffset correctly rejected; no highlight applied.');

// -----------------------------------------------------------------------------
// TEST D — END OUT OF RANGE
// -----------------------------------------------------------------------------
console.log('\n--- TEST D: End Out of Range (endOffset = 1500 on 1000-char page) ---');
const pageTextD = 'X'.repeat(1000);
const clauseD: Clause = {
  id: 'clause_d',
  title: 'Payment',
  originalText: 'Payment shall be made within 90 days.',
  plainSummary: 'Payment',
  riskLevel: 'MEDIUM',
  category: 'PAYMENT',
  unfairnessScore: 60,
  pageNumber: 1,
  startOffset: 700,
  endOffset: 1500,
};

assert(
  !validateOffsets(clauseD.startOffset, clauseD.endOffset, pageTextD, clauseD.originalText),
  'Out of range endOffset must be rejected'
);
const spanD = resolveClauseHighlightSpan(clauseD, pageTextD);
assert(spanD === null, 'Out of bounds offsets must NOT highlight');
console.log('  [PASS] endOffset > page length correctly rejected; no highlight applied.');

// -----------------------------------------------------------------------------
// TEST E — NORMALIZED MATCH (Whitespace & Newline tolerance)
// -----------------------------------------------------------------------------
console.log('\n--- TEST E: Safe Normalized Match (Whitespace & Newline tolerance) ---');
const pageTextE = 'Header line.\n\nClient may\nset off any amount reasonably owed.\n\nFooter line.';
const clauseEText = 'Client may set off any amount reasonably owed.';
const clauseE: Clause = {
  id: 'clause_e',
  title: 'Setoff',
  originalText: clauseEText,
  plainSummary: 'Client setoff rights',
  riskLevel: 'HIGH',
  category: 'PAYMENT',
  unfairnessScore: 78,
  pageNumber: 1,
  // No offsets provided - testing Priority 2
  startOffset: undefined,
  endOffset: undefined,
};

const spanE = resolveClauseHighlightSpan(clauseE, pageTextE);
assert(spanE !== null, 'Safe normalized matching should have found the clause span across newlines');
const extractedE = pageTextE.slice(spanE!.start, spanE!.end);
assert(
  extractedE === 'Client may\nset off any amount reasonably owed.',
  `Expected exact page slice with newline, got: ${repr(extractedE)}`
);
console.log(`  [PASS] Safe normalized matching resolved exact span [${spanE!.start}..${spanE!.end}]: ${repr(extractedE)}`);

// -----------------------------------------------------------------------------
// TEST F — UNSAFE FUZZY MATCH (Incomplete clause must NOT highlight)
// -----------------------------------------------------------------------------
console.log('\n--- TEST F: Unsafe Fuzzy Match Rejection ---');
const pageTextF = 'Agreement text contains only: Client may set off... and nothing more.';
const fullClauseF = 'Client may set off any amount reasonably owed under any other contract between the parties.';
const clauseF: Clause = {
  id: 'clause_f',
  title: 'Setoff',
  originalText: fullClauseF,
  plainSummary: 'Full setoff clause',
  riskLevel: 'HIGH',
  category: 'PAYMENT',
  unfairnessScore: 75,
  pageNumber: 1,
};

const spanF = resolveClauseHighlightSpan(clauseF, pageTextF);
assert(spanF === null, 'Partial prefix must NOT trigger loose fuzzy highlighting');
console.log('  [PASS] Incomplete clause correctly rejected; zero runaway highlights.');

// -----------------------------------------------------------------------------
// TEST G — REPEATED TEXT (Ambiguous duplicates must not guess)
// -----------------------------------------------------------------------------
console.log('\n--- TEST G: Repeated Text (Ambiguous duplicate occurrences) ---');
const repeatedPhrase = 'Each party shall maintain adequate commercial general liability insurance.';
const pageTextG = `SECTION 1: ${repeatedPhrase}\n\nMiddle text here.\n\nSECTION 9: ${repeatedPhrase}\nEnd of document.`;

// G1: Without offsets, ambiguous match must return null (do not choose an arbitrary occurrence)
const clauseGNoOffsets: Clause = {
  id: 'clause_g1',
  title: 'Insurance',
  originalText: repeatedPhrase,
  plainSummary: 'Insurance',
  riskLevel: 'MEDIUM',
  category: 'LIABILITY',
  unfairnessScore: 50,
  pageNumber: 1,
};

const spanGNoOffsets = resolveClauseHighlightSpan(clauseGNoOffsets, pageTextG);
assert(spanGNoOffsets === null, 'Ambiguous repeated clause without offsets must NOT choose arbitrary occurrence');
console.log('  [PASS] Ambiguous repeated clause without offsets correctly returned NO highlight.');

// G2: With exact backend offsets pointing to SECTION 9 occurrence, exact offsets must be preferred
const sec9Start = pageTextG.lastIndexOf(repeatedPhrase);
const sec9End = sec9Start + repeatedPhrase.length;
const clauseGWithOffsets: Clause = {
  id: 'clause_g2',
  title: 'Insurance',
  originalText: repeatedPhrase,
  plainSummary: 'Insurance',
  riskLevel: 'MEDIUM',
  category: 'LIABILITY',
  unfairnessScore: 50,
  pageNumber: 1,
  startOffset: sec9Start,
  endOffset: sec9End,
};

const spanGWithOffsets = resolveClauseHighlightSpan(clauseGWithOffsets, pageTextG);
assert(spanGWithOffsets !== null, 'Exact offsets should disambiguate repeated text');
assert(spanGWithOffsets?.start === sec9Start, `Expected start ${sec9Start}, got ${spanGWithOffsets?.start}`);
assert(spanGWithOffsets?.end === sec9End, `Expected end ${sec9End}, got ${spanGWithOffsets?.end}`);
console.log(`  [PASS] Backend offsets successfully disambiguated repeated text to Section 9 [${sec9Start}..${sec9End}].`);

function repr(str: string): string {
  return JSON.stringify(str);
}

console.log('\n================================================================');
console.log('ALL TESTS A THROUGH G PASSED WITH ZERO FAILURES!');
console.log('================================================================');
