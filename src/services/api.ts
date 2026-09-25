import axios from 'axios';
import type { ContractDocument, Clause, ClauseCategory, RiskLevel } from '../types/contract';
import type { ChatMessage } from '../types/chat';

const API_BASE_URL =
  (typeof import.meta !== 'undefined' && (import.meta as any).env?.VITE_API_BASE_URL) ||
  'http://localhost:8000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 45000,
  headers: {
    'Content-Type': 'application/json',
  },
});

function normalizeCategory(cat?: string): ClauseCategory {
  const upper = (cat || '').toUpperCase();
  if (upper.includes('TERMINAT')) return 'TERMINATION';
  if (upper.includes('LIABIL') || upper.includes('INDEMN')) return 'LIABILITY';
  if (upper.includes('IP') || upper.includes('INTELLECTUAL') || upper.includes('PROPERT')) return 'IP_RIGHTS';
  if (upper.includes('PAY') || upper.includes('FEE')) return 'PAYMENT';
  if (upper.includes('DISPUT') || upper.includes('ARBITRAT')) return 'DISPUTE';
  return 'MISC';
}

function normalizeRiskLevel(level?: string): RiskLevel {
  const upper = (level || '').toUpperCase();
  if (upper === 'HIGH' || upper === 'MEDIUM' || upper === 'LOW' || upper === 'NEUTRAL') {
    return upper as RiskLevel;
  }
  return 'LOW';
}

/**
 * Checks the live connectivity and health of the LegalCompass backend.
 */
export async function checkBackendHealth(): Promise<{
  connected: boolean;
  geminiModel?: string;
  groqModel?: string;
}> {
  try {
    const res = await fetch(`${API_BASE_URL}/health`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal: AbortSignal.timeout(3500),
    });
    if (!res.ok) return { connected: false };
    const data = await res.json();
    return {
      connected: true,
      geminiModel: data.gemini_model_id || data.providers?.gemini?.model_id,
      groqModel: data.groq_model_id || data.providers?.groq?.model_id,
    };
  } catch {
    return { connected: false };
  }
}



/**
 * Maps raw backend clause payload (supporting snake_case & camelCase) into frontend Clause model.
 * Preserves character offsets (startOffset, endOffset) and pageNumber.
 */
export function mapBackendClause(c: any, idx: number = 0): Clause {
  return {
    id: c.id || `clause_${idx + 1}`,
    title: c.title || `Clause ${idx + 1}`,
    originalText: c.text || c.originalText || '',
    plainSummary: c.plain_english_summary || c.plainSummary || 'Clause analyzed by LegalCompass.',
    riskLevel: normalizeRiskLevel(c.risk_level || c.riskLevel),
    category: normalizeCategory(c.category),
    unfairnessScore: c.unfairness_score ?? c.unfairnessScore ?? 40,
    suggestion: c.suggested_pushback || c.suggestion || undefined,
    clauseKind: c.clause_kind ?? c.clauseKind ?? 'OPERATIVE',
    isRiskBearing: c.is_risk_bearing ?? c.isRiskBearing ?? true,
    riskReasons: c.risk_reasons ?? c.riskReasons ?? [],
    pageNumber: c.page_number ?? c.pageNumber ?? 1,
    startOffset: c.start_offset ?? c.startOffset ?? undefined,
    endOffset: c.end_offset ?? c.endOffset ?? undefined,
  };
}

/**
 * Maps raw backend upload response into complete frontend ContractDocument.
 * Preserves documentTitle, pages, and structured clauses with source offsets.
 */
export function mapBackendContractDocument(
  resData: any,
  fallbackFilename: string = 'contract.pdf'
): ContractDocument {
  const rawClauses = resData.clauses || resData.document?.clauses || [];
  const mappedClauses: Clause[] = rawClauses.map((c: any, idx: number) => mapBackendClause(c, idx));

  const rawPages = resData.pages || resData.document?.pages || [];
  const mappedPages = rawPages.map((p: any) => ({
    pageNumber: p.pageNumber || p.page_number || 1,
    text: p.text || '',
  }));

  const totalPages =
    resData.totalPages ||
    resData.total_pages ||
    (mappedPages.length > 0 ? mappedPages.length : 1);

  return {
    sessionId: resData.session_id || resData.sessionId || `sess_${Date.now()}`,
    filename: resData.filename || fallbackFilename,
    documentTitle: resData.document_title ?? resData.documentTitle ?? undefined,
    uploadTimestamp: resData.uploaded_at || resData.uploadTimestamp || new Date().toISOString(),
    overallFairnessScore: resData.overall_fairness_score ?? resData.overallFairnessScore ?? 50,
    totalPages,
    pages: mappedPages,
    clauses: mappedClauses,
  };
}

