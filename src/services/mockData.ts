import type { ContractDocument, Clause } from '../types/contract';
import type { ChatMessage } from '../types/chat';
import { mockAirtightDocument, mockAirtightMessages } from './airtightData';

export type PresetKey = 'freelance' | 'lease' | 'nda' | 'airtight';

// ============================================================================
// PRESET 1: Freelance Dev Master Services Agreement (42/100 - High Risk)
// ============================================================================
export const mockFreelanceClauses: Clause[] = [
  {
    id: 'clause_ip',
    title: '1. Intellectual Property Assignment & Inventions',
    originalText: 
      'Contractor hereby irrevocably assigns, transfers, and conveys to Client all rights, title, and interest in and to all works of authorship, inventions, code, designs, and developments conceived, created, or reduced to practice by Contractor, whether individually or jointly with others, before, during, or outside of normal working hours, relating to or arising out of the performance of Services under this Agreement. Such assignment shall take effect immediately upon creation of said work, regardless of whether invoice payments have been tendered, approved, or settled by Client.',
    plainSummary: 
      'The client claims exclusive ownership of all code, designs, and inventions you produce—even if made on your own personal time outside project hours. Crucially, ownership transfers immediately upon creation, meaning they legally own your deliverables even if they never pay your invoices.',
    riskLevel: 'HIGH',
    category: 'IP_RIGHTS',
    unfairnessScore: 92,
    suggestion: 
      'Condition all IP transfer on full and final payment: "All intellectual property rights in and to Deliverables created specifically for Client shall transfer to Client strictly upon receipt of full and complete payment of all invoiced fees."',
    pageNumber: 1,
  },
  {
    id: 'clause_termination',
    title: '2. Termination for Convenience & Fee Forfeiture',
    originalText: 
      'Client reserves the absolute unilateral right to terminate this Agreement and any associated Statement of Work at any time, with or without cause, effective immediately upon electronic transmission of written notice. In the event of such termination by Client, Contractor shall immediately cease all work and shall forfeit any unbilled hours, work-in-progress fees, or unapproved milestone disbursements. Contractor may terminate this Agreement only upon sixty (60) calendar days prior written notice.',
    plainSummary: 
      'The client can cancel the contract at any second with zero advance warning and walk away without paying for in-progress work or unbilled hours. Conversely, you are locked in and forced to provide 60 days of advance notice if you need to exit.',
    riskLevel: 'HIGH',
    category: 'TERMINATION',
    unfairnessScore: 88,
    suggestion: 
      'Establish mutual 30-day notice and guarantee payment for all work performed: "Either party may terminate this Agreement upon thirty (30) days prior written notice. Upon termination by Client, Client shall compensate Contractor for all hours worked and non-cancelable expenses incurred up to the effective termination date."',
    pageNumber: 2,
  },
  {
    id: 'clause_indemnity',
    title: '3. Unlimited Indemnification & Defense Obligations',
    originalText: 
      'Contractor shall defend, indemnify, and hold harmless Client, its parent companies, subsidiaries, affiliates, and their respective directors, officers, employees, and agents from and against any and all losses, damages, liabilities, penalties, legal fees, court costs, and expenses arising out of, relating to, or resulting from Contractor\'s performance, deliverables, or alleged breach of any warranty, whether direct, indirect, incidental, or consequential. Contractor\'s liability under this section shall be uncapped and unlimited by any other provision herein.',
    plainSummary: 
      'You are personally on the hook for unlimited financial damages, third-party lawsuits, and attorney fees if anything goes wrong or if the client gets sued. There is zero cap on your liability, which could jeopardize your personal assets.',
    riskLevel: 'HIGH',
    category: 'LIABILITY',
    unfairnessScore: 96,
    suggestion: 
      'Cap total liability to the fees paid under the contract: "Each party shall mutually indemnify the other against third-party claims arising solely from gross negligence or willful misconduct. Contractor\'s aggregate liability under this Agreement shall be capped at the total amount of fees received by Contractor in the twelve (12) months preceding the claim."',
    pageNumber: 3,
  },
  {
    id: 'clause_payment',
    title: '4. Payment Terms, Milestones & Subjective Withholding',
    originalText: 
      'Client shall disburse compensation within ninety (90) calendar days following receipt of Contractor\'s itemized invoice, subject to Client\'s sole and subjective satisfaction with the quality and functionality of the deliverables. Client reserves the right to withhold up to one hundred percent (100%) of any invoice amount if Client determines in its sole discretion that any deliverable requires revision or fails to meet Client\'s internal expectations.',
    plainSummary: 
      'Payment is delayed to Net-90 (up to 3 months wait). Furthermore, the client can withhold your entire paycheck based on their purely subjective feelings or arbitrary dissatisfaction without objective acceptance criteria.',
    riskLevel: 'MEDIUM',
    category: 'PAYMENT',
    unfairnessScore: 68,
    suggestion: 
      'Set Net-15 or Net-30 payment with objective acceptance criteria: "Invoices shall be payable within thirty (30) days of receipt. Deliverables shall be deemed accepted unless Client provides written notice of specific non-conformities against agreed specifications within ten (10) business days."',
    pageNumber: 4,
  },
  {
    id: 'clause_dispute',
    title: '5. Dispute Resolution, Governing Law & Jurisdiction',
    originalText: 
      'This Agreement shall be construed and governed in accordance with the laws of the State of Delaware, without regard to conflicts of law principles. Any dispute, claim, or controversy arising out of or relating to this Agreement shall be resolved through binding arbitration administered by JAMS in Wilmington, Delaware. Each party shall bear fifty percent (50%) of the arbitrator\'s fees and administrative arbitration costs.',
    plainSummary: 
      'Any legal dispute must be resolved in Delaware through private arbitration with split administrative costs. While mutual and standard corporate practice, having to arbitrate out-of-state can be costly for an independent freelancer.',
    riskLevel: 'LOW',
    category: 'DISPUTE',
    unfairnessScore: 35,
    suggestion: 
      'Propose local jurisdiction or remote arbitration: "Arbitration proceedings shall be conducted virtually/remotely via video conference, or governed under the laws and courts of Contractor\'s primary place of business."',
    pageNumber: 5,
  },
];

