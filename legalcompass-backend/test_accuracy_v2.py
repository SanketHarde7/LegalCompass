"""
Accuracy V2 Regression Test Suite for LegalCompass.

ZERO HARDCODING: All tests use synthetic inline text.
No clause numbers, section titles, specific phrases from any test contract,
or contract-specific exceptions.

Tests A-L cover:
- Structural classification (clause_kind, is_risk_bearing)
- Triple Gate for HIGH risk
- Mitigation detection
- Hidden trap detection in definitions
- Fairness calculator risk-bearing awareness
"""
import sys
import os
import asyncio

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.heuristic_engine import heuristic_engine
from app.services.fairness_calculator import calculate_overall_fairness
from app.services.rag_engine import rag_engine, is_global_risk_query, rank_risk_clauses, is_risk_bearing_clause
from app.schemas.contract import Clause


def test_a_pure_definition():
    """Test A: Pure definition → DEFINITION, is_risk_bearing=False, risk ≤ LOW."""
    result = heuristic_engine.evaluate_clause(
        title='Definitions',
        text='"Services" means all custom computer software development, architecture, code reviews, and related technical consulting services performed by Contractor pursuant to an executed Statement of Work.'
    )
    assert result.clause_kind == "DEFINITION", f"Expected DEFINITION, got {result.clause_kind}"
    assert result.is_risk_bearing is False, f"Expected is_risk_bearing=False, got {result.is_risk_bearing}"
    assert result.risk_level in ("NEUTRAL", "LOW"), f"Expected NEUTRAL/LOW, got {result.risk_level}"
    assert result.unfairness_score <= 15, f"Expected unfairness ≤ 15, got {result.unfairness_score}"
    print("  ✓ Test A: Pure definition classified correctly")


def test_b_heading_only():
    """Test B: Heading with minimal body → HEADING, is_risk_bearing=False."""
    result = heuristic_engine.evaluate_clause(
        title='3. INDEMNIFICATION',
        text='3. INDEMNIFICATION'
    )
    assert result.clause_kind == "HEADING", f"Expected HEADING, got {result.clause_kind}"
    assert result.is_risk_bearing is False, f"Expected is_risk_bearing=False, got {result.is_risk_bearing}"
    print("  ✓ Test B: Heading-only classified correctly")


def test_c_balanced_mutual_indemnity():
    """Test C: Balanced mutual indemnity with cap → risk ≤ MEDIUM."""
    result = heuristic_engine.evaluate_clause(
        title='Mutual Indemnification',
        text='Each party shall mutually indemnify and hold harmless the other party against third-party claims arising solely from its own breach or negligence, subject to the liability cap set forth in Section X. Total aggregate liability under this indemnity shall not exceed the total fees paid under this Agreement.'
    )
    assert result.is_risk_bearing is True, "Expected is_risk_bearing=True"
    assert result.risk_level in ("LOW", "MEDIUM"), f"Expected LOW/MEDIUM, got {result.risk_level}"
    assert result.unfairness_score <= 60, f"Expected unfairness ≤ 60, got {result.unfairness_score}"
    print("  ✓ Test C: Balanced mutual indemnity scored correctly")


def test_d_unilateral_uncapped_indemnity():
    """Test D: Unilateral uncapped indemnity → HIGH, unfairness ≥ 80."""
    result = heuristic_engine.evaluate_clause(
        title='Contractor Indemnification',
        text='Contractor shall irrevocably defend, indemnify, and hold harmless Client, its parent, affiliates, directors, and officers against any and all losses, claims, and liabilities arising out of the performance of Services without cap or limitation.'
    )
    assert result.is_risk_bearing is True, "Expected is_risk_bearing=True"
    assert result.risk_level == "HIGH", f"Expected HIGH, got {result.risk_level}"
    assert result.unfairness_score >= 80, f"Expected unfairness ≥ 80, got {result.unfairness_score}"
    assert len(result.risk_reasons) >= 2, f"Expected ≥ 2 risk_reasons, got {len(result.risk_reasons)}"
    print("  ✓ Test D: Unilateral uncapped indemnity scored HIGH correctly")


def test_e_definition_with_hidden_trap():
    """Test E: Definition containing hidden operative trap → is_risk_bearing=True, risk ≥ MEDIUM."""
    result = heuristic_engine.evaluate_clause(
        title='Definitions — IP Assignment',
        text='"Work Product" means all code, designs, and documentation. Contractor hereby irrevocably assigns all worldwide rights, title, and interest in Work Product immediately upon creation, irrespective of whether Client has paid.'
    )
    assert result.is_risk_bearing is True, f"Expected is_risk_bearing=True, got {result.is_risk_bearing}"
    assert result.risk_level in ("MEDIUM", "HIGH"), f"Expected MEDIUM/HIGH, got {result.risk_level}"
    print("  ✓ Test E: Definition with hidden trap detected correctly")


def test_f_pure_cross_reference():
    """Test F: Pure cross-reference → BOILERPLATE, is_risk_bearing=False."""
    result = heuristic_engine.evaluate_clause(
        title='Cross-Reference',
        text='As defined in Section 1 of this Agreement.'
    )
    assert result.clause_kind in ("BOILERPLATE", "HEADING"), f"Expected BOILERPLATE/HEADING, got {result.clause_kind}"
    assert result.is_risk_bearing is False, f"Expected is_risk_bearing=False, got {result.is_risk_bearing}"
    print("  ✓ Test F: Pure cross-reference classified correctly")


def test_g_recital():
    """Test G: Recital (WHEREAS clause) → RECITAL, is_risk_bearing=False."""
    result = heuristic_engine.evaluate_clause(
        title='Recitals',
        text='WHEREAS, Client desires to retain Contractor to perform professional software engineering services and Contractor agrees to perform such services on the terms set forth herein.'
    )
    assert result.clause_kind == "RECITAL", f"Expected RECITAL, got {result.clause_kind}"
    assert result.is_risk_bearing is False, f"Expected is_risk_bearing=False, got {result.is_risk_bearing}"
    assert result.risk_level in ("NEUTRAL", "LOW"), f"Expected NEUTRAL/LOW, got {result.risk_level}"
    print("  ✓ Test G: Recital classified correctly")


def test_h_mutual_termination():
    """Test H: Mutual termination with 30-day notice → risk ≤ LOW."""
    result = heuristic_engine.evaluate_clause(
        title='Termination for Convenience',
        text='Either party may terminate this Agreement for convenience upon thirty (30) days prior written notice to the other party. Upon termination, both parties shall settle all outstanding invoices within fifteen (15) business days.'
    )
    assert result.is_risk_bearing is True, "Expected is_risk_bearing=True"
    assert result.risk_level == "LOW", f"Expected LOW, got {result.risk_level}"
    print("  ✓ Test H: Mutual termination scored LOW correctly")


def test_i_unilateral_termination_with_forfeiture():
    """Test I: Unilateral termination with forfeiture → HIGH."""
    result = heuristic_engine.evaluate_clause(
        title='Client Termination Rights',
        text='Client may terminate at any time without notice or penalty. Upon termination, Contractor shall forfeit all unbilled hours and receive no compensation for work in progress.'
    )
    assert result.is_risk_bearing is True, "Expected is_risk_bearing=True"
    assert result.risk_level == "HIGH", f"Expected HIGH, got {result.risk_level}"
    assert result.unfairness_score >= 75, f"Expected unfairness ≥ 75, got {result.unfairness_score}"
    print("  ✓ Test I: Unilateral termination with forfeiture scored HIGH correctly")


