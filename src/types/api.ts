import type { ContractDocument, RiskLevel } from './contract';
import type { ChatMessage } from './chat';

// Upload endpoint payloads
export interface UploadContractRequest {
  file: File;
  userRole?: 'freelancer' | 'tenant' | 'small_business_owner' | 'general';
}

export interface UploadContractResponse {
  document: ContractDocument;
  message?: string;
}

// Chat endpoint payloads
export interface ChatQueryRequest {
  sessionId: string;
  message: string;
  selectedClauseId?: string | null;
  history?: Array<{
    role: 'user' | 'assistant';
    content: string;
  }>;
}

export interface ChatQueryResponse {
  message: ChatMessage;
}

// Streaming SSE chunk definitions
export type SSEStreamChunk = 
  | { type: 'token'; content: string }
  | { type: 'citation'; clause_ids: string[] }
  | { type: 'suggestion'; counter_clause: string; rationale: string; target_clause_id: string }
  | { type: 'done'; total_tokens?: number }
  | { type: 'error'; message: string; code: string };

// Simulation endpoint payloads
export interface SimulateScenarioRequest {
  sessionId: string;
  scenarioPrompt: string;
}

export interface TriggeredClauseItem {
  clauseId: string;
  clauseTitle: string;
  impact: string;
}

export interface SimulateScenarioResponse {
  scenarioTitle: string;
  triggeredClauses: TriggeredClauseItem[];
  riskEvaluation: string;
  financialExposure: string;
  recommendedAction: string;
  riskLevel: RiskLevel;
}

// Export brief endpoint payloads
export interface ExportBriefRequest {
  sessionId: string;
  customNotes?: string;
}

export interface ExportBriefResponse {
  blob: Blob;
  filename: string;
}

// Standard API error payload
export interface ApiErrorResponse {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
    timestamp: string;
    requestId?: string;
  };
}
