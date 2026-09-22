import React, { useEffect, useState, useRef } from 'react';
import { CheckCircle2, Loader2, Circle, Sparkles } from 'lucide-react';

export interface AnalysisProgressProps {
  onComplete: () => void;
  isVisible: boolean;
  isReady?: boolean;
}

interface StepInfo {
  id: number;
  label: string;
  detail: string;
}

const STEPS: StepInfo[] = [
  {
    id: 1,
    label: 'Structure & OCR Extraction',
    detail: 'Extracting exact pages, tables, and clause boundaries...',
  },
  {
    id: 2,
    label: 'Liability & Risk Audit',
    detail: 'Auditing liability caps, indemnity, and asymmetric clauses...',
  },
  {
    id: 3,
    label: 'Plain-English Synthesis',
    detail: 'Synthesizing plain-English explanations and negotiation pushbacks...',
  },
];

export const AnalysisProgress: React.FC<AnalysisProgressProps> = ({
  onComplete,
  isVisible,
  isReady = false,
}) => {
  const [currentStep, setCurrentStep] = useState(1);
  const [progressPercent, setProgressPercent] = useState(15);
  const hasTriggeredCompleteRef = useRef(false);
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;

  // Single unified controller effect for progress pipeline
  useEffect(() => {
    if (!isVisible) {
      setCurrentStep(1);
      setProgressPercent(15);
      hasTriggeredCompleteRef.current = false;
      return;
    }

    hasTriggeredCompleteRef.current = false;
    setCurrentStep(1);
    setProgressPercent(15);

    const timeouts: ReturnType<typeof setTimeout>[] = [];

    // Stage 1: Fast initial extraction
    timeouts.push(
      setTimeout(() => {
        setProgressPercent(35);
      }, 150)
    );

    // Stage 2: Liability & Risk Audit
    timeouts.push(
      setTimeout(() => {
        setCurrentStep(2);
        setProgressPercent(65);
      }, 800)
    );

    // Stage 3: Plain-English Synthesis (approaching completion)
    timeouts.push(
      setTimeout(() => {
        setCurrentStep(3);
        setProgressPercent(88);
      }, 1800)
    );

    // Subtle drift while waiting for live backend completion
    timeouts.push(
      setTimeout(() => {
        setProgressPercent(93);
      }, 3500)
    );

    return () => {
      timeouts.forEach(clearTimeout);
    };
  }, [isVisible]);

  // When document is ready (isReady === true) from backend or preset, complete cleanly
  useEffect(() => {
    if (!isVisible || !isReady || hasTriggeredCompleteRef.current) return;

    setProgressPercent(100);
    setCurrentStep(4);

    const finishTimer = setTimeout(() => {
      if (!hasTriggeredCompleteRef.current) {
        hasTriggeredCompleteRef.current = true;
        onCompleteRef.current();
      }
    }, 400);

    return () => clearTimeout(finishTimer);
  }, [isVisible, isReady]);

  if (!isVisible) return null;

  return (
    <div className="bg-white border border-stone-200 shadow-sm p-6 sm:p-7 rounded-xl max-w-md mx-auto text-center space-y-5">
      {/* Header Badge */}
      <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-stone-100 text-stone-700 text-xs font-semibold border border-stone-200">
        <Sparkles className="h-3.5 w-3.5 text-stone-500 animate-pulse" />
        <span>Deep Clause Intelligence Ingestion</span>
      </div>

      {/* Title & Active Step Subtitle */}
      <div>
        <h3 className="text-base font-bold text-stone-900 tracking-tight">
          Auditing Contract Terms
        </h3>
        <p className="text-xs text-stone-500 mt-1 min-h-[20px] transition-all">
          {currentStep === 1 && STEPS[0].detail}
          {currentStep === 2 && STEPS[1].detail}
          {currentStep === 3 && (isReady ? 'Finalizing analysis...' : STEPS[2].detail)}
          {currentStep >= 4 && 'Ingestion complete! Loading workspace...'}
        </p>
      </div>

      {/* Progress Bar */}
      <div className="space-y-1.5">
        <div className="h-1.5 w-full bg-stone-100 overflow-hidden rounded-full">
          <div
            className="h-full bg-stone-900 rounded-full transition-all duration-400 ease-out"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <div className="flex justify-between items-center text-[10px] font-mono text-stone-400">
          <span>PIPELINE EXECUTION</span>
          <span>{progressPercent}%</span>
        </div>
      </div>

      {/* 3-Stage Checklist */}
      <div className="divide-y divide-stone-100 border-t border-b border-stone-100 py-1 text-left">
        {STEPS.map((step) => {
          const isFinished = currentStep > step.id;
          const isActive = currentStep === step.id;

          return (
            <div
              key={step.id}
              className={`flex items-center justify-between py-2.5 px-2 rounded-lg transition-colors ${
                isActive ? 'bg-stone-50/80 font-medium' : ''
              }`}
            >
              <div className="flex items-center gap-2.5 min-w-0">
                {isFinished ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-600 flex-shrink-0" />
                ) : isActive ? (
                  <Loader2 className="h-4 w-4 text-stone-800 animate-spin flex-shrink-0" />
                ) : (
                  <Circle className="h-4 w-4 text-stone-300 flex-shrink-0" />
                )}
                <span
                  className={`text-xs truncate ${
                    isFinished
                      ? 'text-stone-700'
                      : isActive
                      ? 'text-stone-900 font-semibold'
                      : 'text-stone-400'
                  }`}
                >
                  {step.label}
                </span>
              </div>

              <span
                className={`text-[11px] font-mono ${
                  isFinished
                    ? 'text-emerald-600'
                    : isActive
                    ? 'text-stone-700 font-semibold'
                    : 'text-stone-300'
                }`}
              >
                {isFinished ? 'Done' : isActive ? 'Analyzing...' : 'Queued'}
              </span>
            </div>
          );
        })}
      </div>

      {/* Bottom hint */}
      <p className="text-[11px] text-stone-400">
        Authentic page extraction &bull; Zero summarized omissions
      </p>
    </div>
  );
};
