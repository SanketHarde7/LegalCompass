import type { RiskLevel, ClauseCategory } from './contract';

export interface ScenarioSimulationResult {
  scenarioTitle: string;
  triggeredClauses: Array<{
    clauseId: string;
    clauseTitle: string;
    impact: string;
  }>;
  riskEvaluation: string;
  financialExposure: string;
  recommendedAction: string;
  riskLevel: RiskLevel;
}

export interface RiskDistribution {
  highCount: number;
  mediumCount: number;
  lowCount: number;
  neutralCount: number;
  totalClauses: number;
}

export interface CategorySummary {
  category: ClauseCategory;
  clauseCount: number;
  highestRisk: RiskLevel;
}
