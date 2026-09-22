from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from app.services.rag_engine import rag_engine
from app.services.pdf_generator import generate_attorney_brief_pdf
from app.schemas.contract import ContractDocument, Clause

router = APIRouter()


class ExportBriefRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session_id: str = Field(alias="sessionId", description="Active session UUID")
    custom_notes: Optional[str] = Field(
        default=None, alias="customNotes", description="Optional user questions or notes"
    )


@router.post(
    "/export-brief",
    summary="Compiles the parsed contract and risk summary into an attorney consultation PDF",
)
async def export_brief(request: ExportBriefRequest):
    """Generates an attorney-ready 1-page PDF memorandum."""
    session_id = request.session_id
    session = rag_engine.get_session(session_id)

    if not session or not session.clauses:
        # Construct fallback contract document if session was evicted
        fallback_doc = ContractDocument(
            sessionId=session_id,
            filename="Contract_Risk_Brief.pdf",
            uploadTimestamp="",
            overallFairnessScore=50,
            clauses=[
                Clause(
                    id="clause_1",
                    index=1,
                    title="General Contract Provisions",
                    text="Contract terms reviewed by LegalCompass.",
                    riskLevel="MEDIUM",
                    category="OTHER",
                    plainSummary="General provisions requiring attorney review.",
                    unfairnessScore=50,
                )
            ],
        )
        pdf_bytes = generate_attorney_brief_pdf(fallback_doc, request.custom_notes)
    else:
        doc = ContractDocument(
            sessionId=session.session_id,
            filename=session.filename,
            uploadTimestamp="",
            overallFairnessScore=50,
            clauses=session.clauses,
        )
        pdf_bytes = generate_attorney_brief_pdf(doc, request.custom_notes)

    filename = f"LegalCompass_Attorney_Brief_{session_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
