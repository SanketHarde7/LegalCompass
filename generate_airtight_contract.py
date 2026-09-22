import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    HRFlowable,
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """Canvas that computes total pages dynamically and prints running header and footer."""
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#78716c"))

        # Running Header (pages 2+)
        if self._pageNumber > 1:
            self.drawString(54, 750, "AIRTIGHT COMMERCIAL MASTER SERVICES AGREEMENT (MSA)")
            self.drawRightString(612 - 54, 750, "STANDARD LOOPHOLE-FREE TEMPLATE")
            self.setStrokeColor(colors.HexColor("#e7e5e4"))
            self.setLineWidth(0.5)
            self.line(54, 744, 612 - 54, 744)

        # Running Footer (all pages)
        self.setStrokeColor(colors.HexColor("#e7e5e4"))
        self.setLineWidth(0.5)
        self.line(54, 48, 612 - 54, 48)
        self.drawString(54, 36, "CONFIDENTIAL & PROPRIETARY • BALANCED RECIPROCAL LEGAL TERMS")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(612 - 54, 36, page_str)
        self.restoreState()


def create_airtight_contract(output_pdf_path):
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=64,
        bottomMargin=60,
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=25,
        textColor=colors.HexColor("#1c1917"),
        alignment=1, # Center
        spaceAfter=6,
    )

    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=16,
        textColor=colors.HexColor("#57534e"),
        alignment=1,
        spaceAfter=14,
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11.5,
        leading=15,
        textColor=colors.HexColor("#1c1917"),
        spaceBefore=10,
        spaceAfter=5,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#292524"),
        spaceBefore=6,
        spaceAfter=4,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        'LegalBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.8,
        leading=13.2,
        textColor=colors.HexColor("#292524"),
        spaceAfter=6,
        alignment=4, # Justified
    )

    table_text_style = ParagraphStyle(
        'TableText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11.5,
        textColor=colors.HexColor("#292524"),
    )

    table_text_bold = ParagraphStyle(
        'TableTextBold',
        parent=table_text_style,
        fontName='Helvetica-Bold',
    )

    story = []

    # =========================================================================
    # PAGE 1: TITLE, EXECUTIVE METRICS, FAIRNESS BOX & 2-COLUMN ROADMAP
    # =========================================================================
    story.append(Spacer(1, 10))
    story.append(Paragraph("MASTER SERVICES &amp; PROFESSIONAL AGREEMENT", title_style))
    story.append(Paragraph("A Balanced, Reciprocal, and Legally Airtight Commercial Framework", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.2, color=colors.HexColor("#1c1917"), spaceAfter=14))

    summary_box = [
        [Paragraph("<b>Contract Type:</b>", table_text_style), Paragraph("Enterprise Commercial Master Services Agreement (MSA)", table_text_style)],
        [Paragraph("<b>Governing Principle:</b>", table_text_style), Paragraph("Loophole-Free, Bilateral Obligations &amp; Fair Risk Allocation", table_text_style)],
        [Paragraph("<b>Effective Date:</b>", table_text_style), Paragraph("October 1, 2026", table_text_style)],
        [Paragraph("<b>Applicable Parties:</b>", table_text_style), Paragraph("Client Global Enterprises, Inc. &amp; Contractor Solutions LLC", table_text_style)],
        [Paragraph("<b>Fairness Score:</b>", table_text_style), Paragraph("<font color='#059669'><b>100 / 100 • Certified Zero Predatory Clauses</b></font>", table_text_style)],
    ]
    summary_table = Table(summary_box, colWidths=[130, 374])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 14))

    # Core Safeguards Assurance Highlight
    safeguards_data = [
        [
            Paragraph("<b>LOOPHOLE-FREE COVENANT GUARANTEES:</b><br/>"
                      "• <b>Objective Acceptance:</b> Deemed acceptance within 10 days; subjective aesthetic rejection prohibited.<br/>"
                      "• <b>Net-30 Certainty:</b> Strict 30-day payment timeline with 1.5% monthly late interest and suspension rights.<br/>"
                      "• <b>Conditional IP Transfer:</b> Title to deliverables transfers ONLY upon cleared payment in full.<br/>"
                      "• <b>Mutual Liability Protections:</b> 12-month trailing fee cap with bilateral consequential damages waiver.<br/>"
                      "• <b>Exit Fairness:</b> 30-day mutual notice with mandatory full compensation for in-progress work.", table_text_style)
        ]
    ]
    safeguards_table = Table(safeguards_data, colWidths=[504])
    safeguards_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f0fdf4")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#86efac")),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(safeguards_table)
    story.append(Spacer(1, 14))

    story.append(Paragraph("<b>CONTRACT ROADMAP &amp; TABLE OF CONTENTS</b>", h2_style))
    
    # 2-Column TOC layout ensuring clean fit on Page 1
    toc_data = [
        [
            Paragraph("<b>Sec. 1:</b> Recitals &amp; Intent", table_text_bold), Paragraph("Page 2", table_text_style),
            Paragraph("<b>Sec. 10:</b> Background IP &amp; OSS", table_text_bold), Paragraph("Page 6", table_text_style),
        ],
        [
            Paragraph("<b>Sec. 2:</b> Legal Definitions", table_text_bold), Paragraph("Page 2", table_text_style),
            Paragraph("<b>Sec. 11:</b> Mutual Confidentiality", table_text_bold), Paragraph("Page 7", table_text_style),
        ],
        [
            Paragraph("<b>Sec. 3:</b> SOW &amp; Scope of Work", table_text_bold), Paragraph("Page 3", table_text_style),
            Paragraph("<b>Sec. 12:</b> Data Privacy &amp; Security", table_text_bold), Paragraph("Page 7", table_text_style),
        ],
        [
            Paragraph("<b>Sec. 4:</b> Change Management", table_text_bold), Paragraph("Page 3", table_text_style),
            Paragraph("<b>Sec. 13:</b> Express Warranties", table_text_bold), Paragraph("Page 8", table_text_style),
        ],
        [
            Paragraph("<b>Sec. 5:</b> Objective Acceptance", table_text_bold), Paragraph("Page 4", table_text_style),
            Paragraph("<b>Sec. 14:</b> Mutual Liability Cap", table_text_bold), Paragraph("Page 8", table_text_style),
        ],
        [
            Paragraph("<b>Sec. 6:</b> Rejection &amp; Cure Cycles", table_text_bold), Paragraph("Page 4", table_text_style),
            Paragraph("<b>Sec. 15:</b> Term &amp; Termination", table_text_bold), Paragraph("Page 9", table_text_style),
        ],
        [
            Paragraph("<b>Sec. 7:</b> Invoicing &amp; Net-30", table_text_bold), Paragraph("Page 5", table_text_style),
            Paragraph("<b>Sec. 16:</b> Guaranteed WIP Payout", table_text_bold), Paragraph("Page 9", table_text_style),
        ],
        [
            Paragraph("<b>Sec. 8:</b> Expenses &amp; Remedies", table_text_bold), Paragraph("Page 5", table_text_style),
            Paragraph("<b>Sec. 17:</b> Neutral Arbitration", table_text_bold), Paragraph("Page 10", table_text_style),
        ],
        [
            Paragraph("<b>Sec. 9:</b> Conditional IP Transfer", table_text_bold), Paragraph("Page 6", table_text_style),
            Paragraph("<b>Sec. 18:</b> Signatures &amp; Execution", table_text_bold), Paragraph("Page 10", table_text_style),
        ],
    ]
    toc_table = Table(toc_data, colWidths=[180, 66, 192, 66])
    toc_table.setStyle(TableStyle([
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(toc_table)
    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: RECITALS & DEFINITIONS (SECTIONS 1 & 2)
    # =========================================================================
    story.append(Paragraph("SECTION 1: RECITALS AND PARTIES", h1_style))
    story.append(Paragraph(
        "This Master Services Agreement (\"Agreement\") is made and entered into as of October 1, 2026 (\"Effective Date\") by and between <b>Client Global Enterprises, Inc.</b>, a Delaware corporation having its principal executive offices at 100 Corporate Plaza, Suite 400, New York, NY (\"Client\"), and <b>Contractor Solutions LLC</b>, a California limited liability company having its principal place of business at 500 Innovation Way, San Francisco, CA (\"Contractor\"). Client and Contractor are each referred to individually as a \"Party\" and collectively as the \"Parties.\"",
        body_style
    ))
    story.append(Paragraph(
        "<b>WHEREAS</b>, Client desires to retain Contractor from time to time to perform specialized professional consulting, software engineering, systems architecture, and technical services pursuant to discrete Statements of Work;",
        body_style
    ))
    story.append(Paragraph(
        "<b>WHEREAS</b>, Contractor possesses specialized skill, experience, proprietary background knowledge, and personnel capable of rendering such professional services efficiently and in accordance with highest commercial standards; and",
        body_style
    ))
    story.append(Paragraph(
        "<b>WHEREAS</b>, both Parties desire to establish a transparent, balanced, and reciprocal contractual framework that eliminates predatory terms, ensures prompt remuneration, guarantees mutual liability protection, and fairly distributes intellectual property rights;",
        body_style
    ))
    story.append(Paragraph(
        "<b>NOW, THEREFORE</b>, in consideration of the mutual covenants, representations, and warranties herein contained and other good and valuable consideration, the receipt and adequacy of which are hereby acknowledged, the Parties agree as follows:",
        body_style
    ))

    story.append(Spacer(1, 4))
    story.append(Paragraph("SECTION 2: DEFINITIONS AND INTERPRETATION", h1_style))
    story.append(Paragraph(
        "<b>2.1 \"Acceptance Criteria\"</b> means the objective, measurable, and unambiguous technical specifications, performance benchmarks, and functional acceptance requirements expressly enumerated in an applicable Statement of Work.",
        body_style
    ))
    story.append(Paragraph(
        "<b>2.2 \"Affiliate\"</b> means any entity that directly or indirectly controls, is controlled by, or is under common control with a Party, where control means beneficial ownership of more than fifty percent (50%) of voting securities or managerial control.",
        body_style
    ))
    story.append(Paragraph(
        "<b>2.3 \"Background IP\"</b> means all pre-existing works of authorship, software, algorithms, code libraries, frameworks, know-how, patents, trade secrets, and proprietary tools developed, owned, or licensed by Contractor prior to the Effective Date or developed independently outside the scope of Services without use of Client Materials.",
        body_style
    ))
    story.append(Paragraph(
        "<b>2.4 \"Change Order\"</b> means a written amendment to an active Statement of Work mutually agreed upon and executed by authorized representatives of both Parties in accordance with Section 4.",
        body_style
    ))
    story.append(Paragraph(
        "<b>2.5 \"Client Materials\"</b> means all data, documentation, systems, software, trade secrets, and proprietary information supplied by Client to Contractor solely to enable performance of Services.",
        body_style
    ))
    story.append(Paragraph(
        "<b>2.6 \"Deliverables\"</b> means the specific software modules, reports, designs, and work product required to be created and delivered by Contractor to Client as expressly specified in an executed Statement of Work.",
        body_style
    ))
    story.append(Paragraph(
        "<b>2.7 \"Gross Negligence\"</b> means a conscious, voluntary act or omission in reckless disregard of legal duties and the safety or rights of others, as recognized under governing commercial law.",
        body_style
    ))
    story.append(Paragraph(
        "<b>2.8 \"Statement of Work\" or \"SOW\"</b> means a mutually executed document substantially in the form attached hereto as Exhibit A, incorporating the terms of this Agreement and defining specific Services, schedules, milestones, and fees.",
        body_style
    ))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 3: STATEMENTS OF WORK & CHANGE CONTROL (SECTIONS 3 & 4)
    # =========================================================================
    story.append(Paragraph("SECTION 3: STATEMENTS OF WORK & SCOPE OF SERVICES", h1_style))
    story.append(Paragraph(
        "<b>3.1 Ordering Procedure:</b> Services shall be commissioned through discrete Statements of Work mutually executed by authorized signatories of both Parties. Each SOW shall reference this Agreement and set forth: (a) description of Services; (b) designated milestones and delivery dates; (c) objective Acceptance Criteria; (d) compensation structure (Time &amp; Materials or Fixed Fee); and (e) designated key personnel, if any.",
        body_style
    ))
    story.append(Paragraph(
        "<b>3.2 Primacy of Documents:</b> In the event of an explicit conflict between this Master Services Agreement and any Statement of Work, the terms of this Agreement shall strictly control and prevail, unless the SOW expressly identifies the specific section of this Agreement to be superseded with language explicitly stating \"The Parties intend to override Section [X] of the Master Services Agreement.\"",
        body_style
    ))
    story.append(Paragraph(
        "<b>3.3 Independent Contractor Status:</b> Contractor is an independent contractor. Neither Contractor nor any of Contractor's employees, agents, or subcontractors shall be deemed employees, partners, joint venturers, or agents of Client. Contractor maintains sole responsibility for payment of all federal, state, and local taxes, worker's compensation, unemployment insurance, and fringe benefits for its personnel.",
        body_style
    ))
    story.append(Paragraph(
        "<b>3.4 Mutual Non-Exclusivity:</b> This Agreement is strictly non-exclusive. Contractor retains the complete right to perform services, develop software, and execute consulting engagements for other third parties, including entities operating in Client's general industry, provided Contractor does not disclose or utilize Client's Confidential Information.",
        body_style
    ))

    story.append(Spacer(1, 6))
    story.append(Paragraph("SECTION 4: CHANGE MANAGEMENT & SCOPE ADJUSTMENTS", h1_style))
    story.append(Paragraph(
        "<b>4.1 Change Request Procedure:</b> Either Party may at any time propose modifications, expansions, or reductions to the Services, Deliverables, or schedules described in an active SOW by submitting a written \"Change Request.\" Contractor is under no legal obligation to perform out-of-scope work until a formal Change Order has been fully executed.",
        body_style
    ))
    story.append(Paragraph(
        "<b>4.2 Impact Assessment:</b> Promptly upon receipt or generation of a Change Request (and in no event later than five (5) business days), Contractor shall deliver a written assessment specifying: (a) necessary modifications to technical architecture; (b) required schedule extensions; (c) impact on existing milestones; and (d) additional associated costs or hourly rate adjustments.",
        body_style
    ))
    story.append(Paragraph(
        "<b>4.3 Authorization Required:</b> No oral conversation, email communication, or unilateral direction from Client shall alter the scope or price of any SOW. A Change Order shall become legally binding strictly upon mutual electronic or physical signature of authorized executives of both Parties.",
        body_style
    ))
    story.append(Paragraph(
        "<b>4.4 Client Delay Protection:</b> If Contractor's performance of Services is delayed or prevented due to Client's failure to furnish required Client Materials, timely approvals, credential access, or technical environment access (\"Client Delay\"), all affected delivery milestones shall be automatically extended day-for-day without penalty to Contractor. Client shall reimburse Contractor for any reasonable idle standby costs incurred as a direct consequence of a Client Delay exceeding five (5) consecutive business days.",
        body_style
    ))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 4: OBJECTIVE ACCEPTANCE TESTING & REJECTION (SECTIONS 5 & 6)
    # =========================================================================
    story.append(Paragraph("SECTION 5: MILESTONE DELIVERY & OBJECTIVE ACCEPTANCE TESTING", h1_style))
    story.append(Paragraph(
        "<b>5.1 Delivery Notice:</b> Upon completion of each Deliverable or milestone specified in a Statement of Work, Contractor shall deliver the Deliverable to Client accompanied by a written or electronic \"Delivery Notice.\" Deliverables shall be furnished in source code repository format, compiled binary, or interactive staging environment as designated in the applicable SOW.",
        body_style
    ))
    story.append(Paragraph(
        "<b>5.2 Review Window:</b> Client shall have a standard period of ten (10) business days following receipt of the Delivery Notice (\"Acceptance Period\") to review and verify that the Deliverable materially conforms to the objective Acceptance Criteria set forth in the SOW. The Acceptance Period may be extended only by mutual written agreement.",
        body_style
    ))
    story.append(Paragraph(
        "<b>5.3 Formal Acceptance:</b> Client shall confirm acceptance by executing and transmitting a written \"Acceptance Certificate\" or email confirmation to Contractor. Acceptance shall signify that the Deliverable satisfies all agreed technical benchmarks.",
        body_style
    ))
    story.append(Paragraph(
        "<b>5.4 Deemed Acceptance Safeguard:</b> If Client fails to provide either written approval or a specific, itemized written notice of material non-conformance prior to the expiration of the ten (10) business day Acceptance Period, the Deliverable shall be deemed irrevocably accepted for all purposes under this Agreement. Furthermore, any deployment or productive commercial use of the Deliverable in Client's live production environment shall constitute immediate and conclusive acceptance.",
        body_style
    ))

    story.append(Spacer(1, 6))
    story.append(Paragraph("SECTION 6: REJECTION PROCEDURES & BALANCED CURE CYCLES", h1_style))
    story.append(Paragraph(
        "<b>6.1 Objective Non-Conformance Notice:</b> Client may reject a Deliverable only if it fails materially to satisfy the objective Acceptance Criteria explicitly set forth in the SOW. Subjective dissatisfaction, aesthetic preference, or newly introduced requirements shall not constitute valid legal grounds for rejection. If Client rejects a Deliverable, it must transmit a written \"Notice of Defect\" detailing: (a) the exact Acceptance Criteria failed; (b) reproducible bug logs; and (c) steps required to achieve compliance.",
        body_style
    ))
    story.append(Paragraph(
        "<b>6.2 Contractor Cure Period:</b> Following receipt of a valid Notice of Defect, Contractor shall have fifteen (15) business days (or such longer reasonable period as mutually agreed in writing) to correct the documented non-conformances at no additional fee to Client, and resubmit the revised Deliverable for an expedited five (5) business day verification review.",
        body_style
    ))
    story.append(Paragraph(
        "<b>6.3 Equitable Remedies for Failure to Cure:</b> If Contractor is unable to cure a material defect after two (2) successive cure cycles, Client's sole and exclusive remedy shall be to: (a) grant an additional reasonable remediation window; (b) accept the Deliverable with an equitable, mutually negotiated reduction in fees; or (c) terminate the specific SOW for cause and receive a pro-rated refund of fees paid solely for the non-conforming milestone, provided Client returns or destroys all copies of said non-conforming Deliverable.",
        body_style
    ))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 5: COMPENSATION & NET-30 PAYMENT PROTECTIONS (SECTIONS 7 & 8)
    # =========================================================================
    story.append(Paragraph("SECTION 7: INVOICING, COMPENSATION & PAYMENT TERMS", h1_style))
    story.append(Paragraph(
        "<b>7.1 Invoicing Schedule:</b> Contractor shall invoice Client upon completion and acceptance of milestones (for Fixed Fee engagements) or bi-weekly/monthly in arrears (for Time &amp; Materials engagements), as set forth in the applicable Statement of Work. Each invoice shall itemize services rendered, hours worked, and applicable milestones.",
        body_style
    ))
    story.append(Paragraph(
        "<b>7.2 Net-30 Payment Terms:</b> Client shall pay all undisputed invoice amounts in full within thirty (30) calendar days from the date of invoice transmission (\"Due Date\"). All payments shall be made in United States Dollars (USD) via electronic funds transfer (ACH, wire, or direct bank transfer) to the account designated by Contractor.",
        body_style
    ))
    story.append(Paragraph(
        "<b>7.3 No Subjective Fee Withholding:</b> Client shall have no legal right to set off, discount, or withhold any portion of an invoice based on subjective performance assessments or unrelated disputes. Client may withhold payment solely for specific line items subject to a bona fide written dispute submitted pursuant to Section 7.4.",
        body_style
    ))
    story.append(Paragraph(
        "<b>7.4 Good-Faith Billing Dispute Process:</b> To dispute any invoice item, Client must notify Contractor in writing within ten (10) business days of invoice receipt, articulating with specificity the disputed amounts and mathematical or substantive basis. Undisputed amounts must be remitted by the Due Date. Both Parties shall engage in good-faith executive discussions to resolve the billing dispute within ten (10) business days.",
        body_style
    ))

    story.append(Spacer(1, 6))
    story.append(Paragraph("SECTION 8: EXPENSE REIMBURSEMENT & LATE PAYMENT REMEDIES", h1_style))
    story.append(Paragraph(
        "<b>8.1 Reimbursable Expenses:</b> Client shall reimburse Contractor for all reasonable, pre-approved out-of-pocket travel, accommodation, software licenses, third-party API fees, and cloud hosting disbursements incurred directly in the performance of Services, provided Contractor furnishes standard electronic receipts.",
        body_style
    ))
    story.append(Paragraph(
        "<b>8.2 Late Payment Interest:</b> Any undisputed invoice amount remaining unpaid after thirty (30) calendar days from the invoice date shall accrue interest at the rate of one and one-half percent (1.5%) per month (18% per annum) or the maximum legal rate permissible under applicable law, whichever is lower, calculated daily from the Due Date until paid in full.",
        body_style
    ))
    story.append(Paragraph(
        "<b>8.3 Right to Suspend Services:</b> If Client fails to pay any undisputed invoice within fifteen (15) calendar days following receipt of written overdue notice from Contractor, Contractor reserves the legal right to immediately suspend performance of Services, withhold subsequent Deliverables, and revoke staging access until all past-due balances and accrued interest are settled in cleared funds. Suspension under this Section shall not constitute a breach of this Agreement by Contractor.",
        body_style
    ))
    story.append(Paragraph(
        "<b>8.4 Collection Costs:</b> Client agrees to reimburse Contractor for all reasonable attorney's fees, legal costs, and collection expenses incurred by Contractor in enforcing payment of undisputed delinquent balances.",
        body_style
    ))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 6: INTELLECTUAL PROPERTY & CONDITIONAL ASSIGNMENT (SECTIONS 9 & 10)
    # =========================================================================
    story.append(Paragraph("SECTION 9: INTELLECTUAL PROPERTY & CONDITIONAL ASSIGNMENT", h1_style))
    story.append(Paragraph(
        "<b>9.1 Client Materials Ownership:</b> As between Client and Contractor, Client retains sole and exclusive ownership of all right, title, and interest in and to Client Materials, Client trademarks, and pre-existing Client software. Contractor receives a limited, revocable, non-exclusive license to use Client Materials strictly to perform the Services.",
        body_style
    ))
    story.append(Paragraph(
        "<b>9.2 Conditional Transfer of Deliverables:</b> Subject to Section 9.3 and strictly upon Contractor's receipt of full and complete payment of all invoiced fees and expenses relating to the applicable Deliverable, Contractor hereby assigns, transfers, and conveys to Client all right, title, and interest (including copyright and patent rights) in and to the custom Deliverables specifically created for Client under an executed SOW.",
        body_style
    ))
    story.append(Paragraph(
        "<b>9.3 Essential Non-Forfeiture Safeguard:</b> In no event shall title, ownership, or intellectual property rights in any Deliverable transfer to Client prior to Contractor's receipt of cleared funds. If Client defaults on payment or terminates an SOW without paying for completed Deliverables, all intellectual property rights therein shall remain exclusively with Contractor, and Client shall have zero license or right to utilize, deploy, or reverse-engineer said Deliverables.",
        body_style
    ))
    story.append(Paragraph(
        "<b>9.4 Moral Rights Waiver:</b> Upon receipt of full payment, Contractor waives any moral rights (droit moral) in the Deliverables to the maximum extent permissible under applicable federal and international copyright conventions.",
        body_style
    ))

    story.append(Spacer(1, 6))
    story.append(Paragraph("SECTION 10: BACKGROUND IP & OPEN-SOURCE CARVE-OUTS", h1_style))
    story.append(Paragraph(
        "<b>10.1 Retention of Background IP:</b> Contractor retains sole and exclusive ownership of all Background IP, pre-existing libraries, utility tools, algorithms, and general software architecture developed by Contractor prior to or independently of this Agreement. Nothing in this Agreement shall operate to transfer ownership of Contractor's Background IP to Client.",
        body_style
    ))
    story.append(Paragraph(
        "<b>10.2 Perpetual Client License to Background IP:</b> To the extent Contractor incorporates any Background IP into a Deliverable, Contractor hereby grants to Client a perpetual, irrevocable, worldwide, non-exclusive, fully paid-up, royalty-free license to use, execute, reproduce, display, and perform such Background IP solely as integrated within and necessary for the intended operation of the Deliverable. Client may not sub-license, extract, or sell Background IP on a standalone basis.",
        body_style
    ))
    story.append(Paragraph(
        "<b>10.3 Open-Source Software Compliance:</b> Contractor shall not incorporate into any Deliverable any Open-Source Software governed by copyleft or restrictive public licenses (e.g., GNU GPL, AGPL) that would require Client to publish, disclose, or license its proprietary source code to third parties, without Client's prior written consent. Permissible permissive open-source packages (e.g., MIT, Apache 2.0, BSD) are expressly authorized.",
        body_style
    ))
    story.append(Paragraph(
        "<b>10.4 General Know-How & Residual Rights:</b> Contractor shall remain free to use general concepts, algorithmic techniques, ideas, and professional know-how retained in the unaided memory of Contractor's personnel in the course of future consulting or software development engagements.",
        body_style
    ))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 7: RECIPROCAL CONFIDENTIALITY & DATA PROTECTION (SECTIONS 11 & 12)
    # =========================================================================
    story.append(Paragraph("SECTION 11: RECIPROCAL CONFIDENTIALITY & TRADE SECRETS", h1_style))
    story.append(Paragraph(
        "<b>11.1 Definition of Confidential Information:</b> \"Confidential Information\" means all non-public, proprietary, or sensitive technical, commercial, financial, and legal information disclosed by one Party (\"Disclosing Party\") to the other Party (\"Receiving Party\"), whether orally, visually, or in writing, that is designated as confidential or that reasonably should be understood to be confidential given the nature of the information and circumstances of disclosure.",
        body_style
    ))
    story.append(Paragraph(
        "<b>11.2 Standard of Care:</b> The Receiving Party shall protect the Disclosing Party's Confidential Information with the same degree of care it uses to protect its own confidential materials of like importance, but in no event less than a reasonable standard of care. Receiving Party shall not use Confidential Information for any purpose outside the scope of this Agreement.",
        body_style
    ))
    story.append(Paragraph(
        "<b>11.3 Permitted Disclosees:</b> Receiving Party may disclose Confidential Information solely to its employees, subcontractors, legal counsel, accountants, and financial advisors (\"Representatives\") who have a strict need to know and are bound by confidentiality obligations at least as restrictive as those herein.",
        body_style
    ))
    story.append(Paragraph(
        "<b>11.4 Specific Exclusions:</b> Confidential Information does not include information that: (a) is or becomes publicly known through no breach of Receiving Party; (b) was already known to Receiving Party prior to disclosure without confidentiality restrictions; (c) is independently developed without reference to Disclosing Party's information; or (d) is received rightfully from a third party without duty of confidentiality.",
        body_style
    ))
    story.append(Paragraph(
        "<b>11.5 Compelled Legal Process:</b> If Receiving Party is legally compelled by court subpoena, regulatory authority, or civil order to disclose Confidential Information, it shall provide prompt written notice to Disclosing Party (where legally permissible) to enable Disclosing Party to seek a protective order or appropriate quashing remedy.",
        body_style
    ))
    story.append(Paragraph(
        "<b>11.6 Term of Confidentiality:</b> Confidentiality obligations shall endure throughout the term of this Agreement and for a period of three (3) years following termination, except that bona fide trade secrets shall remain protected for as long as they retain statutory trade secret status.",
        body_style
    ))

    story.append(Spacer(1, 6))
    story.append(Paragraph("SECTION 12: DATA PRIVACY & CYBERSECURITY STANDARDS", h1_style))
    story.append(Paragraph(
        "<b>12.1 Regulatory Compliance:</b> Each Party shall comply with all applicable privacy, cybersecurity, and data protection laws, including GDPR, CCPA/CPRA, and relevant data security statutes, in relation to personal data processed under this Agreement.",
        body_style
    ))
    story.append(Paragraph(
        "<b>12.2 Security Measures:</b> Contractor shall maintain industry-standard administrative, physical, and technical safeguards (including TLS encryption in transit and AES-256 encryption at rest) designed to protect Client data against unauthorized access, loss, or alteration.",
        body_style
    ))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 8: WARRANTIES & CAPPED LIMITATION OF LIABILITY (SECTIONS 13 & 14)
    # =========================================================================
    story.append(Paragraph("SECTION 13: WARRANTIES & REMEDIES", h1_style))
    story.append(Paragraph(
        "<b>13.1 Performance Warranty:</b> Contractor represents and warrants that all Services shall be performed in a professional, workmanlike manner conforming to prevailing industry standards by personnel possessing suitable technical training and expertise.",
        body_style
    ))
    story.append(Paragraph(
        "<b>13.2 Ninety-Day Defect Warranty:</b> Contractor warrants that for a period of ninety (90) calendar days following formal acceptance of any custom Deliverable (\"Warranty Period\"), the Deliverable will operate in material compliance with the objective Acceptance Criteria set forth in the applicable SOW. Contractor's sole obligation and Client's exclusive remedy for breach of this warranty shall be for Contractor to repair or replace the defective software without additional charge.",
        body_style
    ))
    story.append(Paragraph(
        "<b>13.3 Non-Infringement Warranty:</b> Contractor warrants that custom Deliverables created by Contractor do not and will not infringe any valid United States copyright, patent, trademark, or trade secret of any third party. This warranty does not apply to Client Materials or modifications made by third parties.",
        body_style
    ))
    story.append(Paragraph(
        "<b>13.4 Disclaimer of Implied Warranties:</b> EXCEPT AS EXPRESSLY SET FORTH IN THIS SECTION 13, NEITHER PARTY MAKES ANY OTHER WARRANTIES, EXPRESS OR IMPLIED, AND EACH PARTY SPECIFICALLY DISCLAIMS ALL IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND SYSTEM COMPATIBILITY.",
        body_style
    ))

    story.append(Spacer(1, 6))
    story.append(Paragraph("SECTION 14: CAPPED LIMITATION OF LIABILITY (MUTUAL PROTECTION)", h1_style))
    story.append(Paragraph(
        "<b>14.1 Mutual Aggregate Liability Cap:</b> TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, IN NO EVENT SHALL EITHER PARTY'S TOTAL AGGREGATE LIABILITY ARISING OUT OF OR RELATING TO THIS AGREEMENT, WHETHER IN CONTRACT, TORT (INCLUDING NEGLIGENCE), WARRANTY, STRICT LIABILITY, OR OTHERWISE, EXCEED THE TOTAL FEES ACTUALLY PAID OR PAYABLE BY CLIENT TO CONTRACTOR UNDER THE SPECIFIC STATEMENT OF WORK GIVING RISE TO THE CLAIM IN THE TWELVE (12) MONTHS PRECEDING THE OCCURRENCE OF SAID CLAIM.",
        body_style
    ))
    story.append(Paragraph(
        "<b>14.2 Mutual Waiver of Consequential Damages:</b> NEITHER PARTY SHALL BE LIABLE TO THE OTHER FOR ANY INDIRECT, INCIDENTAL, CONSEQUENTIAL, SPECIAL, PUNITIVE, OR EXEMPLARY DAMAGES, INCLUDING LOSS OF PROFITS, LOSS OF REVENUE, LOSS OF GOODWILL, LOSS OF DATA, OR BUSINESS INTERRUPTION, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGES IN ADVANCE.",
        body_style
    ))
    story.append(Paragraph(
        "<b>14.3 Absolute Exclusions:</b> The limitations and waivers in Sections 14.1 and 14.2 shall not apply to: (a) breach of Section 11 (Confidentiality); (b) third-party indemnification obligations under Section 14.4; or (c) damages resulting from a Party's Gross Negligence or intentional willful misconduct.",
        body_style
    ))
    story.append(Paragraph(
        "<b>14.4 Mutual Third-Party Indemnification:</b> Each Party (\"Indemnifying Party\") shall defend, indemnify, and hold harmless the other Party, its officers, and employees against third-party claims, lawsuits, or regulatory penalties solely to the extent arising from: (i) gross negligence or willful misconduct of the Indemnifying Party; or (ii) infringement of third-party IP rights by the Indemnifying Party's materials. Contractor's indemnification is expressly conditioned upon Client providing prompt written notice, sole control of defense, and full cooperation.",
        body_style
    ))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 9: TERM, TERMINATION & WORK-IN-PROGRESS PAYOUT (SECTIONS 15 & 16)
    # =========================================================================
    story.append(Paragraph("SECTION 15: TERM & BALANCED TERMINATION PROVISIONS", h1_style))
    story.append(Paragraph(
        "<b>15.1 Initial Term & Renewal:</b> This Agreement shall commence on the Effective Date and shall remain in full force and effect for an initial term of one (1) year. Thereafter, this Agreement shall automatically renew for successive one (1) year terms, unless either Party provides written notice of non-renewal at least thirty (30) calendar days prior to the expiration of the active term.",
        body_style
    ))
    story.append(Paragraph(
        "<b>15.2 Mutual Termination for Convenience:</b> Either Party may terminate this Agreement or any Statement of Work at any time, for any reason or no reason, upon providing at least thirty (30) calendar days prior written notice to the other Party. Unilateral immediate termination with zero notice is expressly prohibited under this Agreement.",
        body_style
    ))
    story.append(Paragraph(
        "<b>15.3 Mutual Termination for Cause:</b> Either Party may terminate this Agreement or any active SOW immediately upon written notice if the other Party: (a) materially breaches any provision of this Agreement and fails to cure such breach within thirty (30) calendar days after receiving written notice specifying the breach; or (b) becomes insolvent, makes an assignment for the benefit of creditors, or enters bankruptcy proceedings.",
        body_style
    ))

    story.append(Spacer(1, 6))
    story.append(Paragraph("SECTION 16: GUARANTEED WORK-IN-PROGRESS COMPENSATION & EXIT", h1_style))
    story.append(Paragraph(
        "<b>16.1 Guaranteed Work-in-Progress Payment:</b> In the event of early termination of this Agreement or any SOW for convenience by Client, or by Contractor for Client's uncured breach, Client shall immediately pay Contractor for: (a) all Services completed and hours worked up to the effective termination date; (b) pro-rated compensation for in-progress milestones; and (c) all non-cancelable third-party commitments and expenses incurred by Contractor in reliance on the SOW.",
        body_style
    ))
    story.append(Paragraph(
        "<b>16.2 No Forfeiture of Unbilled Hours:</b> The Parties expressly covenant that under no circumstances shall Contractor forfeit any unbilled fees, milestone retainers, or work-in-progress compensation as a consequence of termination.",
        body_style
    ))
    story.append(Paragraph(
        "<b>16.3 Orderly Transition & Handover:</b> Upon receipt of all payments due under Section 16.1, Contractor shall furnish to Client all completed source code, documentation, and Deliverables generated under the terminated SOW, and shall provide up to ten (10) hours of transitional technical consultation at standard hourly rates.",
        body_style
    ))
    story.append(Paragraph(
        "<b>16.4 Return or Destruction of Confidential Materials:</b> Within fifteen (15) calendar days following termination, each Party shall return or certify destruction of all Confidential Information of the other Party, except for one archival copy retained strictly for legal compliance and compliance auditing.",
        body_style
    ))
    story.append(Paragraph(
        "<b>16.5 Survival of Essential Covenants:</b> Sections 2, 7, 8, 9, 10, 11, 12, 13.4, 14, 16, 17, and 18 shall survive the expiration or termination of this Agreement for any reason.",
        body_style
    ))
    story.append(PageBreak())

    # =========================================================================
    # PAGE 10: DISPUTE RESOLUTION, GENERAL CLAUSES & SIGNATURES (SECTIONS 17 & 18)
    # =========================================================================
    story.append(Paragraph("SECTION 17: MULTI-TIER DISPUTE RESOLUTION & ARBITRATION", h1_style))
    story.append(Paragraph(
        "<b>17.1 Executive Negotiation:</b> In the event of any controversy, claim, or dispute arising out of or relating to this Agreement, the Parties shall first endeavor to resolve the dispute informally through executive negotiations between designated C-level officers within fifteen (15) business days of written notice.",
        body_style
    ))
    story.append(Paragraph(
        "<b>17.2 Neutral Mediation:</b> If executive negotiations do not achieve settlement within fifteen (15) business days, the Parties agree to submit the dispute to confidential, non-binding mediation administered by the American Arbitration Association (AAA) or JAMS. Mediation costs shall be borne equally.",
        body_style
    ))
    story.append(Paragraph(
        "<b>17.3 Binding Commercial Arbitration:</b> Any dispute not resolved through mediation within thirty (30) days shall be definitively settled by binding arbitration before a single neutral arbitrator under AAA Commercial Arbitration Rules. Arbitration proceedings shall be conducted virtually or in the mutually agreed neutral venue of Wilmington, Delaware. The arbitrator's award shall be final and enforceable in any court of competent jurisdiction.",
        body_style
    ))
    story.append(Paragraph(
        "<b>17.4 Equal Fee Allocation:</b> Each Party shall pay its own legal fees, and the arbitrator's administrative fees shall be shared equally, eliminating predatory one-way legal fee shifting.",
        body_style
    ))

    story.append(Spacer(1, 5))
    story.append(Paragraph("SECTION 18: MISCELLANEOUS & FORMAL SIGNATURES", h1_style))
    story.append(Paragraph(
        "<b>18.1 Governing Law:</b> This Agreement shall be governed and construed in accordance with the substantive laws of the State of Delaware, without regard to conflicts of law principles.",
        body_style
    ))
    story.append(Paragraph(
        "<b>18.2 Severability & Entire Agreement:</b> If any provision of this Agreement is held invalid, the remainder shall continue in full force. This Agreement represents the entire agreement between the Parties and supersedes all prior negotiations.",
        body_style
    ))
    story.append(Paragraph(
        "<b>18.3 Counterparts & Electronic Signature:</b> This Agreement may be executed in counterparts, each of which shall be deemed an original, and electronic signatures (DocuSign or PDF) shall have the same legal force and effect as handwritten signatures.",
        body_style
    ))

    story.append(Spacer(1, 8))

    # Formal Signature Blocks Table
    sig_data = [
        [
            Paragraph("<b>FOR CLIENT:</b><br/><b>Client Global Enterprises, Inc.</b>", body_style),
            Paragraph("<b>FOR CONTRACTOR:</b><br/><b>Contractor Solutions LLC</b>", body_style),
        ],
        [
            Paragraph("Signature: ___________________________<br/>Name: <b>Marcus Vance, Esq.</b><br/>Title: <b>Chief Executive Officer</b><br/>Date: <b>October 1, 2026</b>", body_style),
            Paragraph("Signature: ___________________________<br/>Name: <b>Elena Rostova</b><br/>Title: <b>Managing Director &amp; Principal</b><br/>Date: <b>October 1, 2026</b>", body_style),
        ],
    ]
    sig_table = Table(sig_data, colWidths=[246, 246])
    sig_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(sig_table)

    # Build document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Contract PDF successfully created at: {output_pdf_path}")

if __name__ == "__main__":
    out_path = os.path.join(os.path.dirname(__file__), "Airtight_Master_Services_Agreement.pdf")
    create_airtight_contract(out_path)