export const mockFreelanceDocument: ContractDocument = {
  sessionId: 'sess_contract_freelance_01',
  filename: 'Sample_Freelance_Master_Services_Agreement.pdf',
  uploadTimestamp: '2026-09-15T18:30:00.000Z',
  overallFairnessScore: 42,
  totalPages: 5,
  pages: [
    {
      pageNumber: 1,
      text: `MASTER SERVICES & SOFTWARE DEVELOPMENT AGREEMENT
Document Reference: MSA-2026-DEV-0881 • Governing Jurisdiction: State of Delaware

This Independent Contractor Professional Services Agreement ("Agreement") is made and entered into as of January 15, 2026 ("Effective Date"), by and between Apex Dynamics Global LLC, a Delaware corporation having its principal executive offices at 100 Enterprise Way, Suite 400, Wilmington, DE ("Client"), and the undersigned independent contractor professional ("Contractor").

RECITALS
WHEREAS, Client is engaged in the development, deployment, and commercialization of enterprise digital software systems and commercial technology applications;
WHEREAS, Contractor is a professional software engineer and specialized technical consultant offering independent development, architecture, and programming services;
WHEREAS, Client desires to retain Contractor, and Contractor agrees to render specialized services for Client, strictly subject to the covenants and terms set forth herein;

NOW, THEREFORE, in consideration of the mutual representations and covenants herein contained, the parties agree as follows:

SECTION 1: ENGAGEMENT & STATEMENTS OF WORK
1.1 Engagement: Client retains Contractor to perform the technical development and consulting services set forth in discrete Statements of Work ("SOW") executed from time to time.
1.2 Standard of Performance: Contractor shall perform all services with reasonable professional care, diligence, and in compliance with mutually agreed technical milestones.

SECTION 2: INDEPENDENT CONTRACTOR STATUS
2.1 Independent Contractor: The relationship between the parties is exclusively that of independent contractors. Nothing in this Agreement shall create an employer-employee, partnership, or joint venture relationship. Contractor is solely responsible for all federal, state, and local self-employment taxes, statutory benefits, and workers' compensation coverage.

1. Intellectual Property Assignment & Inventions
Contractor hereby irrevocably assigns, transfers, and conveys to Client all rights, title, and interest in and to all works of authorship, inventions, code, designs, and developments conceived, created, or reduced to practice by Contractor, whether individually or jointly with others, before, during, or outside of normal working hours, relating to or arising out of the performance of Services under this Agreement. Such assignment shall take effect immediately upon creation of said work, regardless of whether invoice payments have been tendered, approved, or settled by Client.`,
    },
    {
      pageNumber: 2,
      text: `SECTION 3: SCOPE OF DELIVERABLES & ACCEPTANCE
3.1 Milestone Delivery: Contractor shall submit completed code modules, documentation, and technical deliverables to Client's designated version control repositories in accordance with the project schedule.
3.2 Verification Review: Client shall have a period of five (5) business days following notification of milestone delivery to review source code and verify basic operational functionality against agreed functional requirements.

SECTION 4: CLIENT COOPERATION & MATERIALS
4.1 Access and Credentials: Client shall promptly furnish Contractor with necessary API keys, development environment credentials, third-party library licenses, and project specifications. Contractor shall not be held liable for project schedule delays resulting directly from Client's failure to furnish required credentials or documentation.
4.2 Client Point of Contact: Client designates its Vice President of Technology as the primary point of contact for technical architecture reviews and formal sprint approvals.

2. Termination for Convenience & Fee Forfeiture
Client reserves the absolute unilateral right to terminate this Agreement and any associated Statement of Work at any time, with or without cause, effective immediately upon electronic transmission of written notice. In the event of such termination by Client, Contractor shall immediately cease all work and shall forfeit any unbilled hours, work-in-progress fees, or unapproved milestone disbursements. Contractor may terminate this Agreement only upon sixty (60) calendar days prior written notice.

4.3 Post-Termination Handover: Upon delivery of written notice of termination, Contractor shall discontinue development work and furnish current repository commits to Client within forty-eight (48) hours.`,
    },
    {
      pageNumber: 3,
      text: `SECTION 5: CONFIDENTIALITY & PROPRIETARY INFORMATION
5.1 Confidential Information: Contractor acknowledges that during the term of this Agreement, Contractor may receive non-public, proprietary information concerning Client's architecture, customer records, and trade secrets. Contractor agrees to hold such materials in confidence and not disclose them to third parties without prior written authorization.
5.2 Permitted Disclosures: The obligations of confidentiality shall not apply to information that is or becomes publicly available without breach of this Agreement, or information independently developed by Contractor.

SECTION 6: EXPRESS WARRANTIES & LIMITATIONS
6.1 Workmanship Warranty: Contractor warrants that all software code delivered under this Agreement shall be original work or composed of permissible open-source libraries, and shall perform in material conformance with specifications for thirty (30) days following delivery.
6.2 Disclaimer: EXCEPT AS EXPRESSLY PROVIDED HEREIN, CONTRACTOR MAKES NO OTHER WARRANTIES, EXPRESS OR IMPLIED, INCLUDING IMPLIED WARRANTIES OF MERCHANTABILITY OR FITNESS FOR A PARTICULAR PURPOSE.

3. Unlimited Indemnification & Defense Obligations
Contractor shall defend, indemnify, and hold harmless Client, its parent companies, subsidiaries, affiliates, and their respective directors, officers, employees, and agents from and against any and all losses, damages, liabilities, penalties, legal fees, court costs, and expenses arising out of, relating to, or resulting from Contractor's performance, deliverables, or alleged breach of any warranty, whether direct, indirect, incidental, or consequential. Contractor's liability under this section shall be uncapped and unlimited by any other provision herein.`,
    },
    {
      pageNumber: 4,
      text: `SECTION 7: COMPENSATION & EXPENSES
7.1 Billing Structure: Contractor shall be compensated at the hourly rate or fixed milestone amounts specified in the active Statement of Work. Invoices shall itemize completed tasks and hours expended during the applicable billing period.
7.2 Reimbursable Disbursements: Client shall reimburse Contractor for reasonable, pre-approved travel and dedicated third-party cloud infrastructure expenses directly incurred in performing Services.

4. Payment Terms, Milestones & Subjective Withholding
Client shall disburse compensation within ninety (90) calendar days following receipt of Contractor's itemized invoice, subject to Client's sole and subjective satisfaction with the quality and functionality of the deliverables. Client reserves the right to withhold up to one hundred percent (100%) of any invoice amount if Client determines in its sole discretion that any deliverable requires revision or fails to meet Client's internal expectations.

SECTION 8: TAXES & REGULATORY WITHHOLDING
8.1 Tax Responsibility: Contractor acknowledges that Client will not withhold income tax, Social Security, or Medicare contributions from payments made hereunder. Contractor covenants to remit all required quarterly self-employment taxes in compliance with applicable federal and state revenue regulations.`,
    },
    {
      pageNumber: 5,
      text: `5. Dispute Resolution, Governing Law & Jurisdiction
This Agreement shall be construed and governed in accordance with the laws of the State of Delaware, without regard to conflicts of law principles. Any dispute, claim, or controversy arising out of or relating to this Agreement shall be resolved through binding arbitration administered by JAMS in Wilmington, Delaware. Each party shall bear fifty percent (50%) of the arbitrator's fees and administrative arbitration costs.

SECTION 9: SEVERABILITY & INTEGRATION
9.1 Severability: If any provision of this Agreement is held to be invalid or unenforceable, such holding shall not invalidate or render unenforceable any other provision hereof, which shall remain in full force and effect.
9.2 Entire Agreement: This Agreement, together with executed Statements of Work, represents the entire understanding between the parties regarding the subject matter hereof and supersedes all prior oral or written negotiations.
9.3 Amendments: No modification, waiver, or amendment of this Agreement shall be valid unless executed in writing by authorized representatives of both parties.

IN WITNESS WHEREOF, the parties hereto have executed this Master Services Agreement as of the date first written above.

CLIENT:                                  CONTRACTOR:
Apex Dynamics Global LLC                 Independent Technical Consultant

By: ___________________________          By: ___________________________
Name: Richard Sterling                   Name: Alex Chen
Title: Chief Technology Officer          Title: Independent Contractor
Date: January 15, 2026                   Date: January 15, 2026`,
    },
  ],
  clauses: mockFreelanceClauses,
};