def test_j_balanced_payment():
    """Test J: Standard balanced payment terms (Net-30) → risk ≤ LOW."""
    result = heuristic_engine.evaluate_clause(
        title='Payment Terms',
        text='All invoices shall be payable within thirty (30) days of receipt. Late payments shall accrue interest at 1.5% per month or the maximum rate permitted by law, whichever is less.'
    )
    assert result.is_risk_bearing is True, "Expected is_risk_bearing=True"
    assert result.risk_level == "LOW", f"Expected LOW, got {result.risk_level}"
    print("  ✓ Test J: Balanced payment terms scored LOW correctly")


def test_k_fairness_definitions_dont_mask_traps():
    """Test K: 2 HIGH + 10 definitions → fairness score < 50."""
    definition_clauses = []
    for i in range(1, 11):
        definition_clauses.append(Clause(
            id=f"clause_{i}",
            title=f"Definitions {i}",
            text=f'"Term {i}" means the definition of term {i} for purposes of this agreement.',
            riskLevel="NEUTRAL",
            unfairnessScore=10,
            clauseKind="DEFINITION",
            isRiskBearing=False,
            riskReasons=[],
        ))

    # Add 2 HIGH-risk clauses
    high_clauses = [
        Clause(
            id="clause_11",
            title="Uncapped Indemnification",
            text="Contractor shall indemnify without cap or limitation.",
            riskLevel="HIGH",
            unfairnessScore=92,
            clauseKind="OPERATIVE",
            isRiskBearing=True,
            riskReasons=["Material consequence", "Meaningful imbalance", "Insufficient mitigation"],
        ),
        Clause(
            id="clause_12",
            title="IP Assignment",
            text="Contractor assigns all IP immediately upon creation regardless of payment.",
            riskLevel="HIGH",
            unfairnessScore=88,
            clauseKind="OPERATIVE",
            isRiskBearing=True,
            riskReasons=["Material consequence", "Meaningful imbalance", "Insufficient mitigation"],
        ),
    ]

    all_clauses = definition_clauses + high_clauses
    score = calculate_overall_fairness(all_clauses)
    assert score < 50, f"Expected fairness < 50 (definitions shouldn't mask traps), got {score}"
    print(f"  ✓ Test K: Fairness score {score} — definitions don't mask traps")


def test_l_clean_contract_fair():
    """Test L: All LOW/balanced clauses → fairness score ≥ 75."""
    balanced_clauses = []
    for i in range(1, 9):
        balanced_clauses.append(Clause(
            id=f"clause_{i}",
            title=f"Standard Term {i}",
            text=f"Mutual obligation {i} with customary protections for both parties.",
            riskLevel="LOW",
            unfairnessScore=20,
            clauseKind="OPERATIVE",
            isRiskBearing=True,
            riskReasons=[],
        ))

    score = calculate_overall_fairness(balanced_clauses)
    assert score >= 75, f"Expected fairness ≥ 75 for clean contract, got {score}"
    print(f"  ✓ Test L: Fairness score {score} — clean contract scored fairly")


def test_stress_contract_regression():
    """Regression: Verify the stress-test contract structure still works correctly."""
    from app.services.document_parser import document_parser
    from app.schemas.contract import PageContent
    from app.services.llm_service import llm_service

    stress_text = """PROFESSIONAL SOFTWARE DEVELOPMENT AND DIGITAL SERVICES AGREEMENT

This Agreement is entered into on this 1st day of January, 2026, by and between Client Corp ("Client") and Contractor LLC ("Contractor").

RECITALS
WHEREAS, Client desires to retain Contractor to perform professional software engineering services;
WHEREAS, Contractor agrees to perform such services on the terms set forth herein.
NOW, THEREFORE, the parties agree as follows:

1. DEFINITIONS AND ORDER OF PRECEDENCE
1.1 "Services" means all custom computer software development, architecture, code reviews, and related technical consulting services performed by Contractor pursuant to an executed Statement of Work.
1.2 "Deliverables" means all software code, scripts, technical specifications, and documentation authored or prepared specifically for Client by Contractor under this Agreement.
1.3 "Background IP" means all pre-existing software libraries, architectural frameworks, developer tooling, proprietary algorithms, and trade secrets owned or licensed by Contractor prior to the Effective Date.
1.4 Order of Precedence — Invoicing Carve-Out
In the event of any conflict or inconsistency between the terms and conditions of this Agreement and any Purchase Order, vendor invoice, or order form issued by Client, the terms of the Purchase Order or invoice shall supersede and strictly control with respect to payment timelines, dispute procedures, and limitation of contractor liability.
1.5 "Acceptance" means formal written sign-off executed by Client's authorized technical representative verifying that the Deliverables conform to specifications.

2. TERM; RENEWAL
2.1 Term. This Agreement commences on the Effective Date and continues for an initial term of twelve (12) months unless terminated earlier in accordance with Section 4.
2.2 Renewal. This Agreement automatically renews for successive one-year terms unless either party provides written notice of non-renewal at least sixty (60) days prior to the expiration of the then-current term.

3. INDEMNIFICATION; INTELLECTUAL PROPERTY
3.1 Uncapped Contractor Indemnification. Contractor shall irrevocably defend, indemnify, and hold harmless Client, its parent, affiliates, directors, and officers against any and all losses, claims, and liabilities arising out of the performance of Services without cap or limitation.
3.2 Immediate IP Assignment. Contractor hereby irrevocably assigns and transfers all worldwide rights, title, and interest in and to all Deliverables and inventions immediately upon creation, irrespective of whether Client has paid the corresponding invoices.
"""

    pages_content = [(1, stress_text)]
    clauses = document_parser.parse_clauses(stress_text, pages_content)
    page_objects = [PageContent(pageNumber=1, text=stress_text)]

    doc = llm_service._heuristic_analysis(
        session_id="test_v2_sess",
        filename="stress_test.pdf",
        initial_clauses=clauses,
        page_objects=page_objects,
        document_title=document_parser.document_title,
    )

    # Verify structural classification
    for c in doc.clauses:
        if "1.1" in c.title or "1.2" in c.title or "1.3" in c.title or "1.5" in c.title:
            # Definitions should be DEFINITION / non-risk-bearing
            assert c.clause_kind == "DEFINITION", f"Clause {c.id} ({c.title}): expected DEFINITION, got {c.clause_kind}"
            assert c.is_risk_bearing is False, f"Clause {c.id} ({c.title}): expected is_risk_bearing=False"
            assert c.risk_level in ("NEUTRAL", "LOW"), f"Clause {c.id} ({c.title}): expected NEUTRAL/LOW, got {c.risk_level}"
            print(f"    ✓ {c.title}: {c.clause_kind}, risk_bearing={c.is_risk_bearing}, risk={c.risk_level}")

    # Verify 1.4 (Order of Precedence) is OPERATIVE and HIGH
    clause_1_4 = next((c for c in doc.clauses if "1.4" in c.title or "Precedence" in c.title), None)
    if clause_1_4:
        assert clause_1_4.clause_kind == "OPERATIVE", f"1.4 expected OPERATIVE, got {clause_1_4.clause_kind}"
        assert clause_1_4.is_risk_bearing is True, "1.4 expected is_risk_bearing=True"
        assert clause_1_4.risk_level == "HIGH", f"1.4 expected HIGH, got {clause_1_4.risk_level}"
        print(f"    ✓ {clause_1_4.title}: {clause_1_4.clause_kind}, risk_bearing={clause_1_4.is_risk_bearing}, risk={clause_1_4.risk_level}")

    # Verify 3.1 and 3.2 are HIGH
    high_clauses = [c for c in doc.clauses if c.risk_level == "HIGH"]
    assert len(high_clauses) >= 2, f"Expected at least 2 HIGH-risk clauses, got {len(high_clauses)}"

    # Verify fairness score is < 50
    assert doc.overall_fairness_score < 50, f"Expected fairness < 50, got {doc.overall_fairness_score}"
    print(f"    ✓ Overall fairness: {doc.overall_fairness_score}/100 (correctly < 50)")

    # Verify risk_reasons are populated on HIGH clauses
    for hc in high_clauses:
        assert len(hc.risk_reasons) >= 2, f"HIGH clause {hc.id} should have ≥ 2 risk_reasons, got {len(hc.risk_reasons)}"
        print(f"    ✓ {hc.title}: {len(hc.risk_reasons)} risk_reasons")


