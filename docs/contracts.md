# LegalCompass — API Contracts & Backend Interface Specification

**Document Version:** 1.0.0  
**Status:** Approved Integration Specification  
**Scope:** REST Endpoints, Server-Sent Events (SSE) Streaming Protocol, TypeScript Interfaces & Mock Payloads  

---

## 1. Global API Conventions

- **Base URL:** `/api` (configured via `VITE_API_BASE_URL` with default `/api`)
- **Transport Security:** TLS 1.3+ mandatory in production.
- **Content Types:**
  - Standard REST requests/responses: `application/json; charset=utf-8`
  - File Uploads: `multipart/form-data`
  - Streaming AI Copilot: `text/event-stream; charset=utf-8`
  - Brief Export: `application/pdf`
- **Standard Error Format:** All non-2xx responses return a uniform JSON error payload:
```typescript
export interface ApiErrorResponse {
  error: {
    code: string;           // Machine-readable error code (e.g. "FILE_TOO_LARGE")
    message: string;        // User-friendly plain-English description
    details?: Record<string, unknown>;
    timestamp: string;      // ISO 8601 string
    request_id?: string;
  };
}
```

---

## 2. API Endpoints

### 2.1 Endpoint 1: Document Upload & Analysis

- **HTTP Method:** `POST`
- **Route:** `/api/upload`
- **Description:** Receives a raw contract file (`.pdf`, `.docx`), runs semantic chunking, isolates legal clauses, evaluates clause risk levels, generates plain-English summaries, and calculates an overall fairness score.

#### Request Specification
- **Content-Type:** `multipart/form-data`
- **Payload Parameters:**
  - `file`: Binary file data (Required). Permitted MIME types: `application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`. Max file size: 25MB (`26,214,400 bytes`).
  - `user_role` (Optional): `'freelancer' | 'tenant' | 'small_business_owner' | 'general'`. Defaults to `'general'`.

#### TypeScript Interfaces
```typescript
export type RiskLevel = 'HIGH' | 'MEDIUM' | 'LOW' | 'NEUTRAL';

export type RiskCategory = 
  | 'INDEMNIFICATION'
  | 'LIABILITY'
  | 'INTELLECTUAL_PROPERTY'
  | 'TERMINATION'
  | 'PAYMENT_TERMS'
  | 'CONFIDENTIALITY'
  | 'NON_COMPETE'
  | 'WARRANTIES'
  | 'DISPUTE_RESOLUTION'
  | 'OTHER';

export interface Clause {
  id: string;                         // Unique clause identifier, e.g., "clause_1"
  index: number;                      // Positional order in source document (1-indexed)
  title: string;                      // Extracted or synthesized heading, e.g., "Indemnification & Hold Harmless"
  text: string;                       // Raw legal verbiage from source document
  category: RiskCategory;             // Categorical classification
  risk_level: RiskLevel;              // Evaluated severity level
  plain_english_summary: string;      // Translates legalese into layman terms
  suggested_pushback?: string;        // Optional default balanced counter-clause
  page_number?: number;               // Page number in source PDF if applicable
}

export interface UploadContractResponse {
  session_id: string;                 // UUID identifying the analysis session
  filename: string;                   // Original filename uploaded
  file_size_bytes: number;            // Size in bytes
  uploaded_at: string;                // ISO 8601 timestamp
  total_clauses: number;              // Count of identified clauses
  overall_fairness_score: number;     // 0 (extremely one-sided/predatory) to 100 (wholly fair/balanced)
  summary_overview: string;           // High-level executive contract breakdown
  clauses: Clause[];                  // Array of extracted and analyzed clauses
}
```