export const mockFreelanceMessages: ChatMessage[] = [
  {
    id: 'msg_welcome_freelance',
    role: 'assistant',
    content: 
      'I have analyzed **Sample_Freelance_Master_Services_Agreement.pdf**. Overall fairness is rated at **42/100 (High Risk)**.\n\nKey areas of concern include:\n- **Immediate IP forfeiture** without payment guarantees (Clause 1)\n- **Immediate termination with fee forfeiture** (Clause 2)\n- **Uncapped, unilateral indemnification** (Clause 3)\n- **Net-90 payment terms** with subjective withholding (Clause 4)\n\nFeel free to ask questions, explore "What-If" scenarios, or request pushback phrasing for any clause.',
    timestamp: '2026-09-15T18:30:05.000Z',
    triggeredClauseIds: ['clause_ip', 'clause_termination', 'clause_indemnity'],
  },
  {
    id: 'msg_user_query_freelance',
    role: 'user',
    content: 'Can the client terminate the project and keep my work without paying?',
    timestamp: '2026-09-15T18:31:00.000Z',
  },
  {
    id: 'msg_asst_response_freelance',
    role: 'assistant',
    content: 
      '**Yes, under this current contract draft, they can do exactly that.**\n\nHere is how the clauses intersect to create this trap:\n\n1. **Clause 1 (IP Assignment):** States that all IP and deliverables transfer to the client *immediately upon creation*, explicitly *"regardless of whether invoice payments have been tendered, approved, or settled."*\n2. **Clause 2 (Termination for Convenience):** Permits the client to terminate immediately upon email notice and mandates that you *"forfeit any unbilled hours, work-in-progress fees, or unapproved milestone disbursements."*\n\n### Financial & Operational Exposure:\nIf you deliver 90% of a project milestone and the client issues a termination notice, they legally own all your source code and design assets while contractually excusing themselves from paying for that milestone.',
    timestamp: '2026-09-15T18:31:04.000Z',
    triggeredClauseIds: ['clause_ip', 'clause_termination'],
    counterProposal: 
      'Replace Clause 1 and Clause 2 with the following protective terms:\n\n"1. Intellectual Property: All intellectual property rights in and to Deliverables shall transfer to Client exclusively upon receipt of full and final payment of all corresponding fees.\n\n2. Termination: In the event of termination for convenience by Client, Contractor shall be compensated in full for all completed work, pro-rated hours, and uncancelable commitments incurred up to the date of termination."',
    scenarioOutcome: {
      riskLevel: 'HIGH',
      exposureText: 'Loss of 100% of unpaid work product + inability to withhold or relicense code.',
      recommendedAction: 'Do not sign without conditioning IP assignment strictly upon receipt of cleared funds and eliminating fee forfeiture upon termination.',
    },
  },
];

