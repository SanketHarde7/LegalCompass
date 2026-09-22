import React from 'react';
import type { Clause } from '../../../types/contract';
import { useAppStore } from '../../../store/useAppStore';
import { Scale } from 'lucide-react';

export interface PageCanvasProps {
  clauses: Clause[];
  selectedClauseId: string | null;
  onClauseClick: (id: string) => void;
  pageRefs: React.MutableRefObject<Record<number, HTMLDivElement | null>>;
  totalPages: number;
}

export const PageCanvas: React.FC<PageCanvasProps> = ({
  clauses,
  selectedClauseId,
  onClauseClick,
  pageRefs,
  totalPages,
}) => {
  const document = useAppStore((state) => state.document);

  // Array of 1-indexed pages
  const pages = Array.from({ length: Math.max(1, totalPages) }, (_, i) => i + 1);

  // Helper to render text with clean inline marker highlights for flagged issues only
  const renderHighlightedContent = (
    text: string,
    pageClauses: Clause[]
  ): React.ReactNode => {
    // Strictly highlight ONLY clauses that represent actual risk issues or active selection
    const issueClauses = pageClauses.filter(
      (c) =>
        c.riskLevel === 'HIGH' ||
        c.riskLevel === 'MEDIUM' ||
        (c.unfairnessScore ?? 0) >= 50 ||
        c.id === selectedClauseId
    );

    if (issueClauses.length === 0 || !text) {
      return text;
    }

    // Collect all matches
    const matches: { start: number; end: number; clause: Clause }[] = [];

    for (const clause of issueClauses) {
      // Priority 1: Exact backend-provided startOffset/endOffset with validation
      if (
        clause.startOffset !== undefined &&
        clause.startOffset !== null &&
        clause.endOffset !== undefined &&
        clause.endOffset !== null &&
        clause.startOffset >= 0 &&
        clause.endOffset > clause.startOffset &&
        clause.endOffset <= text.length
      ) {
        const slice = text.slice(clause.startOffset, clause.endOffset);
        const raw = (clause.originalText || '').trim();
        const firstWord = raw.split(/\s+/)[0]?.toLowerCase() || '';

        // Verify the slice actually resembles the clause source text
        if (!firstWord || slice.toLowerCase().includes(firstWord)) {
          matches.push({
            start: clause.startOffset,
            end: clause.endOffset,
            clause,
          });
          continue;
        }
      }

      // Priority 2: Safe normalized source match
      if (clause.originalText) {
        const raw = clause.originalText.trim();
        if (raw.length >= 10) {
          // Direct exact substring
          const directIdx = text.indexOf(raw);
          if (directIdx !== -1) {
            matches.push({ start: directIdx, end: directIdx + raw.length, clause });
            continue;
          }

          // Distinctive first substantive line match
          const firstLine = raw.split('\n')[0].trim();
          if (firstLine.length >= 15) {
            const firstIdx = text.indexOf(firstLine);
            if (firstIdx !== -1) {
              const matchLen = Math.min(raw.length, text.length - firstIdx);
              matches.push({ start: firstIdx, end: firstIdx + matchLen, clause });
              continue;
            }
          }
        }
      }

      // Priority 3: No reliable location -> DO NOT HIGHLIGHT
      // Unreliable 3-word fuzzy fallback has been completely removed to prevent false highlights.
    }

    if (matches.length === 0) {
      return text;
    }

    // Sort matches by start position
    matches.sort((a, b) => a.start - b.start);

    const elements: React.ReactNode[] = [];
    let lastIndex = 0;

    for (let i = 0; i < matches.length; i++) {
      const { start, end, clause } = matches[i];
      if (start < lastIndex) continue; // Skip overlaps

      if (start > lastIndex) {
        elements.push(text.slice(lastIndex, start));
      }

      const isSelected = selectedClauseId === clause.id;
      const isHighRisk = clause.riskLevel === 'HIGH';

      elements.push(
        <mark
          key={`highlight-${clause.id}-${i}`}
          id={`page-clause-${clause.id}`}
          onClick={(e) => {
            e.stopPropagation();
            onClauseClick(clause.id);
          }}
          title={`Clause: ${clause.title} (${clause.riskLevel} Risk)`}
          className={`px-1 py-0.5 rounded-xs cursor-pointer select-text transition-colors ${
            isSelected
              ? 'bg-amber-200 text-stone-950 font-medium ring-1 ring-amber-400'
              : isHighRisk
              ? 'bg-rose-100/90 text-stone-900 border-b border-rose-300 hover:bg-rose-200'
              : 'bg-amber-100/90 text-stone-900 border-b border-amber-300 hover:bg-amber-200'
          }`}
        >
          {text.slice(start, end)}
        </mark>
      );

      lastIndex = end;
    }

    if (lastIndex < text.length) {
      elements.push(text.slice(lastIndex));
    }

    return <>{elements}</>;
  };

  return (
    <div className="space-y-8 pb-12">
      {pages.map((pageNum) => {
        const pageData = document?.pages?.find((p) => p.pageNumber === pageNum);
        const pageClauses = clauses.filter((c) => (c.pageNumber ?? 1) === pageNum);

        const fullPageText =
          pageData?.text ||
          pageClauses.map((c) => (c.title ? `${c.title}\n${c.originalText}` : c.originalText)).join('\n\n') ||
          '';

        return (
          <div
            key={pageNum}
            ref={(el) => {
              pageRefs.current[pageNum] = el;
            }}
            id={`page-sheet-${pageNum}`}
            className="bg-white border border-stone-200/90 shadow-sm rounded-xl p-8 sm:p-10 mb-6 max-w-2xl mx-auto text-stone-800 relative transition-all"
            style={{ minHeight: '640px' }}
          >
            {/* Document Sheet Header */}
            <div className="border-b border-stone-200 pb-3 mb-6 flex items-center justify-between text-[11px] font-mono text-stone-400 uppercase tracking-widest select-none">
              <div className="flex items-center gap-1.5 truncate max-w-[70%]">
                <Scale className="h-3.5 w-3.5 text-stone-400 flex-shrink-0" />
                <span className="truncate font-medium text-stone-600">
                  {document?.filename || 'Contract Document'}
                </span>
              </div>
              <span className="font-semibold text-stone-500 flex-shrink-0">
                Page {pageNum} of {totalPages}
              </span>
            </div>

            {/* Page Content: Full Unabridged Text with Inline Marker Highlights */}
            <div className="font-serif text-xs sm:text-[13px] leading-relaxed text-stone-800 whitespace-pre-wrap">
              {renderHighlightedContent(fullPageText, pageClauses)}
            </div>

            {/* Clean Running Page Bottom */}
            <div className="pt-8 mt-8 border-t border-stone-100 flex items-center justify-between text-[10px] text-stone-400 font-mono select-none">
              <span>LEGALCOMPASS AUDIT VIEWER</span>
              <span>PAGE {pageNum} OF {totalPages}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
};
