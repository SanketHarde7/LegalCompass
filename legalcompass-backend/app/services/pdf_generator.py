import io
from datetime import datetime, timezone
from typing import List, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from app.schemas.contract import ContractDocument


def generate_attorney_brief_pdf(
    document: ContractDocument, custom_notes: Optional[str] = None
) -> bytes:
    """Generates an attorney-ready, single-to-two-page PDF memorandum using ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    # Custom typography
    header_small = ParagraphStyle(
        "HeaderSmall",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#78716c"),
    )

    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1c1917"),
    )

    h2_style = ParagraphStyle(
        "H2Style",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1c1917"),
        spaceBefore=10,
        spaceAfter=4,
    )

    body_style = ParagraphStyle(
        "BodyStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#44403c"),
    )

    code_style = ParagraphStyle(
        "CodeStyle",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1c1917"),
    )

    disclaimer_style = ParagraphStyle(
        "DisclaimerStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#78716c"),
    )

    story = []

    # 1. Header Stamp
    story.append(Paragraph("LEGALCOMPASS &bull; PRE-CONSULTATION RISK ASSESSMENT &bull; CONFIDENTIAL", header_small))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Legal Risk Audit Memorandum", title_style))
    story.append(Spacer(1, 8))

    # 2. Metadata Grid Table
    date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    high_count = sum(1 for c in document.clauses if c.risk_level == "HIGH")
    med_count = sum(1 for c in document.clauses if c.risk_level == "MEDIUM")

    meta_data = [
        [
            Paragraph(f"<b>Contract:</b> {document.filename}", body_style),
            Paragraph(f"<b>Date:</b> {date_str}", body_style),
        ],
        [
            Paragraph(f"<b>Fairness Score:</b> {document.overall_fairness_score}/100", body_style),
            Paragraph(f"<b>Identified Imbalances:</b> {high_count} High &bull; {med_count} Med", body_style),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[260, 260])
    meta_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f5f5f4")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e7e5e4")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e7e5e4")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    story.append(meta_table)
    story.append(Spacer(1, 8))

    # 3. Non-Advice Disclaimer Banner
    disclaimer_text = (
        "<b>NON-ADVICE LEGAL DISCLAIMER:</b> Prepared for informational and attorney preparation purposes only under "
        "the LegalCompass open evaluation model. Does not constitute formal legal representation or statutory advice."
    )
    disc_data = [[Paragraph(disclaimer_text, disclaimer_style)]]
    disc_table = Table(disc_data, colWidths=[520])
    disc_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fffbeb")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#fde68a")),
            ("PADDING", (0, 0), (-1, -1), 6),
        ])
    )
    story.append(disc_table)
    story.append(Spacer(1, 8))

    # 4. Section 1: Executive Risk Summary
    story.append(Paragraph("&sect; 1. Executive Risk &amp; Exposure Summary", h2_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#d6d3d1"), spaceAfter=6))

    high_risk_clauses = [c for c in document.clauses if c.risk_level == "HIGH"]
    if high_risk_clauses:
        for c in high_risk_clauses[:3]:
            bullet = f"&bull; <b>{c.title}:</b> {c.plain_english_summary}"
            story.append(Paragraph(bullet, body_style))
            story.append(Spacer(1, 4))
    else:
        story.append(Paragraph("No critical high-risk traps identified.", body_style))
        story.append(Spacer(1, 4))

    # 5. Section 2: Targeted Questions for Licensed Counsel
    story.append(Paragraph("&sect; 2. Targeted Negotiation Questions for Licensed Counsel", h2_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#d6d3d1"), spaceAfter=6))

    sample_questions = [
        "Can we condition all intellectual property transfers strictly upon full receipt of invoiced compensation?",
        "Can we negotiate a mutual 30-day notice period for termination and eliminate unbilled hours forfeiture?",
        "Can we cap aggregate indemnification liability to the total fees actually collected under this agreement?",
        "What objective acceptance criteria can we establish to prevent arbitrary fee withholding under subjective satisfaction clauses?",
    ]
    for idx, q in enumerate(sample_questions, start=1):
        q_text = f"<b>{idx}.</b> <i>\"{q}\"</i>"
        story.append(Paragraph(q_text, body_style))
        story.append(Spacer(1, 3))

    # 6. Section 3: Proposed Counter-Language Appendix
    counter_clauses = [c for c in document.clauses if c.suggested_pushback]
    if counter_clauses:
        story.append(Paragraph("&sect; 3. Proposed Counter-Language Appendix", h2_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#d6d3d1"), spaceAfter=6))

        for c in counter_clauses[:2]:
            c_header = f"<b>{c.title}</b> (Target: {c.risk_level} Risk)"
            story.append(Paragraph(c_header, body_style))
            story.append(Spacer(1, 2))

            code_data = [[Paragraph(f'"{c.suggested_pushback}"', code_style)]]
            code_table = Table(code_data, colWidths=[520])
            code_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fafaf9")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e7e5e4")),
                    ("PADDING", (0, 0), (-1, -1), 6),
                ])
            )
            story.append(code_table)
            story.append(Spacer(1, 6))

    # Footer certification
    story.append(Spacer(1, 10))
    cert_text = f"AUDIT HASH: {document.session_id} &bull; PREPARED VIA LEGALCOMPASS"
    story.append(Paragraph(cert_text, disclaimer_style))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