#### Example Response Payload
```json
{
  "session_id": "sess_9b8f21a4-67c2-489e-9d21-4fa2e95b001a",
  "filename": "Freelance_Design_and_Development_Agreement_2026.pdf",
  "file_size_bytes": 1428500,
  "uploaded_at": "2026-09-15T18:00:00.000Z",
  "total_clauses": 4,
  "overall_fairness_score": 42,
  "summary_overview": "This contract exhibits high risk for independent contractors. Clause 4 imposes uncapped unilateral indemnification on the contractor without mutual protections. Intellectual property transfers immediately upon creation rather than upon receipt of full payment, and payment terms extend to Net-90 with no late fee remedies.",
  "clauses": [
    {
      "id": "clause_1",
      "index": 1,
      "title": "Payment Terms & Schedule",
      "text": "Client shall compensate Contractor within ninety (90) calendar days following receipt and client approval of a detailed invoice. In the event Client disputes any portion of an invoice, Client may withhold payment on the entirety of said invoice indefinitely pending resolution.",
      "category": "PAYMENT_TERMS",
      "risk_level": "HIGH",
      "plain_english_summary": "The client can take 3 months (Net-90) to pay you. Even worse, if they disagree with a small $50 item on your invoice, they can withhold the entire payment indefinitely without penalty.",
      "suggested_pushback": "Client shall pay all undisputed invoice amounts within thirty (30) calendar days of invoice receipt. Disputed amounts shall be resolved in good faith within 15 days, while all undisputed portions remain payable on schedule.",
      "page_number": 1
    },
    {
      "id": "clause_2",
      "index": 2,
      "title": "Ownership of Intellectual Property & Deliverables",
      "text": "Contractor agrees that all works of authorship, designs, source code, and deliverables developed under this Agreement are 'works made for hire' and shall become the immediate and exclusive property of the Client upon creation, irrespective of invoice payment status.",
      "category": "INTELLECTUAL_PROPERTY",
      "risk_level": "HIGH",
      "plain_english_summary": "The client owns all your code and designs the exact moment you create them—even if they end up never paying you a single cent for your work.",
      "suggested_pushback": "All intellectual property rights in and to the Deliverables shall transfer exclusively to Client only upon receipt of full and final payment of all agreed fees.",
      "page_number": 2
    },
    {
      "id": "clause_3",
      "index": 3,
      "title": "Termination for Convenience",
      "text": "Client may terminate this Agreement at any time for any reason or no reason upon three (3) business days written notice. Upon termination, Client shall pay Contractor strictly for completed deliverables accepted in writing by Client.",
      "category": "TERMINATION",
      "risk_level": "MEDIUM",
      "plain_english_summary": "The client can fire you on 3 days' notice without reason and only pay for items they officially approved, meaning in-progress hours could go uncompensated.",
      "suggested_pushback": "Either party may terminate this Agreement upon thirty (30) days prior written notice. Upon termination by Client, Contractor shall be compensated for all hours worked and non-cancelable commitments incurred up to the effective termination date.",
      "page_number": 3
    },
    {
      "id": "clause_4",
      "index": 4,
      "title": "Unilateral Indemnification & Liability Cap",
      "text": "Contractor shall indemnify, defend, and hold harmless Client and its officers from and against any and all claims, damages, liabilities, costs, and attorney's fees arising out of the performance of services. Client's maximum cumulative liability under this Agreement shall not exceed $100.",
      "category": "INDEMNIFICATION",
      "risk_level": "HIGH",
      "plain_english_summary": "You are personally responsible for paying all legal fees and damages if the client gets sued because of the project. Meanwhile, if the client harms you or breaches the contract, your maximum recovery is capped at just $100.",
      "suggested_pushback": "Each party shall mutually indemnify the other against third-party claims arising from gross negligence or willful misconduct. Each party's total liability shall be capped at the total fees paid under this Agreement during the preceding 12 months.",
      "page_number": 4
    }
  ]
}
```

---

### 2.2 Endpoint 2: Conversational Copilot & SSE Stream

- **HTTP Method:** `POST`
- **Route:** `/api/chat`
- **Description:** Accepts user queries regarding the contract, streams the synthesized response token-by-token using Server-Sent Events (SSE), dynamically cites relevant clauses, and delivers structured counter-clause suggestions.

#### Request Specification
- **Content-Type:** `application/json`
- **Payload Interface:**
```typescript
export interface ChatStreamRequest {
  session_id: string;               // Active session UUID
  message: string;                  // User prompt / inquiry
  selected_clause_id?: string;      // Optional specific clause context
  history?: Array<{                 // Prior turns for conversational memory
    role: 'user' | 'assistant';
    content: string;
  }>;
}
```

#### SSE Streaming Protocol Specification
- **Response Headers:**
  ```http
  HTTP/1.1 200 OK
  Content-Type: text/event-stream; charset=utf-8
  Cache-Control: no-cache, no-transform
  Connection: keep-alive
  X-Accel-Buffering: no
  ```
- **Event Types:** The server emits newline-delimited chunks prefixed with `data: `:
  1. `token`: Partial text chunk streamed from the LLM.
  2. `citation`: Signals that specific clauses are cited in the preceding reasoning.
  3. `suggestion`: Proposes a concrete counter-clause modification with negotiation advice.
  4. `done`: Terminal event signaling clean completion.
  5. `error`: Stream-level error event.

#### TypeScript Event Interfaces
```typescript
export type SSEStreamChunk = 
  | { type: 'token'; content: string }
  | { type: 'citation'; clause_ids: string[] }
  | { type: 'suggestion'; counter_clause: string; rationale: string; target_clause_id: string }
  | { type: 'done'; total_tokens?: number }
  | { type: 'error'; message: string; code: string };
```

