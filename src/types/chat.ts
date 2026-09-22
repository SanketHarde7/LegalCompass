import type { RiskLevel } from './contract';

export type MessageRole = 'user' | 'assistant' | 'system';

export interface ScenarioOutcome {
  riskLevel: RiskLevel;
  exposureText: string;
  recommendedAction: string;
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  triggeredClauseIds?: string[];
  counterProposal?: string;
  scenarioOutcome?: ScenarioOutcome;
}
