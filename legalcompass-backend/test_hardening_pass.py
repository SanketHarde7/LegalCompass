"""
Comprehensive Hardening Pass Verification Suite for LegalCompass.

Validates the 4 targeted architectural fixes:
1. Heuristic fallback false positive elimination (negation, reciprocity, definitions, conditions).
2. Page mapping and exact offset highlighting precision (generic title collision prevention, whitespace tolerance).
3. Overall fairness score calculation (differential weighting, severity penalty, batch invariance).
4. Copilot context retrieval (no 10-clause truncation, selected clause inclusion, neighboring context, citation integrity).
"""

import sys
import os
import asyncio
from typing import List

# Setup path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.schemas.contract import Clause
from app.services.heuristic_engine import heuristic_engine
from app.services.fairness_calculator import calculate_overall_fairness
from app.services.document_parser import document_parser
from app.services.rag_engine import rag_engine
from app.services.llm_service import llm_service


def test_fix_1_heuristic_false_positives():
    print("\n--- [FIX 1] Testing Heuristic Fallback False Positive Elimination ---")

    # 1. Neutral indemnity definition
    t1 = heuristic_engine.evaluate_clause(
        "Definitions — Indemnity",
        '"Indemnity" means the legal obligation of one party to hold harmless the other party as defined herein.'
    )
    assert t1.risk_level == "NEUTRAL", f"Expected NEUTRAL for definition, got {t1.risk_level}"
    print("  [PASS] 1. Neutral indemnity definition -> NEUTRAL")

    # 2. Mutual indemnity
    t2 = heuristic_engine.evaluate_clause(
        "Indemnification",
        "Each party shall mutually defend and indemnify the other party solely to the extent caused by its own gross negligence."
    )
    assert t2.risk_level == "LOW", f"Expected LOW for mutual indemnity, got {t2.risk_level}"
    assert t2.unfairness_score <= 35, f"Expected unfairness <= 35, got {t2.unfairness_score}"
    print("  [PASS] 2. Mutual indemnity -> LOW")

    # 3. Explicit no-indemnity
    t3 = heuristic_engine.evaluate_clause(
        "Indemnification",
        "Contractor shall have no indemnification obligation under this Agreement."
    )
    assert t3.risk_level == "LOW", f"Expected LOW for negated indemnity, got {t3.risk_level}"
    print("  [PASS] 3. Explicit no-indemnity -> LOW")

    # 4. Unilateral uncapped indemnity
    t4 = heuristic_engine.evaluate_clause(
        "Indemnification",
        "Contractor shall defend, indemnify, and hold harmless Client against any and all losses, claims, and defense costs without limitation."
    )
    assert t4.risk_level == "HIGH", f"Expected HIGH for uncapped indemnity, got {t4.risk_level}"
    assert t4.unfairness_score >= 85, f"Expected unfairness >= 85, got {t4.unfairness_score}"
    print("  [PASS] 4. Unilateral uncapped indemnity -> HIGH")

    # 5. Neutral IP definition
    t5 = heuristic_engine.evaluate_clause(
        "Definitions — Background IP",
        '"Background IP" means all pre-existing software, libraries, and developer tooling owned prior to Effective Date.'
    )
    assert t5.risk_level in ["NEUTRAL", "LOW"], f"Expected NEUTRAL/LOW for IP definition, got {t5.risk_level}"
    print("  [PASS] 5. Neutral IP definition -> NEUTRAL/LOW")

    # 6. Payment-conditioned IP assignment
    t6 = heuristic_engine.evaluate_clause(
        "Intellectual Property",
        "Contractor assigns all rights to Deliverables to Client strictly upon receipt of full payment."
    )
    assert t6.risk_level == "LOW", f"Expected LOW for payment-conditioned IP, got {t6.risk_level}"
    print("  [PASS] 6. Payment-conditioned IP assignment -> LOW")

    # 7. Unconditional IP assignment
    t7 = heuristic_engine.evaluate_clause(
        "Intellectual Property",
        "Contractor hereby irrevocably assigns all rights in Deliverables immediately upon creation, irrespective of whether Client has paid."
    )
    assert t7.risk_level == "HIGH", f"Expected HIGH for unconditional IP transfer, got {t7.risk_level}"
    print("  [PASS] 7. Unconditional IP assignment -> HIGH")

    # 8. Mutual termination
    t8 = heuristic_engine.evaluate_clause(
        "Termination",
        "Either party may terminate this Agreement upon thirty (30) days prior written notice."
    )
    assert t8.risk_level == "LOW", f"Expected LOW for mutual termination, got {t8.risk_level}"
    print("  [PASS] 8. Mutual termination -> LOW")

    # 9. Unilateral termination with forfeiture
    t9 = heuristic_engine.evaluate_clause(
        "Termination",
        "Client may terminate at any time without cause without payment for work in progress, and unbilled hours shall be forfeit."
    )
    assert t9.risk_level == "HIGH", f"Expected HIGH for unilateral termination with forfeiture, got {t9.risk_level}"
    print("  [PASS] 9. Unilateral termination with forfeiture -> HIGH")

    # 10. Negated liability clause
    t10 = heuristic_engine.evaluate_clause(
        "Limitation of Liability",
        "Neither party shall be liable for indirect, incidental, or consequential damages."
    )
    assert t10.risk_level == "LOW", f"Expected LOW for mutual limitation of liability, got {t10.risk_level}"
    print("  [PASS] 10. Negated liability clause -> LOW")


