import React from 'react';
import { FileX, BookOpen, AlertTriangle } from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';
import { FairnessMeter } from '../analysis/FairnessMeter';
import { PageView } from './pageView/PageView';

export const DocumentPanel: React.FC = () => {
  const document = useAppStore((state) => state.document);

  const clauses = document?.clauses ?? [];
  const highRisksCount = clauses.filter((c) => c.riskLevel === 'HIGH' && c.isRiskBearing !== false).length;
  const mediumRisksCount = clauses.filter((c) => c.riskLevel === 'MEDIUM' && c.isRiskBearing !== false).length;

  if (!document) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
        <FileX className="h-12 w-12 text-stone-300 mb-3" />
        <h3 className="text-base font-semibold text-stone-700">No Contract Loaded</h3>
        <p className="text-xs text-stone-400 mt-1 max-w-sm">
          Upload a contract or click LegalCompass in the top bar to load the sample agreement.
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full min-h-0 overflow-hidden">
      {/* Sticky Top Header */}
      <div className="p-4 sm:p-5 border-b border-stone-200 bg-white/95 backdrop-blur-sm space-y-3 flex-shrink-0">
        <FairnessMeter
          score={document.overallFairnessScore}
          totalClauses={clauses.length}
          highRisks={highRisksCount}
          mediumRisks={mediumRisksCount}
        />

        {/* Clean Document Reader Status Bar */}
        <div className="flex items-center justify-between pt-0.5 text-xs text-stone-500">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 font-semibold text-stone-800">
              <BookOpen className="h-3.5 w-3.5 text-stone-600" />
              Document Reader
            </span>
            <span className="text-stone-300">•</span>
            <span className="font-mono text-[11px] text-stone-500">
              {document.totalPages} {document.totalPages === 1 ? 'Page' : 'Pages'}
            </span>
            {highRisksCount > 0 && (
              <>
                <span className="text-stone-300">•</span>
                <span className="inline-flex items-center gap-1 text-[11px] text-rose-700 font-medium bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
                  <AlertTriangle className="h-3 w-3" />
                  {highRisksCount} High Risk {highRisksCount === 1 ? 'Trap' : 'Traps'}
                </span>
              </>
            )}
          </div>
          <div className="text-[11px] text-stone-400 hidden sm:flex items-center gap-1.5">
            <span>Click any highlighted clause to inspect</span>
          </div>
        </div>
      </div>

      {/* Main Document Reader Content: Always Page View */}
      <PageView />
    </div>
  );
};
