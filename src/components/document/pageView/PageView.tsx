import React, { useState, useRef, useEffect } from 'react';
import { useAppStore } from '../../../store/useAppStore';
import { PageRail } from './PageRail';
import { PageCanvas } from './PageCanvas';

export const PageView: React.FC = () => {
  const document = useAppStore((state) => state.document);
  const selectedClauseId = useAppStore((state) => state.selectedClauseId);
  const selectClause = useAppStore((state) => state.selectClause);

  const clauses = document?.clauses ?? [];

  // Calculate total pages from document metadata, page array, or clauses
  const totalPages =
    document?.totalPages ||
    (document?.pages && document.pages.length > 0
      ? document.pages.length
      : Math.max(1, ...clauses.map((c) => c.pageNumber ?? 1)));

  // Identify pages with high-risk clauses for the red indicator dot
  const riskPages = Array.from(
    new Set(
      clauses
        .filter((c) => c.riskLevel === 'HIGH' && c.isRiskBearing !== false)
        .map((c) => c.pageNumber ?? 1)
    )
  );

  const [activePage, setActivePage] = useState<number>(1);
  const pageRefs = useRef<Record<number, HTMLDivElement | null>>({});
  const canvasContainerRef = useRef<HTMLDivElement>(null);

  // Smooth scroll to selected clause if selection changes
  useEffect(() => {
    if (!selectedClauseId) return;
    const clause = clauses.find((c) => c.id === selectedClauseId);
    if (clause && clause.pageNumber) {
      setActivePage(clause.pageNumber);
      const clauseEl = window.document.getElementById(`page-clause-${selectedClauseId}`);
      if (clauseEl) {
        clauseEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }, [selectedClauseId, clauses]);

  const handlePageSelect = (page: number) => {
    setActivePage(page);
    const targetEl = pageRefs.current[page];
    if (targetEl) {
      targetEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  // Scroll listener to update active page thumbnail indicator as user scrolls
  useEffect(() => {
    const container = canvasContainerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const containerTop = container.scrollTop;

      for (let p = 1; p <= totalPages; p++) {
        const el = pageRefs.current[p];
        if (el) {
          const top = el.offsetTop - container.offsetTop;
          const height = el.offsetHeight;
          if (containerTop >= top - 120 && containerTop < top + height - 120) {
            setActivePage(p);
            break;
          }
        }
      }
    };

    container.addEventListener('scroll', handleScroll, { passive: true });
    return () => container.removeEventListener('scroll', handleScroll);
  }, [totalPages]);

  return (
    <div className="h-full w-full flex min-h-0 overflow-hidden bg-stone-100/60">
      {/* Sub-Panel A: Left Page Rail */}
      <div className="w-20 sm:w-22 border-r border-stone-200/80 bg-white/80 py-3 flex flex-col items-center overflow-y-auto flex-shrink-0">
        <PageRail
          totalPages={totalPages}
          activePage={activePage}
          riskPages={riskPages}
          onPageSelect={handlePageSelect}
        />
      </div>

      {/* Sub-Panel B: Main Document Canvas */}
      <div
        ref={canvasContainerRef}
        className="flex-1 h-full min-h-0 overflow-y-auto p-6 scroll-smooth bg-stone-100/50"
      >
        <PageCanvas
          clauses={clauses}
          selectedClauseId={selectedClauseId}
          onClauseClick={selectClause}
          pageRefs={pageRefs}
          totalPages={totalPages}
        />
      </div>
    </div>
  );
};