def test_1_chat_canonical_context():
    """TEST 1 — Chat canonical context representation includes structural & risk fields."""
    from app.services.llm_service import llm_service
    test_clause = Clause(
        id="clause_7",
        title="Intellectual Property Assignment",
        text="Contractor hereby assigns all right, title, and interest in Work Product.",
        category="INTELLECTUAL_PROPERTY",
        riskLevel="HIGH",
        unfairnessScore=88,
        clauseKind="OPERATIVE",
        isRiskBearing=True,
        riskReasons=["Material consequence: complete IP loss", "Meaningful imbalance: unilateral assignment"],
        plainSummary="Contractor assigns all IP to Client.",
    )
    contract_info = {"filename": "Test Agreement.pdf", "overall_fairness_score": 42}
    context_str = llm_service.format_chat_context([test_clause], contract_info)

    assert "[clause_7]" in context_str, "Missing clause ID marker"
    assert "Title: Intellectual Property Assignment" in context_str, "Missing title"
    assert "Kind: OPERATIVE" in context_str, "Missing clause_kind"
    assert "Risk Bearing: true" in context_str, "Missing is_risk_bearing"
    assert "Risk Level: HIGH" in context_str, "Missing risk_level"
    assert "Unfairness Score: 88" in context_str, "Missing unfairness_score"
    assert "Risk Reasons:" in context_str, "Missing risk_reasons heading"
    assert "- Material consequence: complete IP loss" in context_str, "Missing specific risk reason 1"
    assert "- Meaningful imbalance: unilateral assignment" in context_str, "Missing specific risk reason 2"
    assert "Category: INTELLECTUAL_PROPERTY" in context_str, "Missing category"
    assert "Text:\nContractor hereby assigns all right, title, and interest in Work Product." in context_str, "Missing original text"
    assert "Summary:\nContractor assigns all IP to Client." in context_str, "Missing plain summary"
    print("  ✓ Test 1: Chat canonical context includes all structural and risk fields in format")


def test_2_pure_cross_reference():
    """TEST 2 — Pure cross-reference: 'As defined in Section 4.' → BOILERPLATE, is_risk_bearing=False."""
    result = heuristic_engine.evaluate_clause(
        title="Cross-Reference",
        text="As defined in Section 4."
    )
    assert result.clause_kind == "BOILERPLATE", f"Expected BOILERPLATE, got {result.clause_kind}"
    assert result.is_risk_bearing is False, f"Expected is_risk_bearing=False, got {result.is_risk_bearing}"
    print("  ✓ Test 2: Pure cross-reference → BOILERPLATE, is_risk_bearing=False")


def test_3_cross_reference_with_operative_language():
    """TEST 3 — Cross-reference with operative language: 'Subject to Section 4, Contractor shall reimburse Client...' → OPERATIVE, is_risk_bearing=True."""
    result = heuristic_engine.evaluate_clause(
        title="Expense Reimbursement",
        text="Subject to Section 4, Contractor shall reimburse Client for approved expenses within 30 days."
    )
    assert result.clause_kind == "OPERATIVE", f"Expected OPERATIVE, got {result.clause_kind}"
    assert result.is_risk_bearing is True, f"Expected is_risk_bearing=True, got {result.is_risk_bearing}"
    print("  ✓ Test 3: Cross-reference with operative language → OPERATIVE, is_risk_bearing=True")


def test_4_governing_law_only():
    """TEST 4 — Governing law only → BOILERPLATE, is_risk_bearing=False."""
    result = heuristic_engine.evaluate_clause(
        title="Governing Law and Jurisdiction",
        text="This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware without regard to conflict of law principles."
    )
    assert result.clause_kind == "BOILERPLATE", f"Expected BOILERPLATE, got {result.clause_kind}"
    assert result.is_risk_bearing is False, f"Expected is_risk_bearing=False, got {result.is_risk_bearing}"
    print("  ✓ Test 4: Governing law only → BOILERPLATE, is_risk_bearing=False")


def test_5_operative_obligation_containing_cross_reference():
    """TEST 5 — Operative obligation containing cross-reference → OPERATIVE, not BOILERPLATE."""
    result = heuristic_engine.evaluate_clause(
        title="Invoicing Procedure",
        text="In accordance with Section 2, Client must pay invoices within fifteen (15) days of receipt."
    )
    assert result.clause_kind == "OPERATIVE", f"Expected OPERATIVE, got {result.clause_kind}"
    assert result.is_risk_bearing is True, f"Expected is_risk_bearing=True, got {result.is_risk_bearing}"
    print("  ✓ Test 5: Operative obligation with cross-reference → OPERATIVE, not BOILERPLATE")


def test_6_structural_authority_overrides_llm():
    """TEST 6 — Structural authority: heuristic DEFINITION + mocked LLM HIGH → DEFINITION, is_risk_bearing=False, risk=NEUTRAL."""
    from app.services.llm_service import llm_service
    from app.schemas.contract import PageContent

    initial = [
        Clause(
            id="clause_1",
            title="1.1 Definitions — Services",
            text='"Services" means all custom computer software development and consulting services performed by Contractor.',
            category="OTHER",
        )
    ]
    mock_llm_data = {
        "overall_fairness_score": 30,
        "clauses": [
            {
                "clause_id": "clause_1",
                "title": "1.1 Definitions — Services",
                "clause_kind": "OPERATIVE",
                "is_risk_bearing": True,
                "category": "OTHER",
                "risk_level": "HIGH",
                "unfairness_score": 90,
                "risk_reasons": ["Hallucinated risk reason on definition"],
                "plain_english_summary": "Services definition.",
            }
        ]
    }
    pages = [PageContent(pageNumber=1, text="test")]
    doc = llm_service._build_document_from_json("sess", "test.pdf", mock_llm_data, initial, pages)
    c1 = doc.clauses[0]
    assert c1.clause_kind == "DEFINITION", f"Expected DEFINITION, got {c1.clause_kind}"
    assert c1.is_risk_bearing is False, f"Expected is_risk_bearing=False, got {c1.is_risk_bearing}"
    assert c1.risk_level == "NEUTRAL", f"Expected NEUTRAL, got {c1.risk_level}"
    assert c1.unfairness_score <= 15, f"Expected unfairness <= 15, got {c1.unfairness_score}"
    assert c1.suggested_pushback is None, f"Expected None pushback, got {c1.suggested_pushback}"
    assert c1.risk_reasons == [], f"Expected empty risk_reasons, got {c1.risk_reasons}"
    print("  ✓ Test 6: Structural authority enforced (DEFINITION, is_risk_bearing=False, risk=NEUTRAL)")


