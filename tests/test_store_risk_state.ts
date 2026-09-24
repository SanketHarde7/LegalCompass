/**
 * Frontend Risk-State Unit Tests for LegalCompass (useAppStore.ts)
 * 
 * Verifies:
 * 1. generateAuditGreeting() NEVER calls definitions/headings high-risk.
 * 2. setDocument() NEVER default-selects clause_1 when it's not risk-bearing.
 * 3. setDocument() selects first genuinely risk-bearing clause (HIGH -> MEDIUM -> any risk-bearing).
 * 4. If none are risk-bearing, selectedClauseId is null.
 * 5. isRiskBearingClause() accurately discriminates definitions/headings/boilerplate.
 */

import { useAppStore, isRiskBearingClause } from '../src/store/useAppStore';
import type { ContractDocument } from '../src/types/contract';

function assert(condition: boolean, message: string) {
  if (!condition) {
    console.error(`[FAIL] ${message}`);
    process.exit(1);
  }
  console.log(`  [PASS] ${message}`);
}

console.log('================================================================');
console.log('TESTING FRONTEND RISK-STATE AND STORE INITIALIZATION');
console.log('================================================================\n');

// --- TEST 1: isRiskBearingClause discriminator ---
console.log('--- TEST 1: isRiskBearingClause Helper ---');
assert(
  isRiskBearingClause({ isRiskBearing: false, clauseKind: 'DEFINITION', riskLevel: 'NEUTRAL' }) === false,
  'Pure definition is NOT risk-bearing'
);
assert(
  isRiskBearingClause({ isRiskBearing: false, clauseKind: 'HEADING', riskLevel: 'NEUTRAL' }) === false,
  'Heading-only is NOT risk-bearing'
);
assert(
  isRiskBearingClause({ isRiskBearing: false, clauseKind: 'BOILERPLATE', riskLevel: 'NEUTRAL' }) === false,
  'Boilerplate is NOT risk-bearing'
);
assert(
  isRiskBearingClause({ isRiskBearing: true, clauseKind: 'OPERATIVE', riskLevel: 'HIGH' }) === true,
  'Operative HIGH is risk-bearing'
);
assert(
  isRiskBearingClause({ isRiskBearing: true, clauseKind: 'OPERATIVE', riskLevel: 'MEDIUM' }) === true,
  'Operative MEDIUM is risk-bearing'
);
assert(
  isRiskBearingClause({ isRiskBearing: true, clauseKind: 'OPERATIVE', riskLevel: 'LOW' }) === true,
  'Operative LOW with isRiskBearing=true is risk-bearing'
);

// --- TEST 2: Contract with only definitions (no risk-bearing clauses) ---
console.log('\n--- TEST 2: Contract With Only Definitions (Zero Risk-Bearing) ---');
const pureDefinitionsDoc: ContractDocument = {
  sessionId: 'sess_def_only',
  filename: 'Definitions_Only.pdf',
  uploadTimestamp: new Date().toISOString(),
  overallFairnessScore: 95,
  clauses: [
    {
      id: 'def_1',
      title: '1.1 Services Defined',
      originalText: 'Services means software development.',
      plainSummary: 'Defines services.',
      riskLevel: 'NEUTRAL',
      category: 'OTHER',
      unfairnessScore: 5,
      clauseKind: 'DEFINITION',
      isRiskBearing: false,
    },
    {
      id: 'def_2',
      title: '1.2 Deliverables Defined',
      originalText: 'Deliverables means code.',
      plainSummary: 'Defines deliverables.',
      riskLevel: 'NEUTRAL',
      category: 'OTHER',
      unfairnessScore: 5,
      clauseKind: 'DEFINITION',
      isRiskBearing: false,
    },
  ],
};

useAppStore.getState().setDocument(pureDefinitionsDoc);
const state1 = useAppStore.getState();

assert(state1.selectedClauseId === null, 'selectedClauseId is NULL when no clause is risk-bearing (not def_1)');
const greeting1 = state1.chatMessages[0]?.content || '';
assert(!greeting1.toLowerCase().includes('services defined'), 'Greeting does not mention definition as high risk');
assert(!greeting1.toLowerCase().includes('deliverables defined'), 'Greeting does not mention definition 2 as high risk');
assert(greeting1.includes('No critical high-risk traps were detected'), 'Greeting states no critical traps detected');

