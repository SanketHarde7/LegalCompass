import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Sparkles, ArrowRight, FileText } from 'lucide-react';
import type { Clause } from '../../types/contract';
import { RiskBadge } from '../analysis/RiskBadge';

export interface ClauseCardProps {
  clause: Clause;
  isSelected: boolean;
  onSelect: (id: string) => void;
  onSimulate: (clause: Clause) => void;
}

export const ClauseCard: React.FC<ClauseCardProps> = ({
  clause,
  isSelected,
  onSelect,
  onSimulate,
}) => {
  const [isRawExpanded, setIsRawExpanded] = useState(false);

  const handleCardClick = () => {
    onSelect(clause.id);
  };

  const handleSimulateClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onSimulate(clause);
  };

  const handleToggleRaw = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsRawExpanded(!isRawExpanded);
  };

  return (
    <article
      id={`clause-card-${clause.id}`}
      onClick={handleCardClick}
      className={`rounded-xl p-5 border transition-all duration-200 cursor-pointer bg-white ${
        isSelected
          ? 'border-stone-400 ring-1 ring-stone-900 shadow-sm'
          : 'border-stone-200/90 shadow-xs hover:shadow-sm hover:border-stone-300'
      }`}
    >
      {/* Header: Risk Badge + Plain-English Title */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <h3 className="text-sm sm:text-base font-semibold text-stone-900 tracking-tight leading-snug">
          {clause.title}
        </h3>
        <div className="flex-shrink-0">
          <RiskBadge level={clause.riskLevel} size="sm" />
        </div>
      </div>

      {/* Plain-English Breakdown: Human consequence */}
      <div className="p-3.5 rounded-lg bg-stone-50/90 border border-stone-200/80 mb-3.5">
        <p className="text-xs text-stone-700 leading-relaxed">
          {clause.plainSummary}
        </p>
      </div>

      {/* Action Row: Simulate Scenario + Raw Drawer Toggle */}
      <div className="flex items-center justify-between gap-2 pt-1">
        <button
          type="button"
          onClick={handleToggleRaw}
          className="inline-flex items-center gap-1 text-xs font-medium text-stone-500 hover:text-stone-800 transition-colors py-1"
        >
          <FileText className="h-3.5 w-3.5 text-stone-400" />
          <span>{isRawExpanded ? 'Hide Raw Wording' : 'View Raw Contract Wording'}</span>
          {isRawExpanded ? (
            <ChevronUp className="h-3.5 w-3.5" />
          ) : (
            <ChevronDown className="h-3.5 w-3.5" />
          )}
        </button>

        <button
          type="button"
          onClick={handleSimulateClick}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-stone-900 hover:bg-stone-800 text-stone-50 text-xs font-medium transition-all active:scale-95 shadow-xs group"
          title="Simulate worst-case outcome in Copilot"
        >
          <Sparkles className="h-3 w-3 text-amber-300 opacity-90 group-hover:opacity-100" />
          <span>Simulate Scenario</span>
          <ArrowRight className="h-3 w-3 opacity-60 group-hover:opacity-100 group-hover:translate-x-0.5 transition-transform" />
        </button>
      </div>

      {/* Collapsible Drawer: Raw Contract Wording */}
      {isRawExpanded && (
        <div className="mt-3 p-3 rounded-lg bg-stone-100/70 border border-stone-200 text-stone-700 text-xs font-mono leading-relaxed pl-3.5 border-l-2 border-l-stone-400 animate-in fade-in slide-in-from-top-1 duration-150">
          &ldquo;{clause.originalText}&rdquo;
        </div>
      )}
    </article>
  );
};
