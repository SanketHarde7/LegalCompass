import React from 'react';
import { AlertOctagon, Flame, ArrowRight } from 'lucide-react';
import type { RiskLevel } from '../../types/contract';
import { RiskBadge } from '../analysis/RiskBadge';

export interface ScenarioOutcomeData {
  riskLevel: RiskLevel;
  exposureText: string;
  recommendedAction: string;
}

export interface ScenarioCardProps {
  outcome: ScenarioOutcomeData;
}

export const ScenarioCard: React.FC<ScenarioCardProps> = ({ outcome }) => {
  return (
    <div className="mt-3 p-4 rounded-xl bg-rose-50/50 border border-rose-200/60">
      <div className="flex items-center justify-between gap-2 mb-3 pb-2 border-b border-rose-100">
        <div className="flex items-center gap-1.5 text-rose-700 text-xs font-bold uppercase tracking-wider">
          <AlertOctagon className="h-4 w-4 flex-shrink-0" />
          <span>Worst-Case Simulation Outcome</span>
        </div>
        <RiskBadge level={outcome.riskLevel} size="sm" />
      </div>

      <div className="mb-3">
        <div className="flex items-center gap-1.5 text-[11px] font-bold text-stone-600 uppercase tracking-wide mb-1">
          <Flame className="h-3 w-3 text-rose-500" />
          <span>Financial &amp; Legal Exposure:</span>
        </div>
        <p className="text-xs text-stone-700 leading-relaxed pl-3 border-l-2 border-rose-300">
          {outcome.exposureText}
        </p>
      </div>

      <div className="p-3 rounded-lg bg-white border border-stone-200">
        <div className="flex items-center gap-1.5 text-[11px] font-bold text-stone-700 uppercase tracking-wide mb-1">
          <ArrowRight className="h-3 w-3 text-stone-500" />
          <span>Immediate Recommended Action:</span>
        </div>
        <p className="text-xs text-stone-700 leading-relaxed">
          {outcome.recommendedAction}
        </p>
      </div>
    </div>
  );
};