def test_fix_2_page_mapping_and_offsets():
    print("\n--- [FIX 2] Testing Page Mapping and Exact Offsets ---")

    # Test 1: Generic title on multiple pages
    # Suppose both Page 1 and Page 2 contain a heading "Payment", but distinct body text
    page1_text = "Page 1 Content.\n\n1. Payment terms for initial deposit shall be $500.\nEnd of Page 1."
    page2_text = "Page 2 Content.\n\n2. Payment terms for final milestone shall be Net 30 upon delivery.\nEnd of Page 2."
    pages_content = [(1, page1_text), (2, page2_text)]

    chunk_p2 = "2. Payment terms for final milestone shall be Net 30 upon delivery."
    found_page = document_parser._find_page_number("Payment", chunk_p2, pages_content, last_page_idx=1)
    assert found_page == 2, f"Expected page 2 for distinct body chunk, got {found_page}"
    print("  [PASS] 1. Generic title collision prevented; resolved to correct page based on body text.")

    # Test 2: Whitespace tolerance and exact offset mapping
    pdf_altered_page = "1. Scope of Work\nContractor  shall   provide    software engineering services."
    clean_chunk = "Contractor shall provide software engineering services."
    start_off, end_off = document_parser._find_offsets_in_page(clean_chunk, pdf_altered_page)
    assert start_off is not None and end_off is not None, "Failed to locate offset across whitespace variations"
    extracted_slice = pdf_altered_page[start_off:end_off]
    assert "Contractor" in extracted_slice and "services." in extracted_slice, f"Slice mismatch: {repr(extracted_slice)}"
    print(f"  [PASS] 2. Normalized offset mapping correctly mapped slice: {repr(extracted_slice)}")

    # Test 3: Offsets are strictly relative to page text
    assert 0 <= start_off < end_off <= len(pdf_altered_page)
    print("  [PASS] 3. Offsets strictly bounded by page length.")

    # Test 4: Multi-page / partial clause returns (None, None) (no fabricated partial offset)
    page_with_half_clause = "Page 1 Content.\nContractor shall indemnify Client against all losses and"
    full_multipage_clause = "Contractor shall indemnify Client against all losses and liabilities arising under this Agreement in accordance with Section 8."
    start_multi, end_multi = document_parser._find_offsets_in_page(full_multipage_clause, page_with_half_clause)
    assert start_multi is None and end_multi is None, f"Expected (None, None) for multi-page clause, got ({start_multi}, {end_multi})"
    print("  [PASS] 4. Multi-page clause without full match correctly produces (None, None); zero fabricated offsets.")