#### Raw Wire Example Stream
```http
data: {"type": "token", "content": "Based on "}

data: {"type": "token", "content": "your contract, Clause 4 "}

data: {"type": "citation", "clause_ids": ["clause_4"]}

data: {"type": "token", "content": "creates severe legal vulnerability. You are taking on unlimited liability while the client's liability is capped at $100.\n\nHere is how you can push back:"}

data: {"type": "suggestion", "target_clause_id": "clause_4", "counter_clause": "Each party shall mutually indemnify the other against third-party claims arising from gross negligence. Total liability for either party shall not exceed the total fees paid under this Agreement.", "rationale": "Makes indemnification mutual and ties liability to fees earned rather than unlimited personal risk."}

data: {"type": "token", "content": "\n\nWould you like me to draft an email to send to your client?"}

data: {"type": "done", "total_tokens": 148}
```

---

### 2.3 Endpoint 3: What-If Scenario Simulation

- **HTTP Method:** `POST`
- **Route:** `/api/simulate-scenario`
- **Description:** Runs a deterministic simulation against the active contract for hypothetical real-world triggers (e.g. client default, dispute, sickness, scope creep).

#### Request Specification
- **Content-Type:** `application/json`
```typescript
export interface SimulateScenarioRequest {
  session_id: string;               // Active contract session UUID
  scenario_prompt: string;          // Hypothetical question or scenario description
}
```

#### Response Interface & Payload
```typescript
export interface ScenarioSimulationResult {
  scenario_title: string;           // Short descriptive title of the simulated scenario
  triggered_clauses: Array<{        // Clauses invoked by this scenario
    clause_id: string;
    clause_title: string;
    impact: string;
  }>;
  risk_evaluation: string;          // Deep analysis of what happens legally
  financial_exposure: string;       // Quantified or qualitative financial threat
  recommended_action: string;       // Concrete steps the user should take right now
}
```

#### Example Response Payload
```json
{
  "scenario_title": "Client Delays Payment by 45 Days After Project Completion",
  "triggered_clauses": [
    {
      "clause_id": "clause_1",
      "clause_title": "Payment Terms & Schedule",
      "impact": "Contract permits Net-90 payment terms; client is legally compliant and not in breach at Day 45."
    },
    {
      "clause_id": "clause_2",
      "clause_title": "Ownership of Intellectual Property",
      "impact": "Client already legally owns all code and assets, preventing Contractor from withholding work product."
    }
  ],
  "risk_evaluation": "Under Clause 1, the client is granted a 90-day payment grace period. At 45 days, the client is legally within their contractual rights. You cannot assess late interest fees because none are specified in the agreement. Moreover, because Clause 2 assigns IP immediately upon creation, you cannot legally revoke access or withhold credentials.",
  "financial_exposure": "100% of unpaid invoice balance with zero accruing interest; cash flow gap of up to 90 days with no legal recourse to accelerate payment.",
  "recommended_action": "Do not sign without revising Clause 1 to Net-30 with a 1.5% monthly late interest penalty. Revise Clause 2 to ensure IP transfer is strictly contingent upon full invoice settlement."
}
```

---

### 2.4 Endpoint 4: Attorney Consultation Brief Export

- **HTTP Method:** `POST`
- **Route:** `/api/export-brief`
- **Description:** Compiles the parsed contract, risk heatmaps, overall fairness evaluation, and user notes into an attorney-ready, single-page PDF brief.

#### Request Specification
- **Content-Type:** `application/json`
```typescript
export interface ExportBriefRequest {
  session_id: string;               // Active session UUID
  custom_notes?: string;            // Optional user questions for their attorney
}
```

#### Response Specification
- **HTTP Status:** `200 OK`
- **Content-Type:** `application/pdf`
- **Content-Disposition:** `attachment; filename="LegalCompass_Attorney_Brief_<session_id>.pdf"`
- **Response Body:** Binary PDF Blob.

---

## 3. Standard HTTP Error Status Codes

| Status Code | Error Code (`code`) | Trigger Condition | Frontend Handling Strategy |
| :--- | :--- | :--- | :--- |
| **`400 Bad Request`** | `INVALID_INPUT` | Missing required parameters or empty message payload. | Inline field validation warning; prevents submission. |
| **`413 Payload Too Large`**| `FILE_TOO_LARGE` | Uploaded document exceeds 25MB boundary. | Displays modal toast: `"File exceeds 25MB limit. Please upload a smaller file."` |
| **`415 Unsupported Media`**| `INVALID_FILE_TYPE` | Uploaded file is not `.pdf` or `.docx`. | Displays error: `"Only PDF and DOCX files are supported."` |
| **`422 Unprocessable`** | `PARSING_FAILED` | File is corrupted, password-protected, or unreadable OCR. | Prompts user with options to remove password or upload clear digital document. |
| **`404 Not Found`** | `SESSION_EXPIRED` | Session ID does not exist or expired in cache. | Resets UI to `IDLE` state with prompt: `"Session expired. Please re-upload your document."` |
| **`500 Server Error`** | `INTERNAL_ERROR` | AI synthesis or OCR engine failure. | Offers retry CTA without resetting uploaded file. |
| **`503 Unavailable`** | `AI_SERVICE_OVERLOADED`| LLM provider rate limit exceeded. | Exponential backoff retry with countdown indicator. |
