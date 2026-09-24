"""
Verification script for LegalCompass Backend API.
Tests all endpoints:
1. GET /health
2. POST /api/upload
3. POST /api/chat
4. POST /api/simulate-scenario
5. POST /api/export-brief
"""
import sys
import io

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient
from app.main import app

def run_tests():
    print("=== LegalCompass Backend Verification Suite ===")
    client = TestClient(app)

    # 1. Health Check
    print("\n[1/5] Testing GET /health ...")
    res = client.get("/health")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    print(f" -> Status: {data.get('status')}")
    print(f" -> Gemini Model: {data.get('gemini_model_id')}")
    print(f" -> Groq Model: {data.get('groq_model_id')}")
    print(f" -> Providers: {data.get('providers')}")
    assert "gemini_model_id" in data
    assert "groq_model_id" in data
    print(" [PASS] Health check verified!")

    # 2. Upload Endpoint (Real PDF via pdfplumber)
    print("\n[2/5] Testing POST /api/upload (PDF with pdfplumber extraction) ...")
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=letter)
    c.drawString(50, 750, "MASTER SERVICES AGREEMENT")
    c.drawString(50, 720, "1. Scope of Work: Contractor provides software architecture services.")
    c.drawString(50, 690, "2. Payment Terms: Client pays within 90 days after delivery approval.")
    c.drawString(50, 660, "3. Intellectual Property: Contractor forfeits all rights upon creation.")
    c.drawString(50, 630, "4. Termination: Client may terminate at will without notice or penalty.")
    c.drawString(50, 600, "5. Indemnification: Contractor provides unlimited uncapped indemnity.")
    c.showPage()
    c.save()
    pdf_bytes = pdf_buffer.getvalue()

    files = {"file": ("test_master_agreement.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    res = client.post("/api/upload", files=files)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    res_json = res.json()
    session_id = res_json.get("session_id") or res_json.get("sessionId")
    clauses = res_json.get("clauses", [])
    fairness_score = res_json.get("overall_fairness_score") or res_json.get("overallFairnessScore")
    print(f" -> Session ID: {session_id}")
    print(f" -> Extracted Clauses via pdfplumber: {len(clauses)}")
    print(f" -> Overall Fairness Score: {fairness_score}")
    assert session_id is not None
    assert len(clauses) >= 1
    assert fairness_score is not None

    for c in clauses:
        has_start = "start_offset" in c or "startOffset" in c
        has_end = "end_offset" in c or "endOffset" in c
        has_page = "page_number" in c or "pageNumber" in c
        assert has_start and has_end and has_page, f"Clause {c.get('id')} missing offset metadata"
    print(" -> Verified: All clauses contain start_offset, end_offset, and page_number metadata in API JSON")
    print(" [PASS] Real PDF upload, pdfplumber extraction, and offset serialization verified!")

    # 3. Chat Endpoint (SSE)
    print("\n[3/5] Testing POST /api/chat (SSE Stream) ...")
    chat_payload = {
        "sessionId": session_id,
        "message": "What are the biggest risks regarding intellectual property in this agreement?",
        "history": []
    }
    with client.stream("POST", "/api/chat", json=chat_payload) as stream_res:
        assert stream_res.status_code == 200, f"Expected 200, got {stream_res.status_code}"
        chunks = []
        for line in stream_res.iter_lines():
            if line:
                chunks.append(line)
        print(f" -> Received {len(chunks)} SSE data lines")
        assert len(chunks) > 0
    print(" [PASS] Chat SSE streaming verified!")

    # 4. What-If Simulation Endpoint
    print("\n[4/5] Testing POST /api/simulate-scenario ...")
    sim_payload = {
        "sessionId": session_id,
        "scenarioPrompt": "What if the client cancels the contract midway after 3 months of work?"
    }
    res = client.post("/api/simulate-scenario", json=sim_payload)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    sim_data = res.json()
    print(f" -> Scenario Title: {sim_data.get('scenario_title') or sim_data.get('scenarioTitle')}")
    print(f" -> Risk Level: {sim_data.get('risk_level') or sim_data.get('riskLevel')}")
    print(f" -> Risk Evaluation: {str(sim_data.get('risk_evaluation') or sim_data.get('riskEvaluation'))[:80]}...")
    print(f" -> Financial Exposure: {str(sim_data.get('financial_exposure') or sim_data.get('financialExposure'))[:80]}...")
    print(f" -> Recommended Action: {str(sim_data.get('recommended_action') or sim_data.get('recommendedAction'))[:80]}...")
    assert "risk_level" in sim_data or "riskLevel" in sim_data
    print(" [PASS] Scenario simulation verified!")

    # 5. Export Brief Endpoint
    print("\n[5/5] Testing POST /api/export-brief ...")
    export_payload = {
        "sessionId": session_id,
        "includeCitations": True,
        "customNotes": "Review indemnity clause urgently."
    }
    res = client.post("/api/export-brief", json=export_payload)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    assert res.headers.get("content-type") == "application/pdf"
    pdf_size = len(res.content)
    print(f" -> Generated PDF Size: {pdf_size} bytes")
    assert pdf_size > 1000
    print(" [PASS] Attorney Brief PDF export verified!")

    print("\n================================================")
    print(" ALL 5 BACKEND VERIFICATION TESTS PASSED SUCCESSFULLY! ")
    print("================================================")

if __name__ == "__main__":
    run_tests()