// ============================================================================
// PRESET 2: Residential Apartment Lease Agreement (55/100 - Moderate Risk)
// ============================================================================
export const mockLeaseClauses: Clause[] = [
  {
    id: 'lease_renewal_escalation',
    title: '1. Automatic Renewal & Uncapped Rent Escalation',
    originalText:
      'Upon expiration of the initial lease term, this Lease shall automatically renew for successive twelve (12) month periods unless Tenant provides Landlord with formal written notice of intent to vacate at least ninety (90) calendar days prior to the expiration date. In the event of automatic renewal, the monthly rent shall automatically escalate by twenty percent (20%) over the preceding term rate, without requiring Landlord to deliver any separate or additional written notification of rent adjustment.',
    plainSummary:
      'If you forget to provide written notice 90 days before lease end, you are automatically locked into another whole year at an immediate 20% rent increase. The landlord does not even have to remind you before the rate hike takes effect.',
    riskLevel: 'HIGH',
    category: 'PAYMENT',
    unfairnessScore: 84,
    suggestion:
      'Negotiate month-to-month transition with standard 30-day notice and capped escalation: "Upon expiration of the initial term, the Lease shall convert to a month-to-month tenancy terminable by either party on thirty (30) days written notice. Any annual rent escalation shall not exceed 3% or the local Consumer Price Index (CPI)."',
    pageNumber: 1,
  },
  {
    id: 'lease_landlord_entry',
    title: '2. Landlord Unannounced Entry & Inspection Rights',
    originalText:
      'Landlord and Landlord\'s authorized contractors, inspectors, and prospective purchasers or tenants reserve the unrestricted right to enter the Leased Premises at any hour of the day or night, with or without prior oral or written notice, for the purpose of inspection, routine maintenance, alterations, repairs, or showing the premises. Tenant hereby waives any claim for trespass, disturbance of quiet enjoyment, or damages arising from such entry.',
    plainSummary:
      'The landlord gives themselves permission to walk into your private apartment at any time, day or night, with zero advance warning. This is a severe invasion of privacy and directly contradicts standard tenant quiet enjoyment rights.',
    riskLevel: 'HIGH',
    category: 'MISC',
    unfairnessScore: 90,
    suggestion:
      'Require mandatory 24-hour advance written notice except for bona fide emergencies: "Landlord may enter the Premises only during standard business hours (9:00 AM to 6:00 PM) upon providing at least twenty-four (24) hours advance written or email notice, except in cases of immediate emergency threatening life or severe property damage."',
    pageNumber: 2,
  },
  {
    id: 'lease_deposit_deductions',
    title: '3. Security Deposit Deductions & Carpet Wear Forfeiture',
    originalText:
      'Landlord shall retain Tenant\'s security deposit and may deduct costs for professional deep cleaning, interior repainting, wall scuff rectification, and carpet steam-cleaning necessitated by routine occupancy or ordinary wear and tear. In the event deductions exceed the deposit balance, Tenant shall reimburse Landlord within fifteen (15) days of receiving an invoice. Deposit refunds shall be processed within sixty (60) days following premises surrender.',
    plainSummary:
      'The landlord permits themselves to bill you and wipe out your security deposit for routine, normal wear and tear (like ordinary scuffs or carpet aging) that landlords are legally required to absorb in most jurisdictions. Furthermore, return is delayed to 60 days.',
    riskLevel: 'MEDIUM',
    category: 'PAYMENT',
    unfairnessScore: 65,
    suggestion:
      'Explicitly exempt normal wear and tear and expedite refund to 21 days: "Landlord shall return the security deposit within twenty-one (21) days of surrender. Deductions shall apply solely to verified physical damage exceeding ordinary wear and tear, supported by itemized repair receipts."',
    pageNumber: 3,
  },
  {
    id: 'lease_quiet_enjoyment',
    title: '4. Quiet Enjoyment & Essential Maintenance Upkeep',
    originalText:
      'Landlord covenants that Tenant, upon paying the agreed Rent and performing covenants herein, shall peacefully and quietly hold and enjoy the Premises. Landlord shall be responsible for maintaining standard structural elements, plumbing mains, heating systems, and common areas in good working order in accordance with applicable local housing codes.',
    plainSummary:
      'A fair and standard landlord covenant ensuring the building structure, heating, and plumbing are maintained in habitable condition and you have the legal right to peaceful occupancy.',
    riskLevel: 'LOW',
    category: 'MISC',
    unfairnessScore: 25,
    suggestion:
      'Standard balanced clause. Ensure prompt emergency turnaround: "Landlord shall initiate repairs on essential heating, plumbing, and electrical failures within twenty-four (24) hours of Tenant notification."',
    pageNumber: 4,
  },
];