def test_7_llm_cannot_erase_structure():
    """TEST 7 — LLM cannot erase structure: heuristic OPERATIVE + mocked LLM is_risk_bearing=False → OPERATIVE, is_risk_bearing=True."""
    from app.services.llm_service import llm_service
    from app.schemas.contract import PageContent

    initial = [
        Clause(
            id="clause_2",
            title="3.1 Indemnification",
            text="Contractor shall defend, indemnify, and hold harmless Client against any and all losses without cap or limitation.",
            category="INDEMNIFICATION",
        )
    ]
    mock_llm_data = {
        "overall_fairness_score": 80,
        "clauses": [
            {
                "clause_id": "clause_2",
                "title": "3.1 Indemnification",
                "clause_kind": "BOILERPLATE",
                "is_risk_bearing": False,
                "category": "INDEMNIFICATION",
                "risk_level": "LOW",
                "unfairness_score": 10,
                "risk_reasons": [],
                "plain_english_summary": "Indemnity clause.",
            }
        ]
    }
    pages = [PageContent(pageNumber=1, text="test")]
    doc = llm_service._build_document_from_json("sess", "test.pdf", mock_llm_data, initial, pages)
    c2 = doc.clauses[0]
    assert c2.clause_kind == "OPERATIVE", f"Expected OPERATIVE, got {c2.clause_kind}"
    assert c2.is_risk_bearing is True, f"Expected is_risk_bearing=True, got {c2.is_risk_bearing}"
    print("  ✓ Test 7: LLM cannot erase structure (OPERATIVE, is_risk_bearing=True preserved)")


def test_8_high_triple_gate():
    """TEST 8 — HIGH triple gate: risk-bearing clause with insufficient evidence for all 3 gates downgraded to NOT HIGH."""
    from app.services.llm_service import llm_service
    from app.schemas.contract import PageContent

    initial = [
        Clause(
            id="clause_3",
            title="Bug Notification",
            text="Contractor agrees to notify Client of any critical software bugs within fourteen (14) days of discovery.",
            category="OTHER",
        )
    ]
    mock_llm_data = {
        "overall_fairness_score": 40,
        "clauses": [
            {
                "clause_id": "clause_3",
                "title": "Bug Notification",
                "clause_kind": "OPERATIVE",
                "is_risk_bearing": True,
                "category": "OTHER",
                "risk_level": "HIGH",
                "unfairness_score": 85,
                "risk_reasons": ["Unreasonable 14 day requirement"],
                "plain_english_summary": "Bug notification obligation.",
            }
        ]
    }
    pages = [PageContent(pageNumber=1, text="test")]
    doc = llm_service._build_document_from_json("sess", "test.pdf", mock_llm_data, initial, pages)
    c3 = doc.clauses[0]
    assert c3.risk_level != "HIGH", f"Expected NOT HIGH (downgraded), got {c3.risk_level}"
    assert c3.risk_level == "MEDIUM", f"Expected MEDIUM, got {c3.risk_level}"
    assert c3.unfairness_score <= 65, f"Expected unfairness <= 65, got {c3.unfairness_score}"
    print("  ✓ Test 8: HIGH triple gate enforced (downgraded to MEDIUM due to lack of material imbalance/trap)")


def test_9_cross_reference_resolution():
    """TEST 9 — Cross-reference resolution: referenced clause resolved dynamically and included in reasoning."""
    from app.services.heuristic_engine import resolve_referenced_clauses

    clause_8 = Clause(
        id="clause_8",
        title="Section 8. Limitation of Liability",
        text="In no event shall either party's aggregate liability under this Agreement exceed fifty thousand dollars ($50,000).",
        category="LIABILITY",
    )
    clause_10 = Clause(
        id="clause_10",
        title="Section 10. Indemnification",
        text="Contractor shall indemnify and hold harmless Client, subject to the liability cap in Section 8.",
        category="INDEMNIFICATION",
    )
    all_clauses = [clause_8, clause_10]

    # Resolve references
    refs = resolve_referenced_clauses(clause_10, all_clauses)
    assert len(refs) == 1, f"Expected 1 resolved reference, got {len(refs)}"
    assert refs[0].target_clause.id == "clause_8", f"Expected target clause_8, got {refs[0].target_clause.id}"
    assert refs[0].relation in ("mitigates", "limits"), f"Expected mitigates/limits, got {refs[0].relation}"

    # Evaluate clause with all_clauses
    eval_res = heuristic_engine.evaluate_clause(clause_10.title, clause_10.text, all_clauses=all_clauses)
    assert eval_res.risk_level in ("LOW", "MEDIUM"), f"Expected LOW/MEDIUM due to referenced liability cap, got {eval_res.risk_level}"
    print(f"  ✓ Test 9: Cross-reference resolved dynamically (relation={refs[0].relation}) and incorporated into reasoning")


def test_10_unresolved_reference():
    """TEST 10 — Unresolved reference: reference to nonexistent section produces no fabricated reference and no crash."""
    from app.services.heuristic_engine import resolve_referenced_clauses

    clause_with_missing_ref = Clause(
        id="clause_5",
        title="Section 5. Warranties",
        text="Except as expressly provided in Section 99, Contractor disclaims all warranties.",
        category="WARRANTIES",
    )
    all_clauses = [clause_with_missing_ref]

    refs = resolve_referenced_clauses(clause_with_missing_ref, all_clauses)
    assert len(refs) == 0, f"Expected 0 resolved references for nonexistent Section 99, got {len(refs)}"

    eval_res = heuristic_engine.evaluate_clause(clause_with_missing_ref.title, clause_with_missing_ref.text, all_clauses=all_clauses)
    assert eval_res is not None
    assert eval_res.clause_kind == "OPERATIVE"
    print("  ✓ Test 10: Unresolved reference to nonexistent Section 99 handled gracefully with no fabrication")


def test_11_neutral_term_duration_under_compound_title():
    """TEST 11 — Neutral term duration under compound title 'TERM AND RENEWAL' → OPERATIVE, LOW risk, not TERMINATION risk."""
    eval_res = heuristic_engine.evaluate_clause(
        title="SECTION 2: TERM AND RENEWAL — Initial Term",
        text="This Agreement commences on the Effective Date and shall remain in effect for an initial duration of twelve (12) months, unless terminated earlier in accordance with Section 4.",
    )
    assert eval_res.clause_kind == "OPERATIVE", f"Expected OPERATIVE, got {eval_res.clause_kind}"
    assert eval_res.is_risk_bearing is True, f"Expected is_risk_bearing=True, got {eval_res.is_risk_bearing}"
    assert eval_res.risk_level == "LOW", f"Expected LOW risk, got {eval_res.risk_level}"
    assert eval_res.unfairness_score <= 20, f"Expected unfairness <= 20, got {eval_res.unfairness_score}"
    assert eval_res.category != "TERMINATION", f"Expected non-TERMINATION category, got {eval_res.category}"
    print("  ✓ Test 11: Neutral term duration under compound title scored LOW (not TERMINATION risk)")