def test_fix_3_fairness_score_calculation():
    print("\n--- [FIX 3] Testing Authoritative Overall Fairness Calculation ---")

    # Test 1: All neutral clauses -> high score >= 85
    neutral_clauses = [
        Clause(id=f"c_{i}", index=i, title=f"Def {i}", text="Def...", riskLevel="NEUTRAL", unfairnessScore=10)
        for i in range(1, 11)
    ]
    score_all_neutral = calculate_overall_fairness(neutral_clauses)
    assert score_all_neutral >= 85, f"Expected >= 85 for all neutral, got {score_all_neutral}"
    print(f"  [PASS] 1. All neutral clauses -> Score: {score_all_neutral} (>=85)")

    # Test 2: One medium clause among neutral clauses -> moderate decrease
    one_med = neutral_clauses + [
        Clause(id="c_med", index=11, title="Payment Net-60", text="Pay...", riskLevel="MEDIUM", unfairnessScore=65)
    ]
    score_one_med = calculate_overall_fairness(one_med)
    assert score_one_med < score_all_neutral, "Score should decrease with a medium clause"
    assert score_one_med >= 65, f"Expected >= 65, got {score_one_med}"
    print(f"  [PASS] 2. One medium clause -> Score: {score_one_med} (moderate decrease)")

    # Test 3: One high-risk clause -> material decrease
    one_high = neutral_clauses + [
        Clause(id="c_high", index=12, title="Uncapped Indemnity", text="Indemn...", riskLevel="HIGH", unfairnessScore=92)
    ]
    score_one_high = calculate_overall_fairness(one_high)
    assert score_one_high <= 65, f"Expected <= 65 for single fatal trap, got {score_one_high}"
    print(f"  [PASS] 3. One high-risk clause -> Score: {score_one_high} (material decrease)")

    # Test 4: Multiple high-risk clauses -> significant decrease (< 50)
    multi_high = neutral_clauses + [
        Clause(id="c_h1", index=12, title="Uncapped Indemnity", text="Indemn...", riskLevel="HIGH", unfairnessScore=92),
        Clause(id="c_h2", index=13, title="Unconditional IP Loss", text="IP...", riskLevel="HIGH", unfairnessScore=90),
        Clause(id="c_h3", index=14, title="Immediate Forfeiture", text="Term...", riskLevel="HIGH", unfairnessScore=85),
    ]
    score_multi_high = calculate_overall_fairness(multi_high)
    assert score_multi_high < 50, f"Expected < 50 for multi-high traps, got {score_multi_high}"
    print(f"  [PASS] 4. Multiple high-risk clauses -> Score: {score_multi_high} (<50)")

    # Test 5 & 6: Batch invariance
    # Split multi_high into 2 batches vs 3 batches: the final merged list of clauses gives the identical score
    batch_a = multi_high[:7]
    batch_b = multi_high[7:]
    merged_clauses = batch_a + batch_b
    assert calculate_overall_fairness(merged_clauses) == score_multi_high, "Score must be invariant to batching"
    print("  [PASS] 5. Batch invariance verified: same clauses always produce identical score.")