export const mockLeaseDocument: ContractDocument = {
  sessionId: 'sess_contract_lease_02',
  filename: 'Metro_Apartment_Lease_2026.pdf',
  uploadTimestamp: '2026-09-16T10:15:00.000Z',
  overallFairnessScore: 55,
  totalPages: 4,
  pages: [
    {
      pageNumber: 1,
      text: `RESIDENTIAL APARTMENT LEASE AGREEMENT
Document Reference: LEASE-NY-2026-4B • Property: The Metropolitan Tower, Suite 4B

This Residential Lease Agreement ("Lease") is made and executed as of January 1, 2026, by and between Metro Properties Management LLC ("Landlord"), whose address is 450 Lexington Avenue, New York, NY, and the undersigned tenant ("Tenant").

1. DEMISED PREMISES & RESIDENTIAL OCCUPANCY
Landlord hereby leases to Tenant, and Tenant leases from Landlord, the private dwelling unit identified as Apartment 4B located at 740 Park Boulevard, New York, NY ("Premises"), to be occupied exclusively as a private residential dwelling by Tenant and authorized occupants.

2. LEASE TERM & INITIAL EXPIRATION
The initial term of this Lease shall commence at 12:00 PM on February 1, 2026 ("Commencement Date") and shall expire at 11:59 PM on January 31, 2027 ("Expiration Date"), unless terminated earlier or renewed pursuant to provisions herein.

1. Automatic Renewal & Uncapped Rent Escalation
Upon expiration of the initial lease term, this Lease shall automatically renew for successive twelve (12) month periods unless Tenant provides Landlord with formal written notice of intent to vacate at least ninety (90) calendar days prior to the expiration date. In the event of automatic renewal, the monthly rent shall automatically escalate by twenty percent (20%) over the preceding term rate, without requiring Landlord to deliver any separate or additional written notification of rent adjustment.`,
    },
    {
      pageNumber: 2,
      text: `3. RENT PAYMENT TERMS & GRACE PERIOD
Tenant agrees to pay Landlord base monthly rent of $3,200.00 USD, payable in advance on or before the first (1st) day of each calendar month via Landlord's electronic resident portal. If rent is not received by Landlord by 11:59 PM on the fifth (5th) day of the month, Tenant shall pay a standard late fee of $100.00 USD.

4. UTILITIES & TELECOMMUNICATIONS
Tenant shall be responsible for establishing accounts and remitting timely payments for electricity, gas, high-speed internet, and cable television services directly to utility providers. Landlord shall provide water, sewer, and municipal trash disposal at no additional charge.

2. Landlord Unannounced Entry & Inspection Rights
Landlord and Landlord's authorized contractors, inspectors, and prospective purchasers or tenants reserve the unrestricted right to enter the Leased Premises at any hour of the day or night, with or without prior oral or written notice, for the purpose of inspection, routine maintenance, alterations, repairs, or showing the premises. Tenant hereby waives any claim for trespass, disturbance of quiet enjoyment, or damages arising from such entry.`,
    },
    {
      pageNumber: 3,
      text: `5. OCCUPANCY RULES & PROHIBITED CONDUCT
The Premises shall be utilized exclusively for private residential purposes. Commercial business operations, public gatherings, and disruptive conduct violating the quiet enjoyment of neighboring residents are strictly prohibited. Tenant agrees to observe all building regulations and municipal noise curfews between 10:00 PM and 7:00 AM.

6. PET POLICY & DAMAGE LIABILITIES
No domestic animals, dogs, cats, or exotic pets shall be kept upon the Premises without prior written pet addendum approval and payment of an authorized non-refundable pet sanitation deposit. Tenant bears strict financial responsibility for any physical scratching, odor, or flooring damage caused by authorized pets.

3. Security Deposit Deductions & Carpet Wear Forfeiture
Landlord shall retain Tenant's security deposit and may deduct costs for professional deep cleaning, interior repainting, wall scuff rectification, and carpet steam-cleaning necessitated by routine occupancy or ordinary wear and tear. In the event deductions exceed the deposit balance, Tenant shall reimburse Landlord within fifteen (15) days of receiving an invoice. Deposit refunds shall be processed within sixty (60) days following premises surrender.`,
    },
    {
      pageNumber: 4,
      text: `4. Quiet Enjoyment & Essential Maintenance Upkeep
Landlord covenants that Tenant, upon paying the agreed Rent and performing covenants herein, shall peacefully and quietly hold and enjoy the Premises. Landlord shall be responsible for maintaining standard structural elements, plumbing mains, heating systems, and common areas in good working order in accordance with applicable local housing codes.

7. SURRENDER OF PREMISES
Upon termination or expiration of this Lease, Tenant shall vacate and surrender the Premises to Landlord in broom-clean condition, ordinary wear and tear accepted. Tenant shall return all entry fobs, keys, and garage access remotes to the building management office.

8. GOVERNING LAW & JURISDICTION
This Lease Agreement shall be construed and governed in accordance with the statutory housing and real property laws of the State of New York.

IN WITNESS WHEREOF, the parties hereto have executed this Residential Lease Agreement as of the date first set forth above.

LANDLORD:                                TENANT:
Metro Properties Management LLC          Resident Signatory

By: ___________________________          By: ___________________________
Name: Marcus Vance                       Name: Jordan Taylor
Title: Senior Property Manager           Title: Primary Lessee
Date: January 1, 2026                    Date: January 1, 2026`,
    },
  ],
  clauses: mockLeaseClauses,
};