def test_12_mutual_renewal_customary_notice():
    """TEST 12 — Customary mutual renewal with 30-day notice → OPERATIVE, LOW risk."""
    eval_res = heuristic_engine.evaluate_clause(
        title="TERM AND RENEWAL — Renewal Terms",
        text="This Agreement shall automatically renew for successive terms of one (1) year each, unless either party gives written notice of its intent not to renew at least thirty (30) days prior to the expiration of the then-current term.",
    )
    assert eval_res.clause_kind == "OPERATIVE", f"Expected OPERATIVE, got {eval_res.clause_kind}"
    assert eval_res.is_risk_bearing is True, f"Expected is_risk_bearing=True, got {eval_res.is_risk_bearing}"
    assert eval_res.risk_level == "LOW", f"Expected LOW risk, got {eval_res.risk_level}"
    assert eval_res.unfairness_score <= 25, f"Expected unfairness <= 25, got {eval_res.unfairness_score}"
    print("  ✓ Test 12: Mutual renewal with customary 30-day notice scored LOW")


def test_13_unilateral_renewal_counterparty_option():
    """TEST 13 — Unilateral renewal at counterparty's sole discretion without consent → HIGH risk."""
    eval_res = heuristic_engine.evaluate_clause(
        title="Extension of Agreement",
        text="Client shall have the sole option and unilateral right to renew this Agreement for additional successive periods of twelve (12) months each upon written notice to Contractor, without requiring Contractor consent.",
    )
    assert eval_res.clause_kind == "OPERATIVE", f"Expected OPERATIVE, got {eval_res.clause_kind}"
    assert eval_res.is_risk_bearing is True, f"Expected is_risk_bearing=True, got {eval_res.is_risk_bearing}"
    assert eval_res.risk_level == "HIGH", f"Expected HIGH risk, got {eval_res.risk_level}"
    assert eval_res.unfairness_score >= 75, f"Expected unfairness >= 75, got {eval_res.unfairness_score}"
    assert len(eval_res.risk_reasons) >= 2, f"Expected >= 2 risk reasons, got {len(eval_res.risk_reasons)}"
    print("  ✓ Test 13: Unilateral renewal at counterparty's sole option scored HIGH")


def test_14_automatic_renewal_excessive_notice_trap():
    """TEST 14 — Automatic renewal with excessive 90-day notice window → MEDIUM risk."""
    eval_res = heuristic_engine.evaluate_clause(
        title="Term Extension and Rollover",
        text="Upon expiration of the initial term, this Agreement shall automatically renew for successive three-year periods unless Contractor provides formal written notice of non-renewal at least ninety (90) days prior to the expiration date.",
    )
    assert eval_res.clause_kind == "OPERATIVE", f"Expected OPERATIVE, got {eval_res.clause_kind}"
    assert eval_res.is_risk_bearing is True, f"Expected is_risk_bearing=True, got {eval_res.is_risk_bearing}"
    assert eval_res.risk_level == "MEDIUM", f"Expected MEDIUM risk, got {eval_res.risk_level}"
    assert eval_res.unfairness_score >= 50, f"Expected unfairness >= 50, got {eval_res.unfairness_score}"
    assert len(eval_res.risk_reasons) >= 1, f"Expected >= 1 risk reasons, got {len(eval_res.risk_reasons)}"
    print("  ✓ Test 14: Automatic renewal with excessive 90-day notice scored MEDIUM")


def test_15_term_expiration_with_forfeiture():
    """TEST 15 — Term expiration with forfeiture of compensation → HIGH risk."""
    eval_res = heuristic_engine.evaluate_clause(
        title="Contract Term and Expiration",
        text="The term of this Agreement shall expire on December 31, 2026. Upon expiration without renewal, Contractor shall forfeit all unbilled fees and receive no compensation for work in progress.",
    )
    assert eval_res.clause_kind == "OPERATIVE", f"Expected OPERATIVE, got {eval_res.clause_kind}"
    assert eval_res.is_risk_bearing is True, f"Expected is_risk_bearing=True, got {eval_res.is_risk_bearing}"
    assert eval_res.risk_level == "HIGH", f"Expected HIGH risk, got {eval_res.risk_level}"
    assert eval_res.unfairness_score >= 80, f"Expected unfairness >= 80, got {eval_res.unfairness_score}"
    print("  ✓ Test 15: Term expiration with forfeiture scored HIGH")


def test_16_global_risk_query_intent_detection():
    """TEST 16 — Generic global risk/ranking intent detection."""
    positive_queries = [
        "What are the 5 most materially risky operative provisions in this contract?",
        "What are the most materially risky clauses?",
        "What are the highest risk provisions?",
        "What are the top risks in this agreement?",
        "List the worst clauses for me",
        "Biggest risks in this contract",
        "Major exposures in this agreement",
        "Rank the riskiest provisions",
        "Show me all high risk clauses",
        "What should I be most worried about in this contract?",
        "What are the top predatory terms?",
        "Where is my biggest exposure?",
        "Top 3 risks",
        "What are the critical risks here?",
    ]
    for q in positive_queries:
        assert is_global_risk_query(q) is True, f"Expected global risk intent for: '{q}'"

    negative_queries = [
        "Why is clause 3.1 high risk?",
        "Explain section 4",
        "What does clause 14 say about indemnification?",
        "What happens if the client terminates early?",
        "What is the governing law of this contract?",
        "Can I subcontract my work under section 2?",
        "Hello, how can you help me?",
    ]
    for q in negative_queries:
        assert is_global_risk_query(q) is False, f"Expected non-global query for: '{q}'"

    print("  ✓ Test 16: Generic global-risk intent detection accurately classifies queries")


