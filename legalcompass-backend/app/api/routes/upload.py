from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from typing import Optional
from app.core.config import settings
from app.schemas.contract import UploadContractResponse, ContractDocument
from app.services.document_parser import document_parser
from app.services.rag_engine import rag_engine
from app.services.llm_service import llm_service
import asyncio
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/upload",
    response_model=UploadContractResponse,
    summary="Upload and analyze a contract document",
)
async def upload_contract(
    file: UploadFile = File(...),
    user_role: Optional[str] = Form("general"),
):
    """Parses PDF/DOCX contracts, segments clauses, evaluates risks, and indexes into memory."""
    filename = file.filename or "uploaded_contract.pdf"
    lower_name = filename.lower()

    # 1. Validate File Extension
    if not (lower_name.endswith(".pdf") or lower_name.endswith(".docx") or lower_name.endswith(".txt")):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={
                "code": "INVALID_FILE_TYPE",
                "message": "Only PDF (.pdf), Word (.docx), and text (.txt) documents are supported.",
            },
        )

    # 2. Read file bytes and validate size (< 25MB)
    file_bytes = await file.read()
    file_size = len(file_bytes)

    if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": f"File exceeds the {settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB boundary.",
            },
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "EMPTY_FILE",
                "message": "Uploaded file is empty.",
            },
        )

    # 3. Parse Document Content
    try:
        if lower_name.endswith(".pdf"):
            full_text, pages_content = document_parser.extract_from_pdf(file_bytes)
        elif lower_name.endswith(".docx"):
            full_text, pages_content = document_parser.extract_from_docx(file_bytes)
        else:
            full_text, pages_content = document_parser.extract_from_txt(file_bytes)

        if not full_text.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "PARSING_FAILED",
                    "message": "Could not extract readable text. The document may be an unscanned image.",
                },
            )

        initial_clauses = document_parser.parse_clauses(full_text, pages_content)

        # Validate that the document is actually a legal agreement / contract
        legal_keywords = [
            "agreement", "contract", "parties", "party", "terms", "covenant",
            "section", "clause", "shall", "indemnif", "liability", "termination",
            "warranty", "governing law", "jurisdiction", "confidential", "breach",
            "recitals", "whereas", "in consideration", "obligations", "intellectual property",
            "tenant", "landlord", "contractor", "client", "employee", "employer", "licensor",
        ]
        lower_full = full_text.lower()
        matched_keywords = sum(1 for kw in legal_keywords if kw in lower_full)

        if matched_keywords < 3 or len(initial_clauses) == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "NOT_A_LEGAL_CONTRACT",
                    "message": (
                        "The uploaded file does not appear to be a legal contract or agreement. "
                        "LegalCompass is specifically designed to analyze agreements (such as Master Services Agreements, "
                        "Residential Leases, NDAs, or Terms of Service) with enforceable contractual terms. "
                        "Please upload a valid legal document."
                    ),
                },
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to parse document {filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "PARSING_FAILED",
                "message": f"Document parsing failed: {str(e)}",
            },
        )

    # 4. LLM / Heuristic Clause Analysis & Risk Evaluation
    try:
        analyzed_doc = await llm_service.analyze_contract(
            raw_text=full_text,
            filename=filename,
            initial_clauses=initial_clauses,
            pages_content=pages_content,
            document_title=document_parser.document_title,
        )
    except Exception as e:
        logger.error(f"LLM contract analysis failed: {e}")
        # Use heuristic fallback
        session_id = f"sess_{int(file_size)}_{abs(hash(filename)) % 1000}"
        from app.schemas.contract import PageContent
        page_objects = [PageContent(pageNumber=idx, text=txt) for idx, txt in pages_content]
        analyzed_doc = llm_service._heuristic_analysis(
            session_id, filename, initial_clauses, page_objects, document_title=document_parser.document_title
        )

    # 5. Index Clauses in FastEmbed in-memory RAG
    try:
        await asyncio.to_thread(
            rag_engine.index_document,
            session_id=analyzed_doc.session_id,
            filename=filename,
            clauses=analyzed_doc.clauses,
            overall_fairness_score=analyzed_doc.overall_fairness_score,
        )
    except Exception as e:
        logger.warning(f"Failed to index document in RAG engine: {e}")

    # 6. Return response matching docs/contracts.md + ContractDocument compatibility
    return UploadContractResponse(
        session_id=analyzed_doc.session_id,
        sessionId=analyzed_doc.session_id,
        filename=filename,
        file_size_bytes=file_size,
        uploaded_at=analyzed_doc.upload_timestamp,
        uploadTimestamp=analyzed_doc.upload_timestamp,
        total_clauses=len(analyzed_doc.clauses),
        overall_fairness_score=analyzed_doc.overall_fairness_score,
        overallFairnessScore=analyzed_doc.overall_fairness_score,
        total_pages=analyzed_doc.total_pages,
        totalPages=analyzed_doc.total_pages,
        pages=analyzed_doc.pages,
        document_title=analyzed_doc.document_title,
        documentTitle=analyzed_doc.document_title,
        summary_overview=(
            f"Analyzed {len(analyzed_doc.clauses)} clauses across {analyzed_doc.total_pages} pages. Overall fairness score is "
            f"{analyzed_doc.overall_fairness_score}/100."
        ),
        clauses=analyzed_doc.clauses,
        document=analyzed_doc,
    )