export const mockLeaseMessages: ChatMessage[] = [
  {
    id: 'msg_welcome_lease',
    role: 'assistant',
    content:
      'I have analyzed **Metro_Apartment_Lease_2026.pdf**. Overall fairness is rated at **55/100 (Moderate Risk)**.\n\nKey issues flagged for your review:\n- **Automatic 12-month renewal + 20% rent hike** without reminder (Clause 1)\n- **Unrestricted unannounced landlord entry** at any hour (Clause 2)\n- **Security deposit deductions for routine wear & tear** (Clause 3)\n- Standard habitable maintenance covenant (Clause 4)\n\nAsk questions like *"Can my landlord enter without notice?"* or test negotiation scenarios.',
    timestamp: '2026-09-16T10:15:05.000Z',
    triggeredClauseIds: ['lease_renewal_escalation', 'lease_landlord_entry', 'lease_deposit_deductions'],
  },
  {
    id: 'msg_user_lease_query',
    role: 'user',
    content: 'Can the landlord really enter my apartment anytime without giving notice?',
    timestamp: '2026-09-16T10:16:00.000Z',
  },
  {
    id: 'msg_asst_lease_response',
    role: 'assistant',
    content:
      '**Under Clause 2 as written, yes—the landlord has granted themselves unrestricted entry at any hour without notice.**\n\n### Why This Is Dangerous:\n- **Privacy Violation:** They can show up or bring contractors inside at night or when you are not home.\n- **Legal Enforceability:** In most tenant jurisdictions, tenants have a statutory right to at least **24 to 48 hours written notice** before non-emergency entry. This clause attempts to make you waive that right.\n\n### Recommendation:\nStrike the waiver and require 24 hours written notice during standard business hours.',
    timestamp: '2026-09-16T10:16:04.000Z',
    triggeredClauseIds: ['lease_landlord_entry'],
    counterProposal:
      'Replace Clause 2 with:\n"Landlord may enter the Premises only during standard business hours (9:00 AM to 6:00 PM) upon providing at least twenty-four (24) hours advance written or email notice, except in cases of immediate emergency threatening life or structural damage."',
    scenarioOutcome: {
      riskLevel: 'HIGH',
      exposureText: 'Loss of residential privacy and security; surprise visits without opportunity to prepare or be present.',
      recommendedAction: 'Do not sign without establishing a strict 24-hour advance written notice requirement for non-emergency entries.',
    },
  },
];

// ============================================================================
// PRESET 3: Mutual Non-Disclosure Agreement (NDA) (89/100 - Fair & Balanced)
// ============================================================================
export const mockNdaClauses: Clause[] = [
  {
    id: 'nda_mutual_definition',
    title: '1. Mutual Definition of Confidential Information',
    originalText:
      '"Confidential Information" refers to any proprietary, non-public technical, commercial, financial, or strategic information disclosed by either party ("Disclosing Party") to the other ("Receiving Party"), whether marked as confidential or reasonably understood to be confidential given the nature of the information. Confidential Information does not include information that is publicly known through no breach, already known to Receiving Party without restriction, independently developed, or lawfully obtained from a third party.',
    plainSummary:
      'A fair, two-way standard definition of confidential data. It applies equally to both parties and includes the standard legal exclusions (publicly known info, prior knowledge, or independent development).',
    riskLevel: 'LOW',
    category: 'IP_RIGHTS',
    unfairnessScore: 18,
    suggestion:
      'Well-balanced clause meeting industry standards. No material alterations required.',
    pageNumber: 1,
  },
  {
    id: 'nda_term_return',
    title: '2. Term of Obligation & Return of Materials',
    originalText:
      'The obligations of confidentiality under this Agreement shall survive for a period of two (2) years following disclosure of the relevant Confidential Information, after which obligations shall expire except with respect to trade secrets, which shall remain protected for as long as recognized under applicable law. Upon written request of Disclosing Party, Receiving Party shall promptly return or certify destruction of all tangible copies of Confidential Information.',
    plainSummary:
      'Confidentiality lasts for 2 years (standard business timeframe), with indefinite protection reserved solely for genuine trade secrets. You can request the return or destruction of materials at any time.',
    riskLevel: 'LOW',
    category: 'TERMINATION',
    unfairnessScore: 22,
    suggestion:
      'Standard commercial duration. If sharing highly sensitive source code or algorithms, consider extending to 3 or 5 years if needed.',
    pageNumber: 2,
  },
  {
    id: 'nda_remedies',
    title: '3. Remedies, Equitable Relief & Governing Law',
    originalText:
      'Each party acknowledges that any unauthorized disclosure or breach of this Agreement may cause irreparable harm for which monetary damages alone would be inadequate. Accordingly, either party shall be entitled to seek injunctive relief and equitable remedies in a court of competent jurisdiction, in addition to any other remedies available at law. This Agreement shall be governed by the laws of the State of New York.',
    plainSummary:
      'Both parties have the mutual right to ask a court to stop leaks immediately (injunctive relief) rather than just waiting to sue for cash damages later. The clause is balanced and reciprocal.',
    riskLevel: 'NEUTRAL',
    category: 'DISPUTE',
    unfairnessScore: 30,
    suggestion:
      'Mutual and standard boilerplate for commercial NDAs. Both sides have equal recourse.',
    pageNumber: 3,
  },
];

