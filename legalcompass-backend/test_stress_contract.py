"""
Verification script for LegalCompass Stress Test Contract segmentation, LLM mapping, and offsets.
"""
import sys
import os
import asyncio

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.document_parser import document_parser
from app.services.llm_service import llm_service
from app.schemas.contract import PageContent

STRESS_TEST_CONTRACT = """PROFESSIONAL SOFTWARE DEVELOPMENT AND DIGITAL SERVICES AGREEMENT

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

async def main():
    print("================================================================")
    print("TESTING DOCUMENT PARSER ON STRESS TEST CONTRACT")
    print("================================================================")
    
    pages_content = [(1, STRESS_TEST_CONTRACT)]
    clauses = document_parser.parse_clauses(STRESS_TEST_CONTRACT, pages_content)
    
    print(f"\n[1] Document Title: {repr(document_parser.document_title)}")
    assert document_parser.document_title is not None, "Document title should be extracted"
    assert "PROFESSIONAL SOFTWARE DEVELOPMENT" in document_parser.document_title, "Title should match top line"
    
    clause_titles = [c.title for c in clauses]
    print(f"\n[2] Extracted {len(clauses)} clauses:")
    for c in clauses:
        print(f"  - [{c.id}] {c.title} (offsets: {c.start_offset} -> {c.end_offset})")
        # Verify offsets
        if c.start_offset is not None and c.end_offset is not None:
            slice_text = STRESS_TEST_CONTRACT[c.start_offset:c.end_offset]
            assert slice_text.strip().startswith(c.text[:20].strip()), f"Offset slice mismatch for {c.id}"
            print(f"      Verified exact slice: {repr(slice_text[:40])}...")

    # Requirement 1: Document title must NOT appear as a clause
    for c in clauses:
        assert "PROFESSIONAL SOFTWARE DEVELOPMENT AND DIGITAL SERVICES AGREEMENT" != c.title.strip(), \
            f"Document title was mistakenly parsed as a clause: {c.title}"
        assert not c.title.startswith("PROFESSIONAL SOFTWARE DEVELOPMENT"), \
            f"Clause title contains document title: {c.title}"

    # Requirement 2: RECITALS must not be a risk clause / section 1 must not be one giant chunk
    sub_1_clauses = [c for c in clauses if c.title.startswith("1.") or "1." in c.title]
    print(f"\n[3] Sub-clauses under Section 1: {len(sub_1_clauses)}")
    assert len(sub_1_clauses) >= 5, f"Expected at least 5 sub-clauses for Section 1, got {len(sub_1_clauses)}"

    # Requirement 3: 1.4 must be its own standalone clause
    clause_1_4 = next((c for c in clauses if "1.4" in c.title), None)
    assert clause_1_4 is not None, "Clause 1.4 was not extracted as its own clause!"
    print(f"\n[4] Isolated Clause 1.4:")
    print(f"    Title: {clause_1_4.title}")
    print(f"    Text: {repr(clause_1_4.text[:80])}...")
    print(f"    Offsets: {clause_1_4.start_offset} to {clause_1_4.end_offset}")
    assert "Invoicing" in clause_1_4.title or "Precedence" in clause_1_4.title, f"Unexpected 1.4 title: {clause_1_4.title}"
    assert "conflict or inconsistency" in clause_1_4.text, "Clause 1.4 text missing key language"

    print("\n[5] Testing Heuristic / LLM mapping pipeline (strict clause_id, zero positional fallback)...")
    page_objects = [PageContent(pageNumber=1, text=STRESS_TEST_CONTRACT)]
    doc = llm_service._heuristic_analysis(
        session_id="test_sess",
        filename="stress_test.pdf",
        initial_clauses=clauses,
        page_objects=page_objects,
        document_title=document_parser.document_title,
    )
    
    print(f"    Doc DocumentTitle: {doc.document_title}")
    print(f"    Overall fairness score: {doc.overall_fairness_score}")
    print(f"    Analyzed clauses count: {len(doc.clauses)}")
    for c in doc.clauses:
        print(f"    [{c.id}] {c.title} -> Risk: {c.risk_level}, Score: {c.unfairness_score}, Offsets: {c.start_offset}-{c.end_offset}")
        assert c.start_offset is not None and c.end_offset is not None, f"Offsets lost for {c.id}"

    # Test _build_document_from_json strict clause_id matching
    mock_llm_json = {
        "overall_fairness_score": 45,
        "summary_overview": "Mock summary overview",
        "clauses": [
            {
                "clause_id": clause_1_4.id,
                "title": clause_1_4.title,
                "category": "DISPUTE_RESOLUTION",
                "risk_level": "HIGH",
                "unfairness_score": 85,
                "plain_english_summary": "Order of precedence allows client PO to override contract protections.",
                "suggested_pushback": "The terms of this Agreement shall strictly prevail over any Purchase Order."
            }
        ]
    }
    
    analyzed_from_json = llm_service._build_document_from_json(
        session_id="json_sess",
        filename="stress_test.pdf",
        data=mock_llm_json,
        initial_clauses=clauses,
        page_objects=page_objects,
        document_title=document_parser.document_title,
    )
    
    analyzed_1_4 = next(c for c in analyzed_from_json.clauses if c.id == clause_1_4.id)
    assert analyzed_1_4.risk_level == "HIGH", "Clause 1.4 should have received HIGH risk from LLM response by clause_id"
    assert analyzed_1_4.unfairness_score == 85, "Clause 1.4 unfairness score should be 85"
    assert analyzed_1_4.start_offset == clause_1_4.start_offset, "start_offset must be preserved"
    assert analyzed_1_4.end_offset == clause_1_4.end_offset, "end_offset must be preserved"

    # Other clauses (not in LLM response) must stay in deterministic LOW/NEUTRAL fallback, NOT positionally mapped!
    other_clauses = [c for c in analyzed_from_json.clauses if c.id != clause_1_4.id]
    for oc in other_clauses:
        assert oc.risk_level == "LOW", f"Clause {oc.id} should NOT have been positionally assigned HIGH risk!"
        assert oc.start_offset is not None, f"start_offset missing on {oc.id}"

    # [6] Test completely arbitrary titles to verify nothing is hardcoded
    print("\n[6] Testing dynamic title extraction on diverse contracts (Zero hardcoding check)...")
    sample_contracts = [
        ("RESIDENTIAL LEASE AGREEMENT\n\nThis Lease is made on Jan 1, 2026.\n\nRECITALS\nWHEREAS, Landlord owns property.\n\n1. RENT\n1.1 Base rent is $2000.\n", "RESIDENTIAL LEASE AGREEMENT"),
        ("MUTUAL NON-DISCLOSURE AND CONFIDENTIALITY AGREEMENT\n\nParties agree:\n\n1. CONFIDENTIAL INFORMATION\n1.1 Scope of info.\n", "MUTUAL NON-DISCLOSURE AND CONFIDENTIALITY AGREEMENT"),
        ("EMPLOYMENT & SEVERANCE AGREEMENT\n\nEffective Date: 2026.\n\nWHEREAS, employee is retained.\n\n1. COMPENSATION\n1.1 Salary.\n", "EMPLOYMENT & SEVERANCE AGREEMENT"),
        ("COMMERCIAL CLOUD SERVICES MASTER TERMS\n\nSection 1. DEFINITIONS\n1.1 Customer means the subscriber.\n", "COMMERCIAL CLOUD SERVICES MASTER TERMS"),
    ]
    for text, expected_title in sample_contracts:
        parsed_cs = document_parser.parse_clauses(text, [(1, text)])
        print(f"    Raw Header: '{expected_title}' -> Extracted Title: '{document_parser.document_title}'")
        assert document_parser.document_title == expected_title, f"Expected '{expected_title}', got '{document_parser.document_title}'"
        assert not any(c.title == expected_title for c in parsed_cs), f"Title '{expected_title}' was mistakenly parsed as a clause!"

    print("\n================================================================")
    print("ALL VERIFICATIONS PASSED PERFECTLY (100% DYNAMIC, ZERO HARDCODING)!")
    print("================================================================")

if __name__ == "__main__":
    asyncio.run(main())
