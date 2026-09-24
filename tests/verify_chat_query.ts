import { sendChatMessage, SSEStreamParser } from '../src/services/api';

/**
 * End-to-end verification script for the specific user query:
 * "What are the 5 most materially risky operative provisions in this contract?"
 *
 * Verifies that streaming via sendChatMessage() (using SSEStreamParser under the hood)
 * properly parses all SSE chunks across stream reader intervals and returns an actual substantive
 * legal response instead of "Analysis completed."
 */

async function verifyQuery() {
  console.log('================================================================');
  console.log('VERIFYING CHAT QUERY AGAINST LIVE BACKEND VIA sendChatMessage()');
  console.log('Query: "What are the 5 most materially risky operative provisions in this contract?"');
  console.log('================================================================\n');

  const query = 'What are the 5 most materially risky operative provisions in this contract?';

  const tokensReceived: string[] = [];
  const citationsReceived: string[] = [];

  const contractContext = {
    filename: 'LegalCompass_Accuracy_V2_Stress_Test_Contract.pdf',
    overallFairnessScore: 18,
    clauses: [
      {
        id: 'clause_1',
        title: '3.1 Uncapped Contractor Indemnification',
        originalText:
          'Contractor shall irrevocably defend, indemnify, and hold harmless Client, its parent, affiliates, directors, and officers against any and all losses, claims, and liabilities arising out of the performance of Services without cap or limitation.',
        riskLevel: 'HIGH' as const,
        clauseKind: 'OPERATIVE' as const,
        isRiskBearing: true,
        unfairnessScore: 92,
        plainSummary: 'Contractor provides unlimited indemnity with no reciprocal protection.',
        suggestion: 'Limit indemnification to direct damages caused by gross negligence with mutual cap.',
      },
    ],
  };

  const message = await sendChatMessage(
    'verify_session_' + Date.now(),
    query,
    (token) => {
      tokensReceived.push(token);
    },
    (ids) => {
      citationsReceived.push(...ids);
    },
    [],
    'clause_1',
    contractContext
  );

  console.log('--- STREAMING SUMMARY ---');
  console.log(`Tokens received in stream: ${tokensReceived.length}`);
  console.log(`Total message content length: ${message.content.length} characters`);
  console.log(`Triggered / cited clauses: [${(message.triggeredClauseIds || []).join(', ')}]`);
  console.log(`Counter proposal: ${message.counterProposal ? 'YES' : 'NONE'}`);

  console.log('\n--- ACTUAL RESPONSE PREVIEW ---');
  console.log(message.content);

  // Verifications
  if (message.content === 'Analysis completed.') {
    console.error('\n[FAIL] Response was empty and defaulted to "Analysis completed."!');
    process.exit(1);
  }

  if (message.content.length < 30) {
    console.error(`\n[FAIL] Response was unexpectedly short (${message.content.length} chars).`);
    process.exit(1);
  }

  if (tokensReceived.length < 5) {
    console.error(`\n[FAIL] Too few tokens received (${tokensReceived.length} tokens).`);
    process.exit(1);
  }

  console.log('\n================================================================');
  console.log('SUCCESS: Actual substantive legal answer returned without bug!');
  console.log('Verified: sendChatMessage() did NOT fall back to "Analysis completed."');
  console.log('================================================================');
}

verifyQuery().catch((err) => {
  console.error('[ERROR]', err);
  process.exit(1);
});