export const mockNdaDocument: ContractDocument = {
  sessionId: 'sess_contract_nda_03',
  filename: 'Mutual_Standard_NDA_v3.pdf',
  uploadTimestamp: '2026-09-16T14:00:00.000Z',
  overallFairnessScore: 89,
  totalPages: 3,
  pages: [
    {
      pageNumber: 1,
      text: `MUTUAL NON-DISCLOSURE & CONFIDENTIALITY AGREEMENT
Document Reference: NDA-2026-MUTUAL-04 • Standard Commercial Terms

This Mutual Non-Disclosure Agreement ("Agreement") is made and entered into as of March 1, 2026 ("Effective Date"), by and between Alpha Technologies Inc., a Delaware corporation, and Beta Innovations LLC, a California limited liability company. Alpha and Beta are collectively referred to as the "Parties" and each individually as a "Party."

RECITALS
WHEREAS, the Parties wish to explore potential collaborative business opportunities, software integrations, and technology licensing arrangements ("Permitted Purpose");
WHEREAS, in connection with discussions concerning the Permitted Purpose, each Party may disclose to the other Party certain proprietary, non-public technical, commercial, and financial information;
WHEREAS, both Parties desire to establish mutual covenants ensuring that all disclosed confidential materials remain safeguarded against unauthorized disclosure or misuse;

NOW, THEREFORE, the Parties mutually agree as follows:

1. Mutual Definition of Confidential Information
"Confidential Information" refers to any proprietary, non-public technical, commercial, financial, or strategic information disclosed by either party ("Disclosing Party") to the other ("Receiving Party"), whether marked as confidential or reasonably understood to be confidential given the nature of the information. Confidential Information does not include information that is publicly known through no breach, already known to Receiving Party without restriction, independently developed, or lawfully obtained from a third party.`,
    },
    {
      pageNumber: 2,
      text: `SECTION 2: NON-DISCLOSURE & DUTY OF CARE
2.1 Standard of Protection: The Receiving Party agrees to protect the Disclosing Party's Confidential Information with the same degree of care it employs for its own confidential materials of like importance, but in no event less than a reasonable standard of commercial care.
2.2 Permitted Purpose: The Receiving Party shall use the Confidential Information solely for evaluating and pursuing the Permitted Purpose and for no other commercial or competitive purpose whatsoever.
2.3 Authorized Disclosures: The Receiving Party may disclose Confidential Information solely to its directors, officers, employees, legal counsel, and financial advisors who have a need to know and are bound by confidentiality obligations at least as restrictive as those contained herein.

2. Term of Obligation & Return of Materials
The obligations of confidentiality under this Agreement shall survive for a period of two (2) years following disclosure of the relevant Confidential Information, after which obligations shall expire except with respect to trade secrets, which shall remain protected for as long as recognized under applicable law. Upon written request of Disclosing Party, Receiving Party shall promptly return or certify destruction of all tangible copies of Confidential Information.`,
    },
    {
      pageNumber: 3,
      text: `3. Remedies, Equitable Relief & Governing Law
Each party acknowledges that any unauthorized disclosure or breach of this Agreement may cause irreparable harm for which monetary damages alone would be inadequate. Accordingly, either party shall be entitled to seek injunctive relief and equitable remedies in a court of competent jurisdiction, in addition to any other remedies available at law. This Agreement shall be governed by the laws of the State of New York.

SECTION 3: MISCELLANEOUS & INTEGRATION
3.1 No License Granted: Nothing in this Agreement grants either Party any copyright, patent, trademark, or commercial license in or to the other Party's intellectual property.
3.2 Entire Understanding: This Agreement embodies the entire agreement between the Parties regarding confidentiality and supersedes all prior oral or written discussions.

IN WITNESS WHEREOF, the Parties have executed this Mutual Non-Disclosure Agreement as of the Effective Date.

DISCLOSING PARTY:                        RECEIVING PARTY:
Alpha Technologies Inc.                  Beta Innovations LLC

By: ___________________________          By: ___________________________
Name: Sarah Jenkins                      Name: David K. Ramirez
Title: Chief Executive Officer           Title: Chief Technology Officer
Date: March 1, 2026                      Date: March 1, 2026`,
    },
  ],
  clauses: mockNdaClauses,
};

export const mockNdaMessages: ChatMessage[] = [
  {
    id: 'msg_welcome_nda',
    role: 'assistant',
    content:
      'I have analyzed **Mutual_Standard_NDA_v3.pdf**. Overall fairness is rated at **89/100 (Fair & Balanced)**.\n\nKey highlights:\n- **Symmetric mutual confidentiality definition** with standard exclusions (Clause 1)\n- **Reasonable 2-year survivability term** + trade secret carveout (Clause 2)\n- **Mutual injunctive relief remedies** under NY law (Clause 3)\n\nThis agreement is safe, standard, and reciprocal. Ask any specific questions about permitted disclosures or expiration terms.',
    timestamp: '2026-09-16T14:00:05.000Z',
    triggeredClauseIds: ['nda_mutual_definition', 'nda_term_return', 'nda_remedies'],
  },
  {
    id: 'msg_user_nda_query',
    role: 'user',
    content: 'Can I share this confidential information with my attorney or CPA?',
    timestamp: '2026-09-16T14:01:00.000Z',
  },
  {
    id: 'msg_asst_nda_response',
    role: 'assistant',
    content:
      '**Yes, under standard NDA practice and professional privilege.**\n\nDisclosing information to legal counsel or accountants under professional duties of confidentiality is universally permitted. However, to eliminate all doubt, you can add an explicit "Permitted Disclosees" sentence.\n\n### Recommended Clarification:\n"Receiving Party may disclose Confidential Information to its directors, legal counsel, and financial advisors who have a need-to-know and are bound by professional or contractual duties of confidentiality."',
    timestamp: '2026-09-16T14:01:04.000Z',
    triggeredClauseIds: ['nda_mutual_definition'],
    counterProposal:
      'Add permitted representative carve-out:\n"Receiving Party may disclose Confidential Information to its officers, legal counsel, and financial advisors who need to know such information for the Permitted Purpose and are bound by confidentiality obligations at least as restrictive as this Agreement."',
    scenarioOutcome: {
      riskLevel: 'LOW',
      exposureText: 'Minimal exposure; disclosures to legal/tax counsel are legally protected.',
      recommendedAction: 'Agreement is safe to execute; optional clarifying sentence can be inserted.',
    },
  },
];