/**
 * Uploads a contract document (PDF/DOCX/TXT) for parsing and risk evaluation.
 * Returns the structured ContractDocument.
 */
export async function uploadContract(file: File): Promise<ContractDocument> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('user_role', 'general');

  try {
    const response = await apiClient.post<any>('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 120000,
    });

    const resData = response.data;
    return mapBackendContractDocument(resData, file.name);
  } catch (err: any) {
    if (err.response?.data?.detail) {
      const detail = err.response.data.detail;
      const serverMsg =
        typeof detail === 'object' && detail.message
          ? detail.message
          : typeof detail === 'string'
          ? detail
          : 'The uploaded file does not appear to be a valid legal contract.';
      throw new Error(serverMsg);
    }

    if (err.response?.status === 422) {
      throw new Error(
        'The uploaded file does not appear to be a recognized legal contract or agreement. LegalCompass only processes enforceable agreements with contractual covenants.'
      );
    }

    throw new Error(
      err?.message || 'Failed to connect to the LegalCompass backend. Please ensure the backend server is running.'
    );
  }
}

/**
 * Sends a conversational query and streams the assistant response token-by-token.
 * Invokes `onToken(token)` for every received word/chunk.
 * Invokes `onCitation(clauseIds)` when citing specific clauses.
 */
export interface ContractChatContext {
  filename?: string;
  overallFairnessScore?: number;
  totalPages?: number;
  clauseIndex?: Array<{
    id: string;
    title: string;
    riskLevel?: string;
    pageNumber?: number;
  }>;
  clauses?: Array<{
    id: string;
    title: string;
    text?: string;
    originalText?: string;
    riskLevel?: string;
    unfairnessScore?: number;
    clauseKind?: string;
    isRiskBearing?: boolean;
    riskReasons?: string[];
    category?: string;
    plainSummary?: string;
    suggestion?: string;
    pageNumber?: number;
  }>;
}

export interface SSEEventHandlers {
  onToken?: (token: string) => void;
  onCitation?: (clauseIds: string[]) => void;
  onSuggestion?: (counterClause: string) => void;
  onDone?: () => void;
}

/**
 * Robust Server-Sent Events (SSE) Stream Parser.
 * Maintains a persistent buffer across chunk boundaries, splitting strictly on \n\n boundaries.
 * Preserves incomplete trailing data until future chunks arrive.
 * Prevents premature JSON parsing failures and silent token drops.
 */
export class SSEStreamParser {
  private buffer: string = '';
  private handlers: SSEEventHandlers;

  constructor(handlers: SSEEventHandlers) {
    this.handlers = handlers;
  }

  /**
   * Feed a new text chunk (decoded from stream) into the buffer and process all complete events.
   */
  public feed(chunk: string): void {
    this.buffer += chunk;
    this.processBuffer();
  }

  /**
   * Process all complete SSE events (bounded by double newline \n\n or \r\n\r\n).
   */
  private processBuffer(): void {
    while (true) {
      const match = this.buffer.match(/\r?\n\r?\n/);
      if (!match || match.index === undefined) {
        break; // Incomplete trailing event, keep in buffer until next chunk
      }

      const boundaryIndex = match.index;
      const delimiterLength = match[0].length;
      const eventBlock = this.buffer.slice(0, boundaryIndex);
      this.buffer = this.buffer.slice(boundaryIndex + delimiterLength);

      this.parseEventBlock(eventBlock);
    }
  }

