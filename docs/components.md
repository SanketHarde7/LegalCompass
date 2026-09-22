# LegalCompass — Component Architecture & Specification

**Document Version:** 1.0.0  
**Status:** Approved Technical Component Specification  
**Scope:** Core UI Components, Props Contracts, State Boundaries & Edge Case Resiliency  

---

## 1. Overview & Architectural Principles

All components in LegalCompass follow a strict unidirectional data flow and separation of concerns:
- **Pure Presentation & Primitives (`common/`):** Stateless or localized UI primitives strictly driven by props. No direct access to global store.
- **Domain Display Components (`analysis/`, `document/`):** Contextual renderers receiving domain data. Interacts with store via explicit callbacks or designated selector hooks.
- **Interactive Containers (`layout/`, `chat/`):** Orchestrates layout state, streaming feeds, and user input dispatching to the Zustand store.
- **Resilience First:** Every component specifies defensive fallback rendering for empty states, parsing errors, partial streams, and network failures.

---

## 2. Layout Components

### 2.1 Navbar
- **Exact File Path:** `src/components/layout/Navbar.tsx`
- **Purpose:** Top-level global header hosting brand identity, document metadata pill, overall fairness meter, upload trigger, and export actions.
- **TypeScript Props Interface:**
```typescript
export interface NavbarProps {
  onOpenUploadModal: () => void;
  onExportBrief: () => Promise<void>;
  isExporting?: boolean;
}
```
- **State Boundaries:**
  - **Local State:** Mobile menu toggle (`isMobileMenuOpen: boolean`), Export confirmation tooltip state.
  - **Zustand Store Access:**
    - `useAppStore(state => state.document)` (reads `filename`, `total_clauses`, `overall_fairness_score`).
    - `useAppStore(state => state.uiStatus)` (reads `IDLE`, `UPLOADING`, `PARSING`, `ANALYSED`, `EXPORTING`).
- **Failure & Edge Case Handling:**
  - *No Document Loaded:* Filename displays "No contract loaded", fairness pill rendered in gray neutral state (`--/100`), Export button is disabled with tooltip: `"Upload and analyze a contract first"`.
  - *Ultra-long Filename:* CSS truncation with ellipsis (`max-w-[220px] truncate`) and full filename displayed in a hover `Tooltip`.
  - *Export Failure:* If `onExportBrief` rejects, displays inline amber error badge without resetting the current document session.

---

### 2.2 SplitPane
- **Exact File Path:** `src/components/layout/SplitPane.tsx`
- **Purpose:** Responsive 2-panel resizable container with draggable divider handle, localStorage position caching, and mobile fallback.
- **TypeScript Props Interface:**
```typescript
export interface SplitPaneProps {
  leftPanel: React.ReactNode;
  rightPanel: React.ReactNode;
  defaultSplitRatio?: number; // default: 0.50 (50%)
  minLeftWidthPx?: number;    // default: 360
  minRightWidthPx?: number;   // default: 400
  storageKey?: string;        // default: 'lc_split_ratio'
}
```
- **State Boundaries:**
  - **Local State:** `splitRatio: number`, `isDragging: boolean`, `activeMobileTab: 'document' | 'copilot'`.
  - **Zustand Store Access:** None (pure layout orchestrator).
- **Failure & Edge Case Handling:**
  - *Window Resize under 1024px:* Disables dragging listeners dynamically; converts side-by-side view to tabbed layout with zero layout thrashing.
  - *Corrupt `localStorage` Value:* Validates retrieved ratio against bounds (`0.25 <= ratio <= 0.75`); resets to default `0.50` if value is NaN or out of range.
  - *Pointer Capture Failure:* Attaches mousemove and mouseup listeners to `window` rather than divider element to prevent drag loss when mouse cursor moves rapidly over iframes or code blocks.

---

### 2.3 Header
- **Exact File Path:** `src/components/layout/Header.tsx`
- **Purpose:** Sub-header or panel title bar rendering contextual actions, zoom controls, clause filter dropdowns, and search inputs for the active pane.
- **TypeScript Props Interface:**
```typescript
export interface HeaderProps {
  title: string;
  badgeCount?: number;
  subtitle?: string;
  actions?: React.ReactNode;
  filterComponent?: React.ReactNode;
}
```
- **State Boundaries:**
  - **Local State:** Search input expand/collapse state.
  - **Zustand Store Access:** Optional read-only selector for active clause filtering.