// ============================================================================
// EXPORT LOOKUP MAPS & BACKWARD COMPATIBILITY
// ============================================================================
export const MOCK_PRESETS: Record<PresetKey, ContractDocument> = {
  freelance: mockFreelanceDocument,
  lease: mockLeaseDocument,
  nda: mockNdaDocument,
  airtight: mockAirtightDocument,
};

export const MOCK_PRESET_MESSAGES: Record<PresetKey, ChatMessage[]> = {
  freelance: mockFreelanceMessages,
  lease: mockLeaseMessages,
  nda: mockNdaMessages,
  airtight: mockAirtightMessages,
};

export interface PresetScenario {
  id: string;
  label: string;
  prompt: string;
  iconType: 'briefcase' | 'code' | 'clock' | 'shield' | 'home' | 'key' | 'dollar' | 'file';
}

export const MOCK_PRESET_SCENARIOS: Record<PresetKey, PresetScenario[]> = {
  freelance: [
    {
      id: 'cancel_midway',
      label: 'Client cancels midway',
      prompt: 'What happens if the client cancels the project midway through development? Will I get paid for in-progress work?',
      iconType: 'briefcase',
    },
    {
      id: 'reuse_assets',
      label: 'Reuse code & portfolio',
      prompt: 'Can I reuse my code libraries, components, or portfolio assets for other clients under this agreement?',
      iconType: 'code',
    },
    {
      id: 'late_payment',
      label: 'Payment delayed past 30 days',
      prompt: 'What happens if the client delays payment past 30 or 60 days? Can I pause work or charge interest?',
      iconType: 'clock',
    },
    {
      id: 'server_breach',
      label: 'Client server breach liability',
      prompt: 'Am I liable if the client\'s server or third-party service gets breached while running my software?',
      iconType: 'shield',
    },
  ],
  lease: [
    {
      id: 'unannounced_entry',
      label: 'Can landlord enter unannounced?',
      prompt: 'Can the landlord or their contractors enter my apartment at any hour without giving 24 hours advance notice?',
      iconType: 'key',
    },
    {
      id: 'rent_hike',
      label: 'What if rent jumps 20%?',
      prompt: 'What happens if I miss the 90-day notice window? Will my rent immediately jump by 20% for a full year?',
      iconType: 'dollar',
    },
    {
      id: 'deposit_forfeit',
      label: 'Security deposit deductions',
      prompt: 'Can the landlord legally deduct from my deposit for normal wear and tear like wall scuffs and carpet wear?',
      iconType: 'home',
    },
    {
      id: 'broken_heat',
      label: 'Who fixes heating & plumbing?',
      prompt: 'What are my rights and the landlord\'s duties if the heating or plumbing breaks during the winter?',
      iconType: 'shield',
    },
  ],
  nda: [
    {
      id: 'share_lawyer',
      label: 'Can I share with my attorney?',
      prompt: 'Can I share this confidential information with my personal attorney or accountant for professional advice?',
      iconType: 'file',
    },
    {
      id: 'two_year_expiry',
      label: 'What survives after 2 years?',
      prompt: 'Does my confidentiality obligation truly expire after 2 years, or are there exceptions for trade secrets?',
      iconType: 'clock',
    },
    {
      id: 'public_info',
      label: 'What counts as confidential?',
      prompt: 'If something becomes public knowledge or I already knew it before signing, is it still considered confidential?',
      iconType: 'shield',
    },
    {
      id: 'subpoena',
      label: 'What if subpoenaed by a court?',
      prompt: 'Am I in breach of this NDA if I am compelled to disclose information under a valid court order or subpoena?',
      iconType: 'file',
    },
  ],
  airtight: [
    {
      id: 'airtight_exit',
      label: 'Guaranteed WIP on exit',
      prompt: 'How does Section 16 protect my work-in-progress compensation if the client terminates the contract early?',
      iconType: 'shield',
    },
    {
      id: 'airtight_payment',
      label: 'Net-30 & late fees',
      prompt: 'What are my contractual remedies under Section 7 and 8 if the client does not pay invoices within 30 days?',
      iconType: 'dollar',
    },
    {
      id: 'airtight_ip',
      label: 'Conditional IP transfer',
      prompt: 'Does Section 9 ensure that title to software deliverables transfers strictly upon receipt of cleared payment?',
      iconType: 'code',
    },
    {
      id: 'airtight_liability',
      label: 'Liability cap & indemnity',
      prompt: 'Explain the 12-month mutual fee cap and consequential damages waiver in Section 14.',
      iconType: 'briefcase',
    },
  ],
};

// Backward compatibility exports
export const mockClauses: Clause[] = mockFreelanceClauses;
export const mockContractDocument: ContractDocument = mockFreelanceDocument;
export const mockChatMessages: ChatMessage[] = mockFreelanceMessages;
