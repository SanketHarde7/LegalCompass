import { SSEStreamParser } from '../src/services/api';

/**
 * Regression Test Suite for SSEStreamParser.
 * Validates persistent buffering, boundary handling (\n\n),
 * and event parsing across split fetch chunks.
 */

function runTests() {
  console.log('================================================================');
  console.log('RUNNING SSE STREAM PARSER REGRESSION TEST SUITE');
  console.log('================================================================\n');

  let passed = 0;
  let failed = 0;

  function assert(condition: boolean, msg: string) {
    if (!condition) {
      console.error(`  [FAIL] ${msg}`);
      failed++;
      throw new Error(msg);
    } else {
      console.log(`  [PASS] ${msg}`);
      passed++;
    }
  }

  // --- TEST 1: Intentionally split single SSE JSON token event across 2 chunks ---
  console.log('--- TEST 1: Single Token Event Split Across 2 Chunks ---');
  {
    const tokens: string[] = [];
    const parser = new SSEStreamParser({
      onToken: (t) => tokens.push(t),
    });

    const chunk1 = 'data: {"type": "token", "content": "What are the 5 ';
    const chunk2 = 'most materially risky provisions?"}\n\n';

    parser.feed(chunk1);
    assert(tokens.length === 0, 'No token emitted after partial first chunk');
    assert(parser.getBuffer().length > 0, 'Buffer preserved partial first chunk');

    parser.feed(chunk2);
    assert(tokens.length === 1, 'Exactly one token emitted after second chunk completes event');
    assert(tokens[0] === 'What are the 5 most materially risky provisions?', 'Token content matches expected assembled text');
    assert(parser.getBuffer() === '', 'Buffer is empty after complete event processed');
  }

  // --- TEST 2: Split right across the \n\n boundary ---
  console.log('\n--- TEST 2: Split Across \\n\\n Boundary ---');
  {
    const tokens: string[] = [];
    const parser = new SSEStreamParser({
      onToken: (t) => tokens.push(t),
    });

    const chunk1 = 'data: {"type": "token", "content": "Alpha"}\n';
    const chunk2 = '\ndata: {"type": "token", "content": " Beta"}\n\n';

    parser.feed(chunk1);
    assert(tokens.length === 0, 'Token not emitted before second newline of event boundary');

    parser.feed(chunk2);
    assert(tokens.length === 2, 'Both tokens emitted after delimiter completed');
    assert(tokens.join('') === 'Alpha Beta', 'Tokens correctly assembled in order');
  }

  // --- TEST 3: Citation event split across 2 chunks ---
  console.log('\n--- TEST 3: Citation Event Split Across Chunks ---');
  {
    let citations: string[] = [];
    const parser = new SSEStreamParser({
      onCitation: (ids) => {
        citations = ids;
      },
    });

    const chunk1 = 'data: {"type": "citation", "clause_ids": ["clause_1", ';
    const chunk2 = '"clause_4", "clause_8"]}\n\n';

    parser.feed(chunk1);
    assert(citations.length === 0, 'No citation emitted for partial chunk');

    parser.feed(chunk2);
    assert(citations.length === 3, 'Citation received with all 3 clause IDs');
    assert(citations[0] === 'clause_1' && citations[1] === 'clause_4' && citations[2] === 'clause_8', 'Clause IDs match');
  }

  // --- TEST 4: Counter-clause suggestion event split across chunks ---
  console.log('\n--- TEST 4: Suggestion Event Split Across Chunks ---');
  {
    let suggestion: string | undefined;
    const parser = new SSEStreamParser({
      onSuggestion: (s) => {
        suggestion = s;
      },
    });

    const chunk1 = 'data: {"type": "suggestion", "counter_clause": "Each party shall ';
    const chunk2 = 'mutually indemnify and hold harmless the other."}\n\n';

    parser.feed(chunk1);
    assert(suggestion === undefined, 'No suggestion emitted before event boundary');

    parser.feed(chunk2);
    assert(
      suggestion === 'Each party shall mutually indemnify and hold harmless the other.',
      'Full suggestion received after chunk 2'
    );
  }

  // --- TEST 5: Done event handling (both {"type": "done"} and [DONE]) ---
  console.log('\n--- TEST 5: Done Event Handling ---');
  {
    let doneCalledCount = 0;
    const parser = new SSEStreamParser({
      onDone: () => {
        doneCalledCount++;
      },
    });

    parser.feed('data: {"type": "done"}\n\n');
    assert(doneCalledCount === 1, 'onDone called for {"type": "done"}');

    parser.feed('data: [DONE]\n\n');
    assert(doneCalledCount === 2, 'onDone called for [DONE]');
  }

  // --- TEST 6: Flush trailing event without final newline ---
  console.log('\n--- TEST 6: Flush Trailing Event at Stream End ---');
  {
    const tokens: string[] = [];
    const parser = new SSEStreamParser({
      onToken: (t) => tokens.push(t),
    });

    parser.feed('data: {"type": "token", "content": "Trailing token without trailing newlines"}');
    assert(tokens.length === 0, 'Token kept in buffer before flush');

    parser.flush();
    assert(tokens.length === 1, 'Trailing token emitted upon flush()');
    assert(tokens[0] === 'Trailing token without trailing newlines', 'Token content matches');
    assert(parser.getBuffer() === '', 'Buffer cleared upon flush');
  }

  // --- TEST 7: Malformed event warning without discarding subsequent events ---
  console.log('\n--- TEST 7: Malformed JSON Event Resilience ---');
  {
    const tokens: string[] = [];
    const parser = new SSEStreamParser({
      onToken: (t) => tokens.push(t),
    });

    // Feed bad JSON followed by good JSON
    parser.feed('data: {malformed json}\n\n');
    parser.feed('data: {"type": "token", "content": "Recovered token"}\n\n');

    assert(tokens.length === 1, 'Subsequent valid event parsed despite preceding malformed event');
    assert(tokens[0] === 'Recovered token', 'Recovered token content is accurate');
  }

  // --- TEST 8: Full Realistic Multi-Chunk Stream ---
  console.log('\n--- TEST 8: Full Realistic Multi-Chunk Stream Assembly ---');
  {
    let assembled = '';
    const cited: string[] = [];
    let done = false;

    const parser = new SSEStreamParser({
      onToken: (t) => { assembled += t; },
      onCitation: (ids) => { cited.push(...ids); },
      onDone: () => { done = true; },
    });

    // Simulate arbitrary TCP fragment chunks of 15 characters each
    const rawStream = 
      'data: {"type": "token", "content": "**Top 5 Provisions**:\\n"}\n\n' +
      'data: {"type": "token", "content": "1. Indemnification"}\n\n' +
      'data: {"type": "token", "content": " [CITE:clause_1]"}\n\n' +
      'data: {"type": "citation", "clause_ids": ["clause_1"]}\n\n' +
      'data: {"type": "done"}\n\n';

    const chunkSize = 15;
    for (let i = 0; i < rawStream.length; i += chunkSize) {
      parser.feed(rawStream.slice(i, i + chunkSize));
    }
    parser.flush();

    assert(assembled === '**Top 5 Provisions**:\n1. Indemnification ', 'All fragmented tokens assembled seamlessly');
    assert(cited.length === 1 && cited[0] === 'clause_1', 'Citations assembled seamlessly across fragmentation');
    assert(done === true, 'Done event fired');
  }

  console.log('\n================================================================');
  console.log(`RESULTS: ${passed} passed, ${failed} failed`);
  if (failed === 0) {
    console.log('ALL SSE PARSER REGRESSION TESTS PASSED ✓');
  } else {
    console.log(`⚠ ${failed} TEST(S) FAILED`);
    process.exit(1);
  }
  console.log('================================================================');
}

runTests();
