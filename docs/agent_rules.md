# LegalCompass — Engineering Standards & Agent Operational Rules

**Document Version:** 1.0.0  
**Status:** Mandatory Active Governance  
**Target:** AI Coding Agents, Frontend Architects & Contributing Engineers  

---

## 1. Absolute Codebase Constraints

Every engineer and AI agent operating within `legalcompass-frontend` must strictly adhere to the following non-negotiable rules. Any violation constitutes a critical failure.

### Rule 1: No Inline CSS or Custom CSS Files
- **Mandate:** All styling must be written strictly using Tailwind CSS utility classes.
- **Prohibited:**
  - `style={{ ... }}` attributes in JSX/TSX elements.
  - Creating new `.css`, `.scss`, or `.module.css` files.
  - Injecting raw CSS strings via styled-components or emotion.
- **Permitted:** The single `src/index.css` file contains exclusively the `@tailwind base; @tailwind components; @tailwind utilities;` directives and core global font/reset rules.

### Rule 2: Production Backend Integration
- **Mandate:** All network services in `src/services/api.ts` connect directly to the FastAPI backend defined by `VITE_API_BASE_URL` (defaulting to `http://localhost:8000/api`).
- **Requirements:**
  - Real document upload, multi-page OCR extraction, and legal risk classification.
  - Real SSE token streaming for AI chat interactions.
  - Clean error propagation and graceful user notices when backend connectivity is offline.

### Rule 3: Zero Breaking Changes to API Contracts
- **Mandate:** The types defined in `docs/contracts.md` are the single source of truth.
- **Constraints:**
  - Do not modify, remove, or rename fields in `src/types/contract.ts`, `src/types/chat.ts`, `src/types/analysis.ts`, or `src/types/api.ts` without an explicit, approved refactoring request.

### Rule 4: Mandatory Legal Disclaimer & Safety Guardrails
- **Mandate:** LegalCompass is an informational assistant for non-lawyers and must never position itself as certified legal counsel.
- **Enforcements:**
  - Every view displaying contract risk analysis or AI copilot guidance must display the disclaimer badge:
    `"Informational only. Not professional legal advice."`
  - All counter-clause proposals and pushback suggestions must include a clear advisory notice reminding users to consult a licensed attorney for binding contract modifications.
  - The document export feature must include a disclaimer banner across the top of the generated brief.

---

## 2. TypeScript & Code Quality Standards

### 2.1 Strict TypeScript Enforcement
- `strict: true` is enabled in `tsconfig.app.json` and must never be disabled.
- **No `any`:** The use of `any` is strictly banned. Use `unknown` with runtime type narrowing or write explicit generic interfaces.
- **Explicit Return Types:** All public helper functions, custom hooks, and service methods must specify explicit return types.
- **Props Typing:** Every React component must have an explicitly exported `interface ComponentNameProps`.

### 2.2 Component Directory Boundaries
Features and components must be placed into their exact functional folders as specified in `docs/components.md`:
```
src/
├── components/
│   ├── layout/       (Navbar, SplitPane, Header)
│   ├── document/     (PDFViewer, ClauseHighlighter, ChunkList)
│   ├── analysis/     (RiskBadge, FairnessMeter, ScenarioCards)
│   ├── chat/         (ChatWindow, MessageList, MessageInput, ActionChips)
│   └── common/       (Button, Modal, LoadingSkeleton, Tooltip)
```
- Components in `common/` must remain pure primitives with zero dependencies on domain stores.
- Do not create barrel files (`index.ts`) that circular-import across domain boundaries.

---

## 3. State Management (Zustand) Standards

Global state lives in `src/store/useAppStore.ts` using the Zustand slice pattern or cohesive single-store design.

### 3.1 State Slicing & Selectors
- Components must subscribe to atomic selectors (e.g., `useAppStore(state => state.selectedClauseId)`) rather than the entire state object to eliminate unnecessary re-renders.
- Transient UI states (e.g., hover tooltips, local form inputs, dragging offsets) must remain in local component `useState` / `useRef` and not clutter the global store.

### 3.2 State Lifecycle Transitions
State transitions must strictly follow the Global UI State Machine:
`IDLE` $\rightarrow$ `UPLOADING` $\rightarrow$ `PARSING` $\rightarrow$ `ANALYSED` $\leftrightarrow$ `STREAMING_CHAT` / `EXPORTING`.

---

## 4. SSE Stream Handling & Resiliency

When implementing the Server-Sent Events (SSE) chat stream:
1. **Use `AbortController`:** Every stream invocation must initialize an `AbortController`. When the user navigates away, sends a new message, or clicks "Stop Generating", the active stream must be immediately aborted.
2. **Buffer Ingestion:** Use `fetch` with `ReadableStream` or a dedicated lightweight SSE parser. Handle split chunks and multi-byte UTF-8 character boundary fragments defensively.
3. **Optimistic Message Insertion:** When the user sends a message, immediately append the user's turn to the message list and insert a blank assistant turn ready to receive streaming tokens.
4. **Error Recovery:** If the stream drops before receiving the `{"type": "done"}` event, mark the message with an `INTERRUPTED` indicator and provide a one-click resume trigger.

---

## 5. Contract Fidelity & Heuristic Rules
1. Document extraction must faithfully preserve physical page boundaries and verbatim text for exact legal citation.
2. The heuristic engine classifies provisions based on substantive operative text and material risk indicators (e.g., uncapped indemnification, unilateral termination without pay, subjective acceptance lock-ins).
3. Definitions, headings, and recitals must not be classified as high-risk or presented as actionable operative traps.

---

## 6. Development Workflow & Verification

1. **Linting:** Run `npm run lint` before committing any code changes.
2. **Type Checking:** Run `npm run build` or `npx tsc --noEmit` to verify zero type errors.
3. **No Dead Code:** Delete all unused imports, variables, and commented-out code blocks prior to task completion.