- **Failure & Edge Case Handling:**
  - *Empty Title / Metadata:* Defaults to standard fallback title without breaking header alignment.
  - *Action Overflow:* Collapses secondary action buttons into an overflow dropdown when panel width is compressed.

---

## 3. Document Components

### 3.1 PDFViewer
- **Exact File Path:** `src/components/document/PDFViewer.tsx`
- **Purpose:** High-performance viewer that renders the uploaded PDF contract with responsive zoom, page virtualization, and visual text selection.
- **TypeScript Props Interface:**
```typescript
export interface PDFViewerProps {
  fileUrl: string | null;
  fileBlob?: Blob | null;
  activeClauseId?: string | null;
  onClauseSelect?: (clauseId: string) => void;
  isLoading?: boolean;
}
```
- **State Boundaries:**
  - **Local State:** Current page number, zoom scale (`0.75` to `2.0`), container scroll position.
  - **Zustand Store Access:** Selects `selectedClauseId` from `useAppStore` to trigger auto-scrolling to target page/offset.
- **Failure & Edge Case Handling:**
  - *Failed PDF Loading / Corrupted File:* Catches PDF rendering errors, displays a graceful error card with a `"Switch to Text Chunk View"` fallback button.
  - *Empty Document:* Displays empty state illustration: `"This document contains no readable text pages. It may be a scanned image requiring OCR."`
  - *Rapid Zoom / Memory Leaks:* Cleans up canvas rendering contexts on unmount or file switch using standard `AbortSignal`.

---

### 3.2 ClauseHighlighter
- **Exact File Path:** `src/components/document/ClauseHighlighter.tsx`
- **Purpose:** Wraps individual contract text passages, applying risk-weighted borders, background highlights, plain-English summary toggles, and selection rings.
- **TypeScript Props Interface:**
```typescript
import { Clause, RiskLevel } from '../../types/contract';

export interface ClauseHighlighterProps {
  clause: Clause;
  isSelected: boolean;
  onSelect: (clauseId: string) => void;
  onAskCopilot?: (clause: Clause) => void;
  onViewCounterClause?: (clause: Clause) => void;
}
```
- **State Boundaries:**
  - **Local State:** `isSummaryExpanded: boolean` (toggles the plain-English translation drawer inline).
  - **Zustand Store Access:** None (controlled component).
- **Failure & Edge Case Handling:**
  - *Missing Plain English Summary:* Renders fallback badge: `"AI summary pending..."` with a one-click `"Generate Summary"` trigger.
  - *Unknown Risk Level:* Defaults to neutral slate formatting (`RiskLevel.UNKNOWN`) to prevent styling crashes.
  - *Extremely Long Clause Text (>5000 characters):* Renders clamped text with a `"Show full legal clause"` expander to avoid overwhelming the visual viewport.

---

### 3.3 ChunkList
- **Exact File Path:** `src/components/document/ChunkList.tsx`
- **Purpose:** Virtualized scroll list of parsed contract clauses with category filter pills (`Indemnification`, `Liability`, `IP Rights`, `Termination`, `Payment`).
- **TypeScript Props Interface:**
```typescript
import { Clause, RiskCategory } from '../../types/contract';

export interface ChunkListProps {
  clauses: Clause[];
  selectedClauseId: string | null;
  onSelectClause: (clauseId: string) => void;
  activeFilterCategory?: RiskCategory | 'ALL';
  onFilterChange?: (category: RiskCategory | 'ALL') => void;
}
```
- **State Boundaries:**
  - **Local State:** Search query string, sort order (`By Appearance` vs `By Risk Level`).
  - **Zustand Store Access:** `useAppStore(state => state.clauses)`.
- **Failure & Edge Case Handling:**
  - *Zero Filter Results:* Displays `"No clauses found matching category [X]. Clear filter to see all 14 clauses."`
  - *Empty Clauses Array:* Renders skeleton loader during `PARSING` state; renders dropzone trigger during `IDLE` state.

---

## 4. Analysis Components

### 4.1 RiskBadge
- **Exact File Path:** `src/components/analysis/RiskBadge.tsx`
- **Purpose:** Accessible, color-coded severity tag (`HIGH`, `MEDIUM`, `LOW`, `NEUTRAL`) featuring standardized icons and WCAG-compliant contrast.
- **TypeScript Props Interface:**
```typescript
import { RiskLevel } from '../../types/contract';

export interface RiskBadgeProps {
  level: RiskLevel;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
  className?: string;
}
```
- **State Boundaries:**
  - **Local State:** None (Pure Functional Component).
  - **Zustand Store Access:** None.
