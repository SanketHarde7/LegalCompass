import React from 'react';
import { AlertTriangle, AlertCircle, CheckCircle2 } from 'lucide-react';

export interface FairnessMeterProps {
  score: number;
  totalClauses: number;
  highRisks: number;
  mediumRisks: number;
  className?: string;
}

export const FairnessMeter: React.FC<FairnessMeterProps> = ({
  score,
  totalClauses: _totalClauses,
  highRisks,
  mediumRisks,
  className = '',
}) => {
  const clampedScore = Math.min(100, Math.max(0, score));

  // Determine traffic-light verdict card style & text
  let containerStyle = 'bg-rose-50/60 border border-rose-200 text-rose-900';
  let barColor = 'bg-rose-500';
  let Icon = AlertTriangle;
  let headline = `⚠️ High Risk: ${highRisks} Critical ${highRisks === 1 ? 'Trap' : 'Traps'} Found in this Agreement`;
  let subtext = 'Predatory provisions detected. Key liabilities and exit terms require immediate revision.';

  if (clampedScore >= 75) {
    containerStyle = 'bg-emerald-50/60 border border-emerald-200 text-emerald-900';
    barColor = 'bg-emerald-500';
    Icon = CheckCircle2;
    headline = '✓ Fair & Balanced: Standard Terms with Minimal Exposure';
    subtext = 'Mutual obligations adhere to commercial norms with reciprocal protections.';
  } else if (clampedScore >= 50) {
    containerStyle = 'bg-amber-50/60 border border-amber-200 text-amber-900';
    barColor = 'bg-amber-500';
    Icon = AlertCircle;
    headline = `⚡ Moderate Risk: ${mediumRisks} Unfavorable ${mediumRisks === 1 ? 'Clause' : 'Clauses'} to Review`;
    subtext = 'Minor imbalances identified. Review notice periods and indemnity caps.';
  }

  return (
    <div className={`p-4 sm:p-5 rounded-xl transition-all shadow-sm ${containerStyle} ${className}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5">
          <div className="mt-0.5 flex-shrink-0">
            <Icon className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-sm sm:text-base font-bold tracking-tight leading-snug">
              {headline}
            </h3>
            <p className="text-xs opacity-80 mt-0.5 leading-relaxed">
              {subtext}
            </p>
          </div>
        </div>

        {/* Score Pill */}
        <div className="flex items-baseline gap-0.5 bg-white/80 backdrop-blur-xs px-2.5 py-1 rounded-lg border border-stone-200/60 shadow-2xs flex-shrink-0">
          <span className="text-base sm:text-lg font-bold font-mono text-stone-900">
            {clampedScore}
          </span>
          <span className="text-[11px] font-mono text-stone-400">/100</span>
        </div>
      </div>

      {/* Slim Clean Progress Bar */}
      <div className="mt-3.5 h-1.5 w-full bg-stone-200/50 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ease-out ${barColor}`}
          style={{ width: `${clampedScore}%` }}
        />
      </div>
    </div>
  );
};