  /**
   * Parses an individual complete event block.
   */
  private parseEventBlock(eventBlock: string): void {
    const trimmed = eventBlock.trim();
    if (!trimmed) {
      return; // Ignore empty keep-alive pings or stray delimiters
    }

    const lines = eventBlock.split(/\r?\n/);
    const dataLines: string[] = [];

    for (const line of lines) {
      if (line.startsWith(':')) {
        // SSE comment/heartbeat, ignore
        continue;
      }
      if (line.startsWith('data:')) {
        // Support both "data: payload" and "data:payload"
        const content = line.startsWith('data: ') ? line.slice(6) : line.slice(5);
        dataLines.push(content);
      }
    }

    if (dataLines.length === 0) {
      return;
    }

    const dataPayload = dataLines.join('\n').trim();
    if (!dataPayload) {
      return;
    }

    if (dataPayload === '[DONE]') {
      this.handlers.onDone?.();
      return;
    }

    try {
      const parsed = JSON.parse(dataPayload);
      if (parsed.type === 'token' && typeof parsed.content === 'string') {
        const cleanToken = parsed.content.replace(/\[CITE:[a-zA-Z0-9_-]+\]/g, '');
        if (cleanToken && this.handlers.onToken) {
          this.handlers.onToken(cleanToken);
        }
      } else if (parsed.type === 'citation' && Array.isArray(parsed.clause_ids)) {
        if (this.handlers.onCitation) {
          this.handlers.onCitation(parsed.clause_ids);
        }
      } else if (parsed.type === 'suggestion' && typeof parsed.counter_clause === 'string') {
        if (this.handlers.onSuggestion) {
          this.handlers.onSuggestion(parsed.counter_clause);
        }
      } else if (parsed.type === 'done') {
        this.handlers.onDone?.();
      }
    } catch (err) {
      console.warn('Malformed SSE event payload failed to parse as JSON:', dataPayload, err);
    }
  }

  /**
   * Flushes any remaining data in the buffer when the stream has ended.
   */
  public flush(): void {
    this.processBuffer();
    if (this.buffer.trim()) {
      this.parseEventBlock(this.buffer);
      this.buffer = '';
    }
  }

  /**
   * Returns current internal buffer (useful for inspection/tests).
   */
  public getBuffer(): string {
    return this.buffer;
  }
}

export async function sendChatMessage(
  sessionId: string,
  message: string,
  onToken: (token: string) => void,
  onCitation?: (ids: string[]) => void,
  history?: Array<{ role: 'user' | 'assistant' | 'system'; content: string }>,
  selectedClauseId?: string,
  contractContext?: ContractChatContext
): Promise<ChatMessage> {
  try {
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        sessionId,
        session_id: sessionId,
        message,
        selectedClauseId: selectedClauseId || undefined,
        selected_clause_id: selectedClauseId || undefined,
        history: history && history.length > 0 ? history : undefined,
        contractContext: contractContext || undefined,
        contract_context: contractContext || undefined,
      }),
    });

    if (!response.ok) {
      throw new Error(`Chat request failed with status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('ReadableStream not supported on response body.');
    }

    const decoder = new TextDecoder('utf-8');
    let accumulatedContent = '';
    const triggeredClauseIds: string[] = [];
    let counterProposal: string | undefined = undefined;

    const sseParser = new SSEStreamParser({
      onToken: (cleanToken: string) => {
        accumulatedContent += cleanToken;
        onToken(cleanToken);
      },
      onCitation: (ids: string[]) => {
        triggeredClauseIds.push(...ids);
        if (onCitation) {
          onCitation(ids);
        }
      },
      onSuggestion: (counterClause: string) => {
        counterProposal = counterClause;
      },
      onDone: () => {
        // Stream completed
      },
    });

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunkStr = decoder.decode(value, { stream: true });
      sseParser.feed(chunkStr);
    }

    // Flush any remaining characters from the decoder and parser
    const finalChunk = decoder.decode();
    if (finalChunk) {
      sseParser.feed(finalChunk);
    }
    sseParser.flush();

    const finalCleaned = (accumulatedContent || 'Analysis completed.')
      .replace(/\[CITE:[a-zA-Z0-9_-]+\]/g, '')
      .replace(/[ \t]{2,}/g, ' ')
      .replace(/ +([.,;!?])/g, '$1')
      .trim();

    return {
      id: `msg_asst_${Date.now()}`,
      role: 'assistant',
      content: finalCleaned,
      timestamp: new Date().toISOString(),
      triggeredClauseIds: Array.from(new Set(triggeredClauseIds)),
      counterProposal,
    };
  } catch (err: any) {
    console.error('Backend chat request error:', err);
    const errorMsg = 'Unable to connect to the LegalCompass analysis backend. Please ensure the backend is running.';
    onToken(errorMsg);
    return {
      id: `msg_asst_${Date.now()}`,
      role: 'assistant',
      content: errorMsg,
      timestamp: new Date().toISOString(),
      triggeredClauseIds: [],
    };
  }
}

/**
 * Generates and downloads the one-page Attorney Consultation Brief PDF.
 */
export async function exportConsultationBrief(
  sessionId: string,
  customNotes?: string
): Promise<Blob> {
  const response = await apiClient.post(
    '/export-brief',
    {
      sessionId,
      session_id: sessionId,
      customNotes,
      custom_notes: customNotes,
    },
    { responseType: 'blob' }
  );

  return response.data as Blob;
}