- **Failure & Edge Case Handling:**
  - *Malformed Risk String:* Safely falls back to `RiskLevel.LOW` with a subtle dashed border and log warning.

---

### 4.2 FairnessMeter
- **Exact File Path:** `src/components/analysis/FairnessMeter.tsx`
- **Purpose:** Radial or linear gauge illustrating the overall contractual fairness score (0–100) with calibrated contextual benchmarks for freelancers and tenants.
- **TypeScript Props Interface:**
```typescript
export interface FairnessMeterProps {
  score: number; // 0 to 100
  size?: 'sm' | 'md' | 'lg';
  showDetails?: boolean;
  animated?: boolean;
}
```
- **State Boundaries:**
  - **Local State:** CSS progress animation counter.
  - **Zustand Store Access:** Reads score from props; can optionally fall back to `useAppStore(state => state.document?.overall_fairness_score)`.
- **Failure & Edge Case Handling:**
  - *Score is Null or Undefined:* Renders empty neutral state with message `"Upload contract to compute score"`.
  - *Score Out of Range (<0 or >100):* Clamps automatically via `Math.min(100, Math.max(0, score))`.

---

### 4.3 ScenarioCards
- **Exact File Path:** `src/components/analysis/ScenarioCards.tsx`
- **Purpose:** Interactive what-if simulation cards demonstrating real-world outcomes under the contract (e.g., late payment, unilateral cancellation, IP infringement claims).
- **TypeScript Props Interface:**
```typescript
import { ScenarioSimulationResult } from '../../types/analysis';

export interface ScenarioCardsProps {
  scenarios: ScenarioSimulationResult[];
  onSelectScenario: (scenario: ScenarioSimulationResult) => void;
  onSimulateCustomPrompt: (prompt: string) => Promise<void>;
  isSimulating?: boolean;
}
```
- **State Boundaries:**
  - **Local State:** Custom simulation input text, active card accordion state.
  - **Zustand Store Access:** Dispatches simulation trigger to store action `simulateScenario`.
- **Failure & Edge Case Handling:**
  - *Simulation Timeout:* Renders retry button on the affected scenario card: `"Simulation timed out. Click to recalculate."`
  - *Unresolvable Exposure:* Renders `"Financial exposure: Undetermined from contract terms alone. Requires human legal review."`

---

## 5. Chat Components

### 5.1 ChatWindow
- **Exact File Path:** `src/components/chat/ChatWindow.tsx`
- **Purpose:** High-level conversational copilot container encapsulating header controls, message stream, interactive citation handling, and query dispatch.
- **TypeScript Props Interface:**
```typescript
export interface ChatWindowProps {
  className?: string;
  onCiteClauseClick?: (clauseId: string) => void;
}
```
- **State Boundaries:**
  - **Local State:** Auto-scroll stickiness flag (`shouldAutoScroll: boolean`).
  - **Zustand Store Access:**
    - `messages: ChatMessage[]` from `useAppStore`.
    - `isStreaming: boolean` from `useAppStore`.
    - `selectedClause: Clause | null` from `useAppStore`.
    - `sendMessage: (text: string) => Promise<void>` from `useAppStore`.
    - `abortStream: () => void` from `useAppStore`.
- **Failure & Edge Case Handling:**
  - *SSE Connection Drop Mid-Stream:* Catches network interruption, sets message status to `INTERRUPTED`, and appends an inline action pill: `"[Stream Interrupted] Click to Resume Generation"`.
  - *Document Not Yet Analysed:* Disables input field with clear placeholder: `"Please upload a contract before asking questions."`

---

### 5.2 MessageList
- **Exact File Path:** `src/components/chat/MessageList.tsx`
- **Purpose:** Virtualized list of conversation turns, rendering Markdown formatting, code/clause snippets, citation buttons, and pushback proposal cards.
- **TypeScript Props Interface:**
```typescript
import { ChatMessage } from '../../types/chat';

export interface MessageListProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  onCitationClick: (clauseId: string) => void;
  onCopyCounterClause: (clauseText: string) => void;
}
```
- **State Boundaries:**
  - **Local State:** Copied badge state (`copiedMessageId: string | null`).
  - **Zustand Store Access:** None (pure functional list).
