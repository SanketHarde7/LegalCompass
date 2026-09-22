export type RiskLevel = 'HIGH' | 'MEDIUM' | 'LOW' | 'NEUTRAL';

export type ClauseCategory = 
  | 'TERMINATION' 
  | 'LIABILITY' 
  | 'IP_RIGHTS' 
  | 'PAYMENT' 
  | 'DISPUTE' 
  | 'MISC'
  | 'OTHER';

export interface Clause {
  id: string;
  title: string;
  originalText: string;
  plainSummary: string;
  riskLevel: RiskLevel;
  category: ClauseCategory;
  unfairnessScore: number; // 0 (wholly fair) to 100 (predatory / extremely unfair)
  suggestion?: string;
  pageNumber?: number;
}

export interface PageContent {
  pageNumber: number;
  text: string;
}

export interface ContractDocument {
  sessionId: string;
  filename: string;
  uploadTimestamp: string;
  overallFairnessScore: number; // 0 to 100
  clauses: Clause[];
  totalPages?: number;
  pages?: PageContent[];
}