def test_17_global_risk_ranking_prefers_high_medium_over_low():
    """TEST 17 — Global risk ranking prefers HIGH/MEDIUM over LOW/NEUTRAL."""
    synthetic_clauses = [
        Clause(id="c_def_1", title="1.1 Definitions — Scope", text="Scope defined.", risk_level="NEUTRAL", clause_kind="DEFINITION", is_risk_bearing=False, unfairness_score=0),
        Clause(id="c_def_2", title="1.2 Definitions — Deliverables", text="Deliverables defined.", risk_level="NEUTRAL", clause_kind="DEFINITION", is_risk_bearing=False, unfairness_score=0),
        Clause(id="c_head", title="2.0 PERFORMANCE TERMS", text="Section heading.", risk_level="NEUTRAL", clause_kind="HEADING", is_risk_bearing=False, unfairness_score=0),
        Clause(id="c_low_1", title="2.1 Delivery Timelines", text="Delivery within 30 days.", risk_level="LOW", clause_kind="OPERATIVE", is_risk_bearing=True, unfairness_score=15),
        Clause(id="c_low_2", title="2.2 Status Reports", text="Monthly reporting.", risk_level="LOW", clause_kind="OPERATIVE", is_risk_bearing=True, unfairness_score=20),
        Clause(id="c_med_1", title="3.1 Extended Payment Terms", text="Net 90 payment terms.", risk_level="MEDIUM", clause_kind="OPERATIVE", is_risk_bearing=True, unfairness_score=60),
        Clause(id="c_med_2", title="3.2 Renewal Notice Window", text="90 day non-renewal notice window.", risk_level="MEDIUM", clause_kind="OPERATIVE", is_risk_bearing=True, unfairness_score=55),
        Clause(id="c_high_1", title="4.1 Uncapped Indemnification", text="Contractor provides uncapped indemnity.", risk_level="HIGH", clause_kind="OPERATIVE", is_risk_bearing=True, unfairness_score=92),
        Clause(id="c_high_2", title="4.2 Immediate IP Assignment", text="Irrevocable immediate IP transfer.", risk_level="HIGH", clause_kind="OPERATIVE", is_risk_bearing=True, unfairness_score=88),
    ]

    ranked = rank_risk_clauses(synthetic_clauses, limit=5)

    # 1. No definitions or headings
    for c in ranked:
        assert c.clause_kind == "OPERATIVE", f"Definitions/headings must never be in ranked list: {c.title}"
        assert c.is_risk_bearing is True, f"Non-risk-bearing clause in ranked list: {c.title}"

    # 2. Top 2 must be the HIGH risk clauses
    assert ranked[0].id == "c_high_1", f"Expected c_high_1 first, got {ranked[0].id}"
    assert ranked[0].risk_level == "HIGH"
    assert ranked[1].id == "c_high_2", f"Expected c_high_2 second, got {ranked[1].id}"
    assert ranked[1].risk_level == "HIGH"

    # 3. Next 2 must be the MEDIUM risk clauses
    assert ranked[2].id == "c_med_1", f"Expected c_med_1 third, got {ranked[2].id}"
    assert ranked[2].risk_level == "MEDIUM"
    assert ranked[3].id == "c_med_2", f"Expected c_med_2 fourth, got {ranked[3].id}"
    assert ranked[3].risk_level == "MEDIUM"

    # 4. Only genuine materially risky clauses are returned (exactly 4, not padded with LOW to reach 5)
    assert len(ranked) == 4, f"Expected 4 materially risky clauses, got {len(ranked)}"
    assert "c_low_1" not in [c.id for c in ranked], "LOW clause must not be in ranked list"
    assert "c_low_2" not in [c.id for c in ranked], "LOW clause must not be in ranked list"

    # 5. Verify monotonic risk severity ranking (HIGH before MEDIUM)
    risk_weights = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "NEUTRAL": 0}
    weights = [risk_weights[c.risk_level] for c in ranked]
    assert weights == sorted(weights, reverse=True), "Ranked list must be monotonically non-increasing by risk severity"

    print("  ✓ Test 17: Global risk ranking strictly prefers HIGH/MEDIUM and never pads with LOW/NEUTRAL")


def test_18_global_risk_excludes_definitions_even_if_selected():
    """TEST 18 — Global risk query excludes definitions/headings even when passed as selected_clause_id."""
    synthetic_clauses = [
        Clause(id="def_1", title="1.1 Definitions — Scope", text="Definitions text.", risk_level="NEUTRAL", clause_kind="DEFINITION", is_risk_bearing=False, unfairness_score=0),
        Clause(id="op_high", title="2.1 Unlimited Liability Trap", text="Sole uncapped liability.", risk_level="HIGH", clause_kind="OPERATIVE", is_risk_bearing=True, unfairness_score=95),
        Clause(id="op_med", title="2.2 Unilateral Termination", text="Termination at will.", risk_level="MEDIUM", clause_kind="OPERATIVE", is_risk_bearing=True, unfairness_score=70),
    ]

    session_id = "test_sess_def_exclude"
    rag_engine.index_document(session_id, "TestAgreement.pdf", synthetic_clauses)

    query = "What are the 5 most materially risky operative provisions in this contract?"
    context = rag_engine.retrieve_chat_context(session_id, query, selected_clause_id="def_1", k=5)

    assert "def_1" not in [c.id for c in context], "def_1 must not be in the ranked risk context!"
    assert [c.id for c in context] == ["op_high", "op_med"]
    print("  ✓ Test 18: Definitions/headings excluded from global risk ranking even if selected")


def test_19_normal_rag_preserved_for_specific_queries():
    """TEST 19 — Specific clause/scenario questions preserve normal RAG behavior and selected clause context."""
    synthetic_clauses = [
        Clause(id="c_1", title="1.1 Preamble", text="Introductory text.", risk_level="LOW", clause_kind="OPERATIVE", is_risk_bearing=True),
        Clause(id="c_2", title="1.2 Scope of Services", text="Consultant provides architecture design.", risk_level="LOW", clause_kind="OPERATIVE", is_risk_bearing=True),
        Clause(id="c_3", title="1.3 Payment Deadlines", text="Client pays within 15 days.", risk_level="LOW", clause_kind="OPERATIVE", is_risk_bearing=True),
        Clause(id="c_4", title="1.4 Uncapped Indemnification", text="Contractor uncapped indemnity.", risk_level="HIGH", clause_kind="OPERATIVE", is_risk_bearing=True, unfairness_score=90),
    ]

    session_id = "test_sess_specific_rag"
    rag_engine.index_document(session_id, "ServicesAgreement.pdf", synthetic_clauses)

    specific_query = "What are the payment deadlines under Section 1.3?"
    context = rag_engine.retrieve_chat_context(session_id, specific_query, selected_clause_id="c_3", k=3)

    context_ids = [c.id for c in context]
    assert "c_3" in context_ids, f"Expected selected clause c_3 in context, got {context_ids}"
    assert "c_2" in context_ids or "c_4" in context_ids, "Expected adjacent neighbor in context"
    print("  ✓ Test 19: Specific clause questions preserve focused RAG selection and neighboring context")