// --- TEST 3: Contract with definitions first, then HIGH clause later ---
console.log('\n--- TEST 3: Contract with Definitions First, HIGH Clause Later ---');
const mixedDoc: ContractDocument = {
  sessionId: 'sess_mixed',
  filename: 'Vendor_Agreement.pdf',
  uploadTimestamp: new Date().toISOString(),
  overallFairnessScore: 40,
  clauses: [
    {
      id: 'clause_def_1',
      title: '1.1 Definitions',
      originalText: 'Services means work.',
      plainSummary: 'Defines services.',
      riskLevel: 'NEUTRAL',
      category: 'OTHER',
      unfairnessScore: 5,
      clauseKind: 'DEFINITION',
      isRiskBearing: false,
    },
    {
      id: 'clause_def_2',
      title: '1.2 Background IP',
      originalText: 'Pre-existing IP.',
      plainSummary: 'Defines IP.',
      riskLevel: 'NEUTRAL',
      category: 'OTHER',
      unfairnessScore: 5,
      clauseKind: 'DEFINITION',
      isRiskBearing: false,
    },
    {
      id: 'clause_indemnity_trap',
      title: '4.1 Uncapped Indemnification',
      originalText: 'Contractor defends and indemnifies without cap.',
      plainSummary: 'Unlimited indemnity liability.',
      riskLevel: 'HIGH',
      category: 'LIABILITY',
      unfairnessScore: 90,
      clauseKind: 'OPERATIVE',
      isRiskBearing: true,
    },
  ],
};

useAppStore.getState().setDocument(mixedDoc);
const state2 = useAppStore.getState();

assert(
  state2.selectedClauseId === 'clause_indemnity_trap',
  'selectedClauseId selects first HIGH risk-bearing clause (clause_indemnity_trap), skipping definitions'
);
const greeting2 = state2.chatMessages[0]?.content || '';
assert(greeting2.includes('4.1 Uncapped Indemnification'), 'Greeting correctly highlights the true HIGH clause');
assert(!greeting2.includes('1.1 Definitions'), 'Greeting never calls 1.1 Definitions high-risk');

// --- TEST 4: Contract with NO HIGH clauses, only MEDIUM operative clause ---
console.log('\n--- TEST 4: Contract with NO HIGH Clauses, Only MEDIUM Operative ---');
const mediumOnlyDoc: ContractDocument = {
  sessionId: 'sess_medium',
  filename: 'Balanced_Services.pdf',
  uploadTimestamp: new Date().toISOString(),
  overallFairnessScore: 65,
  clauses: [
    {
      id: 'heading_1',
      title: 'Section 1. Preliminary',
      originalText: 'Heading text.',
      plainSummary: 'Heading.',
      riskLevel: 'NEUTRAL',
      category: 'OTHER',
      unfairnessScore: 0,
      clauseKind: 'HEADING',
      isRiskBearing: false,
    },
    {
      id: 'medium_clause',
      title: '3.1 Payment Net 60',
      originalText: 'Invoices payable in 60 days.',
      plainSummary: 'Extended payment terms.',
      riskLevel: 'MEDIUM',
      category: 'PAYMENT',
      unfairnessScore: 45,
      clauseKind: 'OPERATIVE',
      isRiskBearing: true,
    },
  ],
};

useAppStore.getState().setDocument(mediumOnlyDoc);
const state3 = useAppStore.getState();

assert(
  state3.selectedClauseId === 'medium_clause',
  'selectedClauseId selects first MEDIUM risk-bearing clause, skipping non-risk heading'
);
const greeting3 = state3.chatMessages[0]?.content || '';
assert(!greeting3.toLowerCase().includes('high-risk areas include'), 'Greeting does NOT invent high-risk label');
assert(greeting3.includes('3.1 Payment Net 60'), 'Greeting mentions the moderate risk provision to review');
assert(!greeting3.includes('Section 1. Preliminary'), 'Greeting never mentions heading');

console.log('\n================================================================');
console.log('ALL FRONTEND RISK-STATE TESTS PASSED WITH ZERO FAILURES!');
console.log('================================================================');
