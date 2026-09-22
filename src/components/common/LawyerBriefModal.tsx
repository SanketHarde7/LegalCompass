import React, { useState, useEffect } from 'react';
import {
  X,
  Printer,
  ShieldAlert,
  Copy,
  Check,
} from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';

export interface LawyerBriefModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const LawyerBriefModal: React.FC<LawyerBriefModalProps> = ({ isOpen, onClose }) => {
  const [isCopied, setIsCopied] = useState(false);
  const document = useAppStore((state) => state.document);
  const activePresetKey = useAppStore((state) => state.activePresetKey);

  // Close on Escape key press
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !document) return null;

  const clauses = document.clauses;
  const highRiskClauses = clauses.filter((c) => c.riskLevel === 'HIGH');
  const mediumRiskClauses = clauses.filter((c) => c.riskLevel === 'MEDIUM');
  const score = document.overallFairnessScore;

  const currentDate = new Date().toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  // Tailored Questions for Attorney based on active contract type
  const getTailoredQuestions = (): string[] => {
    if (activePresetKey === 'lease' || document.filename.toLowerCase().includes('lease')) {
      return [
        'Does local residential tenancy statute supersede the waiver of 24-hour advance written notice for landlord entry?',
        'Can we strike the 20% automatic rent escalation and restrict renewal increases to the local Consumer Price Index (CPI)?',
        'Is it legally permissible for a landlord to deduct from a tenant security deposit for routine wear and tear or carpet aging?',
        'What are the tenant\'s statutory remedies (e.g., rent withholding or repair-and-deduct) if essential heating or plumbing is not repaired within 24 hours?',
      ];
    }

    if (activePresetKey === 'nda' || document.filename.toLowerCase().includes('nda')) {
      return [
        'Does the definition of Confidential Information properly exclude information independently developed or already in our possession prior to execution?',
        'Can we add an explicit carve-out permitting disclosure to legal counsel and financial advisors under professional duty of confidentiality?',
        'Is a 2-year survivability term sufficient for proprietary technological disclosures, or should trade secrets be expressly carved out?',
        'What are the required notice procedures if confidential information is compelled by judicial subpoena or regulatory authority?',
      ];
    }

    // Default / Freelance
    return [
      'Can we condition all intellectual property transfers strictly upon full and complete receipt of invoiced compensation?',
      'Can we negotiate a mutual 30-day notice period for termination and eliminate any forfeiture of unbilled or in-progress work?',
      'Can we cap aggregate contractor indemnification liability to the total fees actually collected under this agreement?',
      'What objective acceptance criteria can we establish to prevent arbitrary fee withholding under subjective satisfaction clauses?',
    ];
  };

  const tailoredQuestions = getTailoredQuestions();

  // Clauses with suggested revisions for Appendix
  const counterLanguageClauses = clauses.filter((c) => Boolean(c.suggestion));

  const handlePrint = () => {
    window.print();
  };

  const handleCopyMarkdown = async () => {
    const questionsText = tailoredQuestions.map((q, i) => `${i + 1}. "${q}"`).join('\n');
    const trapsText = highRiskClauses.map((c) => `- **${c.title}** (${c.riskLevel}): ${c.plainSummary}`).join('\n');
    const appendixText = counterLanguageClauses
      .map((c) => `### ${c.title}\n> ${c.suggestion}`)
      .join('\n\n');

    const briefMarkdown = `# LEGALCOMPASS • PRE-CONSULTATION RISK ASSESSMENT
**Document:** ${document.filename}
**Date Generated:** ${currentDate}
**Overall Fairness Score:** ${score}/100
**High Risk Imbalances:** ${highRiskClauses.length} | **Medium Risk Concerns:** ${mediumRiskClauses.length}

---

## Non-Advice Legal Disclaimer
Prepared for informational and attorney preparation purposes only under the LegalCompass open evaluation model. Does not constitute formal legal representation. Consult a licensed attorney for binding contract review and negotiations.

---

## Executive Risk Summary
${trapsText || 'No critical high-risk traps identified.'}

---

## Targeted Questions for Licensed Counsel
${questionsText}

---

## Appendix: Proposed Counter-Draft Provisions
${appendixText || 'No preliminary counter-draft revisions requested.'}
`;

    try {
      await navigator.clipboard.writeText(briefMarkdown);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2200);
    } catch (err) {
      console.error('Failed to copy brief to clipboard:', err);
    }
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4 print:static print:p-0 print:bg-white print:block print:overflow-visible"
      onClick={handleBackdropClick}
    >
      <div className="relative bg-white rounded-2xl shadow-2xl border border-stone-200 max-w-2xl w-full max-h-[90vh] overflow-y-auto print:max-w-none print:w-full print:max-h-none print:overflow-visible print:shadow-none print:border-none print:p-0 print:m-0 print:text-black">
        
        {/* Close Button (Hidden on Print) */}
        <button
          type="button"
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg bg-stone-100 hover:bg-stone-200 text-stone-500 hover:text-stone-700 transition-colors z-10 print:hidden"
          title="Close (Esc)"
        >
          <X className="h-4 w-4" />
        </button>

        {/* Printable Legal Memorandum Container */}
        <div className="p-8 sm:p-10 space-y-7 print:p-8 print:space-y-6">
          
          {/* Memorandum Header */}
          <div className="border-b-2 border-stone-900 pb-5">
            <div className="flex items-center justify-between gap-4 mb-2">
              <span className="text-[11px] font-mono uppercase tracking-widest text-stone-500 font-bold">
                LEGALCOMPASS &bull; PRE-CONSULTATION RISK ASSESSMENT
              </span>
              <span className="text-[11px] font-mono text-stone-400">
                CONFIDENTIAL &bull; ATTORNEY-CLIENT PREP
              </span>
            </div>

            <h1
              className="text-2xl sm:text-3xl font-bold text-stone-900 tracking-tight"
              style={{ fontFamily: "'Newsreader', serif" }}
            >
              Legal Risk Audit Memorandum
            </h1>

            {/* Metadata Grid */}
            <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3 p-3.5 rounded-xl bg-stone-50 border border-stone-200 text-xs">
              <div>
                <span className="text-stone-400 block text-[10px] uppercase font-semibold">Contract File</span>
                <span className="font-semibold text-stone-900 truncate block mt-0.5" title={document.filename}>
                  {document.filename}
                </span>
              </div>
              <div>
                <span className="text-stone-400 block text-[10px] uppercase font-semibold">Assessment Date</span>
                <span className="font-medium text-stone-800 block mt-0.5">{currentDate}</span>
              </div>
              <div>
                <span className="text-stone-400 block text-[10px] uppercase font-semibold">Fairness Score</span>
                <span className="font-bold text-stone-900 block mt-0.5">
                  {score}/100 ({score < 50 ? 'High Risk' : score < 75 ? 'Moderate' : 'Balanced'})
                </span>
              </div>
              <div>
                <span className="text-stone-400 block text-[10px] uppercase font-semibold">Flagged Imbalances</span>
                <span className="font-medium text-stone-800 block mt-0.5">
                  {highRiskClauses.length} High &bull; {mediumRiskClauses.length} Med
                </span>
              </div>
            </div>

            {/* Non-Advice Legal Disclaimer Banner */}
            <div className="mt-3.5 flex items-start gap-2 p-3 rounded-lg bg-amber-50 border border-amber-200/70 text-amber-800 text-xs">
              <ShieldAlert className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
              <p className="leading-relaxed">
                <strong>NON-ADVICE LEGAL DISCLAIMER:</strong> Prepared for informational and attorney preparation purposes only under the LegalCompass open evaluation model. Does not constitute formal legal representation or binding statutory advice.
              </p>
            </div>
          </div>

          {/* Section 1: Executive Health Index & Summary */}
          <section className="space-y-3">
            <h2
              className="text-base font-bold text-stone-900 flex items-center gap-2 border-b border-stone-200 pb-1.5"
              style={{ fontFamily: "'Newsreader', serif" }}
            >
              <span className="text-stone-400 font-mono text-xs">&sect; 1.</span>
              Executive Risk &amp; Exposure Summary
            </h2>

            <div className="flex items-center gap-5 p-4 rounded-xl bg-stone-50 border border-stone-200">
              <div className="text-center min-w-[75px]">
                <span className="text-3xl sm:text-4xl font-bold text-stone-900">{score}</span>
                <span className="text-xs text-stone-400 block">/ 100</span>
              </div>
              <div className="flex-1 space-y-1.5 border-l border-stone-200 pl-4">
                <div className="h-2 w-full bg-stone-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      score >= 75 ? 'bg-emerald-600' : score >= 50 ? 'bg-amber-500' : 'bg-rose-600'
                    }`}
                    style={{ width: `${score}%` }}
                  />
                </div>
                <p className="text-xs text-stone-600 leading-relaxed">
                  {score < 50
                    ? 'Predatory or heavily one-sided terms identified. Key exposures include uncapped liabilities and unilateral exit penalties.'
                    : score < 75
                    ? 'Moderate commercial imbalances detected. Requires clarification on notice windows and default cure periods.'
                    : 'Balanced reciprocal agreement generally adhering to standard commercial norms.'}
                </p>
              </div>
            </div>

            {highRiskClauses.length > 0 && (
              <div className="p-4 rounded-xl bg-rose-50/70 border border-rose-200 text-xs space-y-2">
                <span className="font-bold text-rose-800 uppercase tracking-wider text-[10px] block">
                  Critical High-Exposure Traps Identified:
                </span>
                <ul className="list-disc list-inside space-y-1.5 text-stone-800">
                  {highRiskClauses.map((c) => (
                    <li key={c.id}>
                      <strong>{c.title}:</strong> {c.plainSummary}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>

          {/* Section 2: Targeted Questions for Licensed Counsel */}
          <section className="space-y-3">
            <h2
              className="text-base font-bold text-stone-900 flex items-center gap-2 border-b border-stone-200 pb-1.5"
              style={{ fontFamily: "'Newsreader', serif" }}
            >
              <span className="text-stone-400 font-mono text-xs">&sect; 2.</span>
              Targeted Negotiation Questions for Licensed Counsel
            </h2>

            <div className="space-y-2.5">
              {tailoredQuestions.map((q, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-2.5 p-3 rounded-lg bg-stone-50 border border-stone-200 text-xs text-stone-800"
                >
                  <span className="h-5 w-5 rounded-full bg-stone-200 text-stone-700 font-bold flex items-center justify-center text-[10px] flex-shrink-0 mt-0.5">
                    {idx + 1}
                  </span>
                  <p className="leading-relaxed italic">&ldquo;{q}&rdquo;</p>
                </div>
              ))}
            </div>
          </section>

          {/* Section 3: Proposed Counter-Language Appendix */}
          <section className="space-y-3">
            <h2
              className="text-base font-bold text-stone-900 flex items-center gap-2 border-b border-stone-200 pb-1.5"
              style={{ fontFamily: "'Newsreader', serif" }}
            >
              <span className="text-stone-400 font-mono text-xs">&sect; 3.</span>
              Proposed Counter-Language Appendix (Pre-Drafted Provisions)
            </h2>

            <div className="space-y-3">
              {counterLanguageClauses.map((clause) => (
                <div
                  key={clause.id}
                  className="p-3.5 rounded-xl bg-stone-50 border border-stone-200 text-xs space-y-1.5"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-bold text-stone-900">{clause.title}</span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                        clause.riskLevel === 'HIGH'
                          ? 'bg-rose-50 text-rose-700 border-rose-200'
                          : 'bg-amber-50 text-amber-700 border-amber-200'
                      }`}
                    >
                      Target: {clause.riskLevel} Risk
                    </span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-white border border-stone-200 font-mono text-[11px] text-stone-800 leading-relaxed">
                    {clause.suggestion}
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Document Certification Sign-off Footer */}
          <div className="border-t-2 border-stone-200 pt-4 text-[10px] text-stone-400 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <span>AUDIT HASH: {document.sessionId} &bull; TIMESTAMP: {document.uploadTimestamp}</span>
            <span>PREPARED VIA LEGALCOMPASS</span>
          </div>
        </div>

        {/* Action Footer (Hidden on Print) */}
        <div className="sticky bottom-0 p-4 border-t border-stone-200 bg-white/95 backdrop-blur-sm flex items-center justify-between gap-3 rounded-b-2xl print:hidden">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-white border border-stone-200 text-stone-600 hover:bg-stone-50 text-xs font-medium transition-colors shadow-sm"
          >
            Close (Esc)
          </button>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleCopyMarkdown}
              className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold border transition-all active:scale-95 shadow-sm ${
                isCopied
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
                  : 'bg-white hover:bg-stone-50 text-stone-700 border-stone-200'
              }`}
            >
              {isCopied ? (
                <>
                  <Check className="h-3.5 w-3.5 text-emerald-600" />
                  <span>Copied Brief to Clipboard!</span>
                </>
              ) : (
                <>
                  <Copy className="h-3.5 w-3.5 text-stone-400" />
                  <span>Copy Brief as Text</span>
                </>
              )}
            </button>

            <button
              type="button"
              onClick={handlePrint}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-stone-900 hover:bg-stone-800 text-white text-xs font-semibold transition-all active:scale-95 shadow-sm"
            >
              <Printer className="h-3.5 w-3.5" />
              <span>Download / Print Brief (PDF)</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