def test_20_cannot_return_low_when_high_exists():
    """TEST 20 — Proves a global 'top risks' query cannot return LOW/NEUTRAL when stronger canonical risk clauses exist."""
    mixed_clauses = [
        Clause(id="def_heading", title="1.0 DEFINITIONS", text="Definitions heading.", risk_level="NEUTRAL", clause_kind="HEADING", is_risk_bearing=False, unfairness_score=0),
        Clause(id="def_item", title="1.1 Definition — Affiliate", text="Means parent or subsidiary.", risk_level="NEUTRAL", clause_kind="DEFINITION", is_risk_bearing=False, unfairness_score=0),
        Clause(id="low_term", title="2.1 Term Duration", text="Agreement continues for 1 year.", risk_level="LOW", clause_kind="OPERATIVE", is_risk_bearing=True, unfairness_score=10),
        Clause(id="low_conf", title="2.2 Confidentiality", text="Parties maintain standard confidentiality.", risk_level="LOW", clause_kind="OPERATIVE", is_risk_bearing=True, unfairness_score=15),
        Clause(id="med_audit", title="3.1 Discretionary Audit", text="Client may audit contractor records upon 5 days notice.", risk_level="MEDIUM", clause_kind="OPERATIVE", is_risk_bearing=True, unfairness_score=60),
        Clause(id="high_indem", title="4.1 Uncapped Indemnity Trap", text="Contractor irrevocably defends and indemnifies client without cap or fault.", risk_level="HIGH", clause_kind="OPERATIVE", is_risk_bearing=True, unfairness_score=95),
        Clause(id="high_ip", title="4.2 Immediate IP Forfeiture", text="Contractor assigns all IP immediately without condition of payment.", risk_level="HIGH", clause_kind="OPERATIVE", is_risk_bearing=True, unfairness_score=90),
    ]

    session_id = "test_sess_preference_proof"
    rag_engine.index_document(session_id, "VendorContract.pdf", mixed_clauses)

    query = "What are the 5 most materially risky operative provisions in this contract?"
    context = rag_engine.retrieve_chat_context(session_id, query, k=3)

    retrieved_ids = [c.id for c in context]
    assert retrieved_ids == ["high_indem", "high_ip", "med_audit"], f"Expected top risk clauses, got {retrieved_ids}"
    assert "low_term" not in retrieved_ids, "LOW risk clause must NOT displace HIGH/MEDIUM risks"
    assert "low_conf" not in retrieved_ids, "LOW risk clause must NOT displace HIGH/MEDIUM risks"
    assert "def_heading" not in retrieved_ids, "HEADING must never be in risk ranking"
    assert "def_item" not in retrieved_ids, "DEFINITION must never be in risk ranking"
    print("  ✓ Test 20: Verified global top risks query CANNOT return LOW/NEUTRAL when stronger risk clauses exist")


def test_21_low_protective_clause_excluded_from_global_risk():
    """TEST 21 — LOW protective clause in an indemnity/liability section must NEVER be ranked as a material risk."""
    clauses = [
        Clause(
            id="c_prot_indem",
            title="3.2 Client Indemnification of Contractor",
            text="Client shall defend, indemnify, and hold harmless Contractor from and against any and all third-party claims, damages, and expenses arising out of Client's breach or materials.",
            risk_level="LOW",
            clause_kind="OPERATIVE",
            is_risk_bearing=True,
            unfairness_score=15,
            risk_reasons=[],
        ),
        Clause(
            id="c_high_ip",
            title="4.1 Immediate IP Assignment",
            text="Contractor hereby irrevocably assigns all intellectual property rights to Client immediately upon creation without condition of payment.",
            risk_level="HIGH",
            clause_kind="OPERATIVE",
            is_risk_bearing=True,
            unfairness_score=90,
            risk_reasons=["Material consequence: unconditional IP forfeiture", "Meaningful imbalance: unilateral transfer without payment"],
        ),
    ]

    session_id = "test_sess_protective_exclude"
    rag_engine.index_document(session_id, "ProtectiveTest.pdf", clauses)

    query = "What are the 5 most materially risky operative provisions in this contract?"
    ranked = rank_risk_clauses(clauses, limit=5)
    context = rag_engine.retrieve_chat_context(session_id, query, k=5)

    ranked_ids = [c.id for c in ranked]
    context_ids = [c.id for c in context]

    assert "c_prot_indem" not in ranked_ids, "LOW protective clause must be excluded from rank_risk_clauses"
    assert "c_prot_indem" not in context_ids, "LOW protective clause must be excluded from retrieve_chat_context"
    assert ranked_ids == ["c_high_ip"]
    assert context_ids == ["c_high_ip"]
    print("  ✓ Test 21: LOW protective clause under indemnity section strictly excluded from global risk ranking")


def test_22_mitigation_clause_excluded_from_material_risk():
    """TEST 22 — Clause containing mitigating/protective language (caps, mutuality, carve-outs) excluded from material risk."""
    clauses = [
        Clause(
            id="c_mitigated_indem",
            title="4.1 Mutual Indemnification and Liability Cap",
            text="Each party shall defend and indemnify the other against third-party claims arising solely from its gross negligence. Contractor's total aggregate liability shall be capped at fees received. Contractor shall have no liability for claims arising from Client's negligence.",
            risk_level="MEDIUM",
            clause_kind="OPERATIVE",
            is_risk_bearing=True,
            unfairness_score=35,
            risk_reasons=["Bilateral indemnity with contractual fee cap"],
        ),
        Clause(
            id="c_high_trap",
            title="5.1 Uncapped Direct Damages",
            text="Contractor shall be liable for all direct, indirect, and consequential damages without limitation or cap.",
            risk_level="HIGH",
            clause_kind="OPERATIVE",
            is_risk_bearing=True,
            unfairness_score=95,
            risk_reasons=["Material consequence: unlimited liability", "Meaningful imbalance: uncapped damages against contractor"],
        ),
    ]

    session_id = "test_sess_mitigation_exclude"
    rag_engine.index_document(session_id, "MitigationTest.pdf", clauses)

    query = "What are the highest risk provisions?"
    context = rag_engine.retrieve_chat_context(session_id, query, k=5)
    context_ids = [c.id for c in context]

    assert "c_mitigated_indem" not in context_ids, "Mitigated clause with fee caps and carve-outs must not be ranked as material risk"
    assert context_ids == ["c_high_trap"]
    print("  ✓ Test 22: Mitigated clause with caps, mutuality, and carve-outs excluded from material risk ranking")


def test_23_low_neutral_clauses_never_used_as_fillers():
    """TEST 23 — Proves that for a 'top 5' query, fewer than 5 items are returned when fewer than 5 material risks exist."""
    clauses = [
        Clause(id="def_1", title="1.1 Definitions — Scope", text="Definitions text.", risk_level="NEUTRAL", clause_kind="DEFINITION", is_risk_bearing=False, unfairness_score=0),
        Clause(id="c_low_1", title="2.1 Term Duration", text="Agreement continues for 1 year.", risk_level="LOW", clause_kind="OPERATIVE", is_risk_bearing=True, unfairness_score=10),
        Clause(id="c_low_2", title="2.2 Confidentiality", text="Parties maintain mutual confidentiality.", risk_level="LOW", clause_kind="OPERATIVE", is_risk_bearing=True, unfairness_score=15),
        Clause(id="c_low_3", title="2.3 Notices", text="Notices given in writing.", risk_level="LOW", clause_kind="OPERATIVE", is_risk_bearing=True, unfairness_score=10),
        Clause(id="c_med_renewal", title="3.1 Auto-Renewal Trap", text="Automatically renews unless non-renewal notice provided 90 days prior.", risk_level="MEDIUM", clause_kind="OPERATIVE", is_risk_bearing=True, unfairness_score=60, risk_reasons=["Excessive 90-day non-renewal notice"]),
        Clause(id="c_high_indem", title="4.1 Uncapped Indemnity", text="Contractor indemnifies client without cap or fault.", risk_level="HIGH", clause_kind="OPERATIVE", is_risk_bearing=True, unfairness_score=95, risk_reasons=["Uncapped unilateral indemnification"]),
    ]

    session_id = "test_sess_filler_proof"
    rag_engine.index_document(session_id, "FewRisksContract.pdf", clauses)

    query = "What are the 5 most materially risky operative provisions in this contract?"
    ranked = rank_risk_clauses(clauses, limit=5)
    context = rag_engine.retrieve_chat_context(session_id, query, k=5)

    # Exactly 2 clauses exist that are materially risky (c_high_indem and c_med_renewal).
    # Remaining 3 slots must NOT be filled with LOW/NEUTRAL clauses!
    assert len(ranked) == 2, f"Expected exactly 2 material risks in rank_risk_clauses, got {len(ranked)}"
    assert len(context) == 2, f"Expected exactly 2 material risks in retrieve_chat_context, got {len(context)}"
    assert [c.id for c in ranked] == ["c_high_indem", "c_med_renewal"]
    assert [c.id for c in context] == ["c_high_indem", "c_med_renewal"]
    for low_id in ["def_1", "c_low_1", "c_low_2", "c_low_3"]:
        assert low_id not in [c.id for c in context], f"{low_id} was improperly used as a filler!"
    print("  ✓ Test 23: LOW/NEUTRAL clauses are never used as fillers to reach 'top 5'")