- **Failure & Edge Case Handling:**
  - *Empty History:* Renders conversational starter prompts tailored to the uploaded contract type.
  - *Malformed Markdown or Incomplete Tokens:* Markdown parser wrapped in an error boundary; renders raw text fallback without crashing the chat list.

---

### 5.3 MessageInput
- **Exact File Path:** `src/components/chat/MessageInput.tsx`
- **Purpose:** Multi-line expanding textarea with keyboard shortcut dispatch (`Enter` to send, `Shift+Enter` for newline), clause reference tag, and stop generation CTA.
- **TypeScript Props Interface:**
```typescript
export interface MessageInputProps {
  onSendMessage: (message: string) => void;
  onAbortStream: () => void;
  isStreaming: boolean;
  disabled?: boolean;
  placeholder?: string;
  selectedClauseTitle?: string | null;
  onClearSelectedClause?: () => void;
}
```
- **State Boundaries:**
  - **Local State:** `text: string`, `inputHeight: number`.
  - **Zustand Store Access:** Reads `selectedClause` context pill from props.
- **Failure & Edge Case Handling:**
  - *Whitespace Only Submission:* Blocks dispatch if `text.trim().length === 0`.
  - *Rapid Enter Key Spamming:* Throttled via local boolean flag to prevent duplicate network requests.

---

### 5.4 ActionChips
- **Exact File Path:** `src/components/chat/ActionChips.tsx`
- **Purpose:** Quick-prompt suggestion pills (e.g., *"Explain Clause 3 in simple terms"*, *"How do I negotiate payment terms?"*, *"Is there a non-compete clause?"*).
- **TypeScript Props Interface:**
```typescript
export interface ActionChip {
  id: string;
  label: string;
  prompt: string;
  category?: 'risk' | 'scenario' | 'negotiation';
}

export interface ActionChipsProps {
  chips: ActionChip[];
  onChipClick: (prompt: string) => void;
  disabled?: boolean;
}
```
- **State Boundaries:**
  - **Local State:** None.
  - **Zustand Store Access:** None.
- **Failure & Edge Case Handling:**
  - *Disabled state during streaming:* Chips visually dim (`opacity-50 pointer-events-none`) to prevent conflicting prompts while SSE is active.

---

## 6. Common Components

### 6.1 Button
- **Exact File Path:** `src/components/common/Button.tsx`
- **Purpose:** Reusable button primitive supporting primary, secondary, destructive, ghost, and outline variants with loading spinners.
- **TypeScript Props Interface:**
```typescript
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'destructive' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}
```
- **State Boundaries:** Local hover/focus only.
- **Failure & Edge Case Handling:** Form submission safety: prevents click execution when `disabled` or `isLoading` is true.

---

### 6.2 Modal
- **Exact File Path:** `src/components/common/Modal.tsx`
- **Purpose:** Accessible dialog overlay supporting keyboard `Escape` dismissal, focus trapping, and background backdrop blur.
- **TypeScript Props Interface:**
```typescript
export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl';
}
```
- **State Boundaries:** Manages body scroll lock (`document.body.style.overflow = 'hidden'`) on mount/unmount.
- **Failure & Edge Case Handling:** Traps focus within modal; handles backdrop clicks gracefully; returns focus to trigger element upon closing.

---

### 6.3 LoadingSkeleton
- **Exact File Path:** `src/components/common/LoadingSkeleton.tsx`
- **Purpose:** Shimmer placeholders for clauses, document pages, chat messages, and fairness meters during `UPLOADING` and `PARSING` states.
- **TypeScript Props Interface:**
```typescript
export interface LoadingSkeletonProps {
  variant?: 'text' | 'card' | 'clause' | 'circle';
  count?: number;
  className?: string;
}
```
- **State Boundaries:** None.
- **Failure & Edge Case Handling:** Provides accessible `aria-busy="true"` and `aria-label="Loading content..."`.

---

### 6.4 Tooltip
- **Exact File Path:** `src/components/common/Tooltip.tsx`
- **Purpose:** Micro-interaction popover for legal terms, risk ratings, truncated titles, and non-lawyer disclaimer reminders.
- **TypeScript Props Interface:**
```typescript
export interface TooltipProps {
  content: React.ReactNode;
  children: React.ReactElement;
  position?: 'top' | 'bottom' | 'left' | 'right';
  delayMs?: number;
}
```
- **State Boundaries:** Local hover/focus timer state.
- **Failure & Edge Case Handling:** Automatic viewport edge boundary detection to prevent tooltips from rendering off-screen.
