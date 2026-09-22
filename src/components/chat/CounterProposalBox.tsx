import React, { useState } from 'react';
import { ShieldCheck, Copy, Check } from 'lucide-react';

export interface CounterProposalBoxProps {
  text: string;
}

export const CounterProposalBox: React.FC<CounterProposalBoxProps> = ({ text }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2200);
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
    }
  };

  return (
    <div className="mt-3 p-4 rounded-xl bg-emerald-50/50 border border-emerald-200/60">
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-1.5 text-emerald-700 text-xs font-bold uppercase tracking-wider">
          <ShieldCheck className="h-4 w-4 flex-shrink-0" />
          <span>Recommended Balanced Counter-Clause</span>
        </div>
        <button
          type="button"
          onClick={handleCopy}
          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-[11px] font-semibold transition-all active:scale-95 shadow-sm border ${
            copied
              ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
              : 'bg-white hover:bg-stone-50 text-stone-600 hover:text-stone-800 border-stone-200'
          }`}
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5 text-emerald-600" />
              <span className="text-emerald-700 font-semibold">Copied to Clipboard!</span>
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5 text-stone-400" />
              <span>Copy Clause</span>
            </>
          )}
        </button>
      </div>

      <div className="p-3 rounded-lg bg-white border border-stone-200 text-xs text-stone-800 leading-relaxed select-all font-mono">
        {text}
      </div>

      <p className="text-[11px] text-stone-400 mt-2 italic">
        You can propose this revision to your counterparty or bring it to an attorney for formal review.
      </p>
    </div>
  );
};
