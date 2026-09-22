import React from 'react';
import { AlertTriangle, AlertCircle, CheckCircle2, MinusCircle } from 'lucide-react';
import type { RiskLevel } from '../../types/contract';

export interface RiskBadgeProps {
  level: RiskLevel;
  size?: 'sm' | 'md';
  className?: string;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({ level, size = 'md', className = '' }) => {
  const isSm = size === 'sm';
  const iconSize = isSm ? 'h-3 w-3' : 'h-3.5 w-3.5';
  const textSize = isSm ? 'text-[10px] px-2 py-0.5' : 'text-xs px-2.5 py-1';

  switch (level) {
    case 'HIGH':
      return (
        <span className={`inline-flex items-center gap-1 font-semibold rounded-full border bg-rose-50 text-rose-800 border-rose-200/70 ${textSize} ${className}`}>
          <AlertTriangle className={`${iconSize} flex-shrink-0`} />
          <span>High Risk</span>
        </span>
      );
    case 'MEDIUM':
      return (
        <span className={`inline-flex items-center gap-1 font-semibold rounded-full border bg-amber-50 text-amber-800 border-amber-200/70 ${textSize} ${className}`}>
          <AlertCircle className={`${iconSize} flex-shrink-0`} />
          <span>Medium Risk</span>
        </span>
      );
    case 'LOW':
      return (
        <span className={`inline-flex items-center gap-1 font-semibold rounded-full border bg-emerald-50 text-emerald-800 border-emerald-200/70 ${textSize} ${className}`}>
          <CheckCircle2 className={`${iconSize} flex-shrink-0`} />
          <span>Low Risk</span>
        </span>
      );
    case 'NEUTRAL':
    default:
      return (
        <span className={`inline-flex items-center gap-1 font-medium rounded-full border bg-stone-50 text-stone-600 border-stone-200 ${textSize} ${className}`}>
          <MinusCircle className={`${iconSize} flex-shrink-0`} />
          <span>Neutral</span>
        </span>
      );
  }
};