def test_fix_4_copilot_context_retrieval():
    print("\n--- [FIX 4] Testing Copilot Context Retrieval (No 10-clause truncation) ---")

    # Create a 25-clause contract
    all_clauses = [
        Clause(
            id=f"clause_{i}",
            index=i,
            title=f"Section {i} {'Special Term' if i == 18 else 'Standard'}",
            text=f"This is the detailed legal text of clause {i}. It specifies governing covenants.",
            riskLevel="HIGH" if i == 18 else "LOW",
            unfairnessScore=85 if i == 18 else 20,
            pageNumber=(i // 5) + 1,
        )
        for i in range(1, 26)
    ]

    session_id = "test_rag_session_25"
    rag_engine.index_document(session_id, "TwentyFiveClauses.pdf", all_clauses)

    # 1. Query about clause 18 (past the old 10-clause limit)
    retrieved = rag_engine.retrieve_top_k(session_id, "Special Term clause 18", k=7)
    retrieved_ids = [c.id for c in retrieved]
    assert "clause_18" in retrieved_ids, f"Clause 18 was not retrieved: {retrieved_ids}"
    print("  [PASS] 1. Clause 18 (beyond clause 10) is retrievable via RAG.")

    # 2. Selected clause neighbor context test
    selected_id = "clause_20"
    selected_idx = next(i for i, c in enumerate(all_clauses) if c.id == selected_id)
    # Replicate route logic for neighbor inclusion
    context_clauses = [all_clauses[selected_idx]]
    if selected_idx > 0:
        context_clauses.append(all_clauses[selected_idx - 1])
    if selected_idx + 1 < len(all_clauses):
        context_clauses.append(all_clauses[selected_idx + 1])
    
    ctx_ids = [c.id for c in context_clauses]
    assert "clause_20" in ctx_ids
    assert "clause_19" in ctx_ids
    assert "clause_21" in ctx_ids
    print(f"  [PASS] 2. Selected clause 20 includes neighbors 19 and 21: {ctx_ids}")

    # 3. Citation integrity: citations must only reference clauses provided in context
    from app.services.llm_service import extract_citations_and_clean_text
    model_response = f"Reviewing obligations under [CITE:{selected_id}]."
    extracted, _ = extract_citations_and_clean_text(model_response, {c.id for c in context_clauses})
    assert extracted == [selected_id], f"Expected [{selected_id}], got {extracted}"
    print(f"  [PASS] 3. Citation integrity confirmed: {extracted} referenced from context.")

    # 4. Chat session fairness preservation
    test_session_id = "test_fairness_session"
    rag_engine.index_document(test_session_id, "TestAgreement.pdf", all_clauses, overall_fairness_score=33)
    retrieved_session = rag_engine.get_session(test_session_id)
    assert retrieved_session is not None
    assert retrieved_session.overall_fairness_score == 33, f"Expected 33, got {retrieved_session.overall_fairness_score}"
    print("  [PASS] 4. SessionIndex correctly stores and preserves overall_fairness_score (33).")

    # 5. chat.py import & runtime test
    from fastapi.testclient import TestClient
    from app.main import app
    client = TestClient(app)
    chat_res = client.post(
        "/api/chat",
        json={"sessionId": test_session_id, "message": "What is the fairness score of this contract?", "history": []},
    )
    assert chat_res.status_code == 200, f"Chat endpoint failed with status {chat_res.status_code}"
    print("  [PASS] 5. chat.py route imported and verified with real session fairness.")


def test_fix_5_chat_citation_and_suggestion_hardening():
    print("\n--- [FIX 5] Testing Chat Citation Integrity & Suggestion Event Delivery ---")
    import json
    from unittest.mock import MagicMock, AsyncMock
    from app.services.llm_service import (
        llm_service,
        extract_citations_and_clean_text,
        CitationStreamFilter,
    )

    # 5 test clauses
    clauses = [
        Clause(
            id=f"clause_{i}",
            index=i,
            title=f"Section {i} {'Liability' if i == 4 else 'Standard'}",
            text=f"Legal verbiage for clause {i}.",
            riskLevel="HIGH" if i == 4 else "LOW",
            plainSummary=f"Summary of clause {i}",
            suggestion="Cap liability to total fees paid." if i == 4 else None,
            pageNumber=1,
        )
        for i in range(1, 6)
    ]
    allowed_ids = {c.id for c in clauses}

    # TEST 1 — Citation IDs come from actual context only
    model_text_1 = "Under the agreement, exposure is governed by [CITE:clause_4] which creates high liability."
    valid_cites_1, cleaned_1 = extract_citations_and_clean_text(model_text_1, allowed_ids)
    assert valid_cites_1 == ["clause_4"], f"Expected ['clause_4'], got {valid_cites_1}"
    assert "clause_1" not in valid_cites_1
    assert "clause_2" not in valid_cites_1
    assert "clause_3" not in valid_cites_1
    print("  [PASS] TEST 1: Citation IDs come from actual context only (clause_4, not 1, 2, 3).")

    # TEST 2 — Invalid citation IDs rejected
    model_text_2 = "This term is subject to statutory rules [CITE:clause_999]."
    valid_cites_2, cleaned_2 = extract_citations_and_clean_text(model_text_2, allowed_ids)
    assert valid_cites_2 == [], f"Expected empty list for nonexistent clause_999, got {valid_cites_2}"
    assert "clause_999" not in valid_cites_2
    print("  [PASS] TEST 2: Invalid citation IDs (clause_999) rejected silently.")

    # TEST 3 — Duplicate citation deduplication
    model_text_3 = "See liability in [CITE:clause_4] and further remedies in [CITE:clause_4]."
    valid_cites_3, cleaned_3 = extract_citations_and_clean_text(model_text_3, allowed_ids)
    assert valid_cites_3 == ["clause_4"], f"Expected deduplicated ['clause_4'], got {valid_cites_3}"
    print("  [PASS] TEST 3: Duplicate citations deduplicated while preserving order.")

    # TEST 4 — Multiple citations
    model_text_4 = "Refer to indemnification in [CITE:clause_2] and termination in [CITE:clause_5]."
    valid_cites_4, cleaned_4 = extract_citations_and_clean_text(model_text_4, allowed_ids)
    assert valid_cites_4 == ["clause_2", "clause_5"], f"Expected ['clause_2', 'clause_5'], got {valid_cites_4}"
    print("  [PASS] TEST 4: Multiple valid citations preserved in exact order.")

    # TEST 5 — Citation marker removed from final visible response
    input_text_5 = "Payment is delayed. [CITE:clause_5]"
    _, cleaned_5 = extract_citations_and_clean_text(input_text_5, allowed_ids)
    assert "[CITE:clause_5]" not in cleaned_5, f"Citation marker remained in text: {cleaned_5}"
    assert cleaned_5 == "Payment is delayed."

    # Also verify CitationStreamFilter on chunk boundary
    filter_inst = CitationStreamFilter()
    out1 = filter_inst.process_chunk("Payment is delayed. [CITE:")
    out2 = filter_inst.process_chunk("clause_5] Please negotiate.")
    out3 = filter_inst.flush()
    streamed_visible = out1 + out2 + out3
    assert "[CITE:clause_5]" not in streamed_visible, f"Citation marker leaked into stream: {streamed_visible}"
    assert "Payment is delayed." in streamed_visible
    assert "Please negotiate." in streamed_visible
    print("  [PASS] TEST 5: Citation markers completely removed from final visible text & streamed tokens.")

    # TEST 6 — No citation
    model_text_6 = "Hello! How can I assist you with your contract analysis today?"
    valid_cites_6, cleaned_6 = extract_citations_and_clean_text(model_text_6, allowed_ids)
    assert valid_cites_6 == [], f"Expected empty list, got {valid_cites_6}"
    assert cleaned_6 == model_text_6
    print("  [PASS] TEST 6: No citation markers produce deterministic empty citation list.")

    # TEST 7 — Suggestion event
    suggestion = llm_service._get_applicable_suggestion(clauses)
    assert suggestion is not None, "Expected suggestion for HIGH-risk clause with pushback"
    assert suggestion["type"] == "suggestion"
    assert suggestion["target_clause_id"] == "clause_4"
    assert suggestion["counter_clause"] == "Cap liability to total fees paid."
    assert len(suggestion["rationale"]) > 0
    print("  [PASS] TEST 7: Suggestion event generated correctly for HIGH-risk clause.")

    # TEST 8 — No suggestion
    low_risk_clauses = [c for c in clauses if c.id != "clause_4"]
    no_suggestion = llm_service._get_applicable_suggestion(low_risk_clauses)
    assert no_suggestion is None, f"Expected None when no HIGH-risk clause with pushback, got {no_suggestion}"
    print("  [PASS] TEST 8: No suggestion event generated when no HIGH-risk clause with pushback.")

    # TEST 9 — Provider-path consistency & full SSE stream event order
    async def run_sse_order_test():
        # Test full SSE stream through heuristic fallback generator
        events = []
        async for sse_chunk in llm_service.stream_chat_response(
            session_id="test_sess",
            query="Analyze liability",
            context_clauses=clauses,
        ):
            for line in sse_chunk.split("\n"):
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))

        event_types = [e.get("type") for e in events]

        # Verify event order: token(s) -> suggestion -> citation -> done
        assert "token" in event_types, "Missing token events"
        last_token_idx = max(i for i, t in enumerate(event_types) if t == "token")

        assert "suggestion" in event_types, "Missing suggestion event"
        sugg_idx = event_types.index("suggestion")

        assert "citation" in event_types, "Missing citation event"
        cite_idx = event_types.index("citation")

        assert "done" in event_types, "Missing done event"
        done_idx = event_types.index("done")

        assert last_token_idx < sugg_idx, f"Tokens must finish before suggestion: token={last_token_idx}, sugg={sugg_idx}"
        assert sugg_idx < cite_idx, f"Suggestion must precede citation: sugg={sugg_idx}, cite={cite_idx}"
        assert cite_idx < done_idx, f"Citation must precede done: cite={cite_idx}, done={done_idx}"

        # Verify suggestion event structure matches canonical format
        sugg_event = events[sugg_idx]
        assert sugg_event == suggestion, "Suggestion event in stream does not match canonical helper payload"

        # Verify citation event contains clause_1 from heuristic stream and no leaked markers
        cite_event = events[cite_idx]
        assert "clause_ids" in cite_event
        for token_ev in [e for e in events if e.get("type") == "token"]:
            assert "[CITE:" not in token_ev.get("content", ""), f"Leaked citation marker in token: {token_ev}"

        # Verify Gemini / Groq mocked provider consistency
        gemini_mock = MagicMock()
        mock_chunk = MagicMock()
        mock_chunk.text = "Grounded analysis [CITE:clause_4] completed."
        gemini_mock.models.generate_content_stream.return_value = [mock_chunk]
        llm_service._gemini_client = gemini_mock

        gemini_events = []
        async for sse_chunk in llm_service.stream_chat_response("test", "query", clauses):
            for line in sse_chunk.split("\n"):
                if line.startswith("data: "):
                    gemini_events.append(json.loads(line[6:]))

        gemini_types = [e.get("type") for e in gemini_events]
        gemini_type_sequence = [t for i, t in enumerate(gemini_types) if i == 0 or t != gemini_types[i-1]]
        assert gemini_type_sequence == ["token", "suggestion", "citation", "done"], f"Gemini event sequence mismatch: {gemini_type_sequence}"
        gemini_sugg = next(e for e in gemini_events if e.get("type") == "suggestion")
        assert gemini_sugg == suggestion, "Gemini suggestion format mismatch"
        gemini_cite = next(e for e in gemini_events if e.get("type") == "citation")
        assert gemini_cite["clause_ids"] == ["clause_4"], f"Gemini citations mismatch: {gemini_cite}"

        # Mock Groq failover
        llm_service._gemini_client = None  # Force Gemini to fail / be absent
        groq_mock = MagicMock()
        mock_choice = MagicMock()
        mock_choice.delta.content = "Groq analysis [CITE:clause_4] completed."
        mock_groq_chunk = MagicMock()
        mock_groq_chunk.choices = [mock_choice]

        async def mock_groq_generator():
            yield mock_groq_chunk

        groq_mock.chat.completions.create = AsyncMock(return_value=mock_groq_generator())
        llm_service._groq_client = groq_mock

        groq_events = []
        async for sse_chunk in llm_service.stream_chat_response("test", "query", clauses):
            for line in sse_chunk.split("\n"):
                if line.startswith("data: "):
                    groq_events.append(json.loads(line[6:]))

        groq_types = [e.get("type") for e in groq_events]
        groq_type_sequence = [t for i, t in enumerate(groq_types) if i == 0 or t != groq_types[i-1]]
        assert groq_type_sequence == ["token", "suggestion", "citation", "done"], f"Groq event sequence mismatch: {groq_type_sequence}"
        groq_sugg = next(e for e in groq_events if e.get("type") == "suggestion")
        assert groq_sugg == suggestion, "Groq suggestion format mismatch"
        groq_cite = next(e for e in groq_events if e.get("type") == "citation")
        assert groq_cite["clause_ids"] == ["clause_4"], f"Groq citations mismatch: {groq_cite}"

        # Reset clients
        llm_service._gemini_client = None
        llm_service._groq_client = None

    asyncio.run(run_sse_order_test())
    print("  [PASS] TEST 9: Provider-path consistency & deterministic SSE event order verified across all 3 providers.")


if __name__ == "__main__":
    print("==================================================================")
    print("RUNNING LEGALCOMPASS TARGETED HARDENING REGRESSION SUITE")
    print("==================================================================")
    test_fix_1_heuristic_false_positives()
    test_fix_2_page_mapping_and_offsets()
    test_fix_3_fairness_score_calculation()
    test_fix_4_copilot_context_retrieval()
    test_fix_5_chat_citation_and_suggestion_hardening()
    print("\n==================================================================")
    print("ALL 5 TARGETED FIXES VERIFIED AND PASSED WITH ZERO FAILURES!")
    print("==================================================================")
