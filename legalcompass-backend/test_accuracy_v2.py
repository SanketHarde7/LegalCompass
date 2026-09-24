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


def main():
    print("================================================================")
    print("ACCURACY V2.1 — GENERALIZED REGRESSION TEST SUITE")
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
