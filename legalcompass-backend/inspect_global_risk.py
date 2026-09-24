import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient
from app.main import app

def inspect_chat_path():
    print("=========================================================================")
    print("INSPECTING GLOBAL-RISK CHAT PATH END-TO-END")
    print("Query: 'What are the 5 most materially risky operative provisions in this contract?'")
    print("=========================================================================\n")

    client = TestClient(app)

    # 1. Upload the Stress Test Contract PDF
    pdf_path = os.path.abspath("../LegalCompass_Accuracy_V2_Stress_Test_Contract.pdf")
    print(f"Uploading PDF from: {pdf_path}")
    with open(pdf_path, "rb") as f:
        upload_res = client.post(
            "/api/upload",
            files={"file": ("LegalCompass_Accuracy_V2_Stress_Test_Contract.pdf", f, "application/pdf")},
            data={"user_role": "general"}
        )

    assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
    upload_data = upload_res.json()
    session_id = upload_data.get("session_id") or upload_data.get("sessionId")
    clauses = upload_data.get("clauses", [])

    print(f"\n[UPLOAD RESULT]")
    print(f"Session ID: {session_id}")
    print(f"Total extracted/analyzed clauses: {len(clauses)}")
    print(f"Overall fairness score: {upload_data.get('overall_fairness_score') or upload_data.get('overallFairnessScore')}")
    for idx, c in enumerate(clauses, 1):
        print(f"  {idx}. ID={c.get('id')} | Title='{c.get('title')}' | Kind={c.get('clauseKind') or c.get('clause_kind')} | Risk={c.get('riskLevel') or c.get('risk_level')} | Unfairness={c.get('unfairnessScore') or c.get('unfairness_score')} | isRiskBearing={c.get('isRiskBearing', c.get('is_risk_bearing'))}")

    query = "What are the 5 most materially risky operative provisions in this contract?"

    # 2. Test Path A: With active session (rag_engine.retrieve_chat_context)
    print("\n-------------------------------------------------------------------------")
    print("PATH A: Querying with active session_id in rag_engine")
    print("-------------------------------------------------------------------------")
    chat_payload_a = {
        "sessionId": session_id,
        "message": query,
        "selectedClauseId": None,
    }
    chat_res_a = client.post("/api/chat", json=chat_payload_a)
    assert chat_res_a.status_code == 200, f"Chat failed: {chat_res_a.text}"

    # 3. Test Path B: Without active session (fallback to request.contract_context)
    print("\n-------------------------------------------------------------------------")
    print("PATH B: Querying without active session (frontend contract_context fallback)")
    print("-------------------------------------------------------------------------")
    chat_payload_b = {
        "sessionId": "nonexistent_session_for_fallback",
        "message": query,
        "selectedClauseId": None,
        "contractContext": {
            "filename": "LegalCompass_Accuracy_V2_Stress_Test_Contract.pdf",
            "overallFairnessScore": upload_data.get("overall_fairness_score") or upload_data.get("overallFairnessScore"),
            "clauses": clauses,
        }
    }
    chat_res_b = client.post("/api/chat", json=chat_payload_b)
    assert chat_res_b.status_code == 200, f"Chat failed: {chat_res_b.text}"

    print("\n=========================================================================")
    print("INSPECTION RUN COMPLETE")
    print("=========================================================================")

if __name__ == "__main__":
    inspect_chat_path()