def test_24_proposed_rewrites_tailored_to_clause_text_and_reasons():
    """TEST 24 — Proposed rewrites are generated from actual clause text and risk reasons, not broad category name alone."""
    from app.services.llm_service import llm_service

    ip_clause = Clause(
        id="c_ip",
        title="4.1 Intellectual Property Assignment",
        text="Contractor hereby irrevocably assigns all intellectual property rights to Client immediately upon creation without condition of payment.",
        category="INTELLECTUAL_PROPERTY",
        risk_level="HIGH",
        clause_kind="OPERATIVE",
        is_risk_bearing=True,
        unfairness_score=90,
        risk_reasons=["Material consequence: immediate unconditional assignment", "Meaningful imbalance: transfer occurs prior to payment"],
    )

    pay_clause = Clause(
        id="c_pay",
        title="5.1 Disputed Invoicing & Withholding",
        text="Client reserves the right to withhold any invoice payments or setoff disputed fees at its sole discretion.",
        category="PAYMENT_TERMS",
        risk_level="MEDIUM",
        clause_kind="OPERATIVE",
        is_risk_bearing=True,
        unfairness_score=65,
        risk_reasons=["Meaningful imbalance: unilateral right to withhold invoice payments"],
    )

    ip_rewrite = llm_service._generate_tailored_counter_proposal(ip_clause)
    pay_rewrite = llm_service._generate_tailored_counter_proposal(pay_clause)

    # IP rewrite must target IP transfer and payment condition, NOT generic liability caps
    assert "intellectual property" in ip_rewrite.lower() or "payment" in ip_rewrite.lower(), f"IP rewrite not tailored: {ip_rewrite}"
    assert "liability cap" not in ip_rewrite.lower(), f"IP rewrite used generic liability boilerplate: {ip_rewrite}"

    # Payment rewrite must target invoice / withholding, NOT IP or liability caps
    assert "invoice" in pay_rewrite.lower() or "payment" in pay_rewrite.lower() or "withhold" in pay_rewrite.lower(), f"Payment rewrite not tailored: {pay_rewrite}"
    print("  ✓ Test 24: Proposed rewrites are tailored to actual clause text and risk reasons, not category name alone")


def main():
    print("================================================================")
    print("ACCURACY V2.4 — GENERALIZED REGRESSION TEST SUITE")
    print("(Zero Hardcoding — All Synthetic Inline Text)")
    print("================================================================\n")

    print("--- Core V2 Tests (A - L) ---")
    tests_v2 = [
        ("A", test_a_pure_definition),
        ("B", test_b_heading_only),
        ("C", test_c_balanced_mutual_indemnity),
        ("D", test_d_unilateral_uncapped_indemnity),
        ("E", test_e_definition_with_hidden_trap),
        ("F", test_f_pure_cross_reference),
        ("G", test_g_recital),
        ("H", test_h_mutual_termination),
        ("I", test_i_unilateral_termination_with_forfeiture),
        ("J", test_j_balanced_payment),
        ("K", test_k_fairness_definitions_dont_mask_traps),
        ("L", test_l_clean_contract_fair),
    ]

    passed = 0
    failed = 0
    for label, fn in tests_v2:
        try:
            fn()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ Test {label}: FAILED — {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ Test {label}: ERROR — {e}")
            failed += 1

    print("\n--- Accuracy V2.1 Hardening Tests (1 - 10) ---")
    tests_v2_1 = [
        ("1", test_1_chat_canonical_context),
        ("2", test_2_pure_cross_reference),
        ("3", test_3_cross_reference_with_operative_language),
        ("4", test_4_governing_law_only),
        ("5", test_5_operative_obligation_containing_cross_reference),
        ("6", test_6_structural_authority_overrides_llm),
        ("7", test_7_llm_cannot_erase_structure),
        ("8", test_8_high_triple_gate),
        ("9", test_9_cross_reference_resolution),
        ("10", test_10_unresolved_reference),
    ]

    for label, fn in tests_v2_1:
        try:
            fn()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ Test {label}: FAILED — {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ Test {label}: ERROR — {e}")
            failed += 1

    print("\n--- Accuracy V2.2 Term & Renewal Hardening Tests (11 - 15) ---")
    tests_v2_2 = [
        ("11", test_11_neutral_term_duration_under_compound_title),
        ("12", test_12_mutual_renewal_customary_notice),
        ("13", test_13_unilateral_renewal_counterparty_option),
        ("14", test_14_automatic_renewal_excessive_notice_trap),
        ("15", test_15_term_expiration_with_forfeiture),
    ]

    for label, fn in tests_v2_2:
        try:
            fn()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ Test {label}: FAILED — {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ Test {label}: ERROR — {e}")
            failed += 1

    print("\n--- Accuracy V2.3 & V2.4 Global Risk Ranking & Quality Tests (16 - 24) ---")
    tests_v2_3 = [
        ("16", test_16_global_risk_query_intent_detection),
        ("17", test_17_global_risk_ranking_prefers_high_medium_over_low),
        ("18", test_18_global_risk_excludes_definitions_even_if_selected),
        ("19", test_19_normal_rag_preserved_for_specific_queries),
        ("20", test_20_cannot_return_low_when_high_exists),
        ("21", test_21_low_protective_clause_excluded_from_global_risk),
        ("22", test_22_mitigation_clause_excluded_from_material_risk),
        ("23", test_23_low_neutral_clauses_never_used_as_fillers),
        ("24", test_24_proposed_rewrites_tailored_to_clause_text_and_reasons),
    ]

    for label, fn in tests_v2_3:
        try:
            fn()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ Test {label}: FAILED — {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ Test {label}: ERROR — {e}")
            failed += 1

    print(f"\n--- Stress Contract Regression ---")
    try:
        test_stress_contract_regression()
        passed += 1
    except AssertionError as e:
        print(f"  ✗ Stress Regression: FAILED — {e}")
        failed += 1
    except Exception as e:
        print(f"  ✗ Stress Regression: ERROR — {e}")
        failed += 1

    total = passed + failed
    print(f"\n================================================================")
    print(f"RESULTS: {passed}/{total} passed, {failed}/{total} failed")
    if failed == 0:
        print("ALL TESTS PASSED ✓")
    else:
        print(f"⚠ {failed} TEST(S) FAILED")
    print(f"================================================================")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
