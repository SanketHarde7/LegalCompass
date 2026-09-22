import React from 'react';

export interface PageRailProps {
  totalPages: number;
  activePage: number;
  riskPages: number[];
  onPageSelect: (page: number) => void;
}

export const PageRail: React.FC<PageRailProps> = ({
  totalPages,
  activePage,
  riskPages,
  onPageSelect,
}) => {
  const pages = Array.from({ length: Math.max(1, totalPages) }, (_, i) => i + 1);

  return (
    <div className="w-full h-full flex flex-col items-center py-2 space-y-1.5 overflow-y-auto min-h-0 select-none px-1.5">
      <span className="text-[9px] font-mono font-bold uppercase tracking-wider text-stone-400 mb-1">
        Pages
      </span>

      {pages.map((pageNum) => {
        const isActive = activePage === pageNum;
        const hasHighRisk = riskPages.includes(pageNum);

        return (
          <button
            key={pageNum}
            type="button"
            onClick={() => onPageSelect(pageNum)}
            title={`Page ${pageNum}${hasHighRisk ? ' • Contains high-risk clauses' : ''}`}
            className={`relative w-full py-2 px-1.5 rounded-lg flex flex-col items-center justify-center transition-all group ${
              isActive
                ? 'bg-stone-900 text-white shadow-sm ring-1 ring-stone-900'
                : 'bg-white hover:bg-stone-50 text-stone-600 hover:text-stone-900 border border-stone-200/90 shadow-2xs'
            }`}
          >
            <span className="text-[11px] font-mono font-medium tracking-tight whitespace-nowrap">
              Page {pageNum}
            </span>

            {/* High-Risk Indicator Dot */}
            {hasHighRisk && (
              <span
                className={`w-1.5 h-1.5 rounded-full bg-rose-500 mt-1 ${
                  isActive ? 'ring-1 ring-white' : ''
                }`}
              />
            )}
          </button>
        );
      })}
    </div>
  );
};
