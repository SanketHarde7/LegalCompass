import React, { useState, useRef } from 'react';
import {
  UploadCloud,
  FileText,
  AlertTriangle,
  Scale,
  ShieldAlert,
  Search,
  FileCheck,
  X,
} from 'lucide-react';
import { AnalysisProgress } from './AnalysisProgress';
import { useAppStore } from '../../store/useAppStore';
import { uploadContract } from '../../services/api';
import type { ContractDocument } from '../../types/contract';

export const LandingHero: React.FC = () => {
  const [isDragging, setIsDragging] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [analyzingFileMeta, setAnalyzingFileMeta] = useState<{
    name: string;
    sizeFormatted: string;
  } | null>(null);
  const [pendingDoc, setPendingDoc] = useState<ContractDocument | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const setDocument = useAppStore((state) => state.setDocument);
  const setUploading = useAppStore((state) => state.setUploading);

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024 * 1024) {
      return `${Math.round(bytes / 1024)} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const handleProcessFile = async (file: File) => {
    const validExts = ['.pdf', '.docx', '.txt'];
    const isSupported = validExts.some((ext) => file.name.toLowerCase().endsWith(ext));

    if (!isSupported) {
      setErrorMessage('Please upload a PDF (.pdf), Word (.docx), or text (.txt) document.');
      return;
    }

    if (file.size > 25 * 1024 * 1024) {
      setErrorMessage('File size exceeds the 25MB boundary limit.');
      return;
    }

    setErrorMessage(null);
    setPendingDoc(null);
    setAnalyzingFileMeta({
      name: file.name,
      sizeFormatted: formatFileSize(file.size),
    });
    setUploading(true);
    setIsAnalyzing(true);

    try {
      const realDoc = await uploadContract(file);
      setPendingDoc(realDoc);
    } catch (err: any) {
      console.warn('Upload error:', err);
      setUploading(false);
      setIsAnalyzing(false);
      setPendingDoc(null);

      const rejectionMsg =
        err?.message ||
        'The uploaded document does not appear to be a recognized legal contract or agreement. LegalCompass only analyzes enforceable agreements with contractual covenants.';
      setErrorMessage(rejectionMsg);
    }
  };

  const handleAnalysisComplete = () => {
    if (pendingDoc) {
      setDocument(pendingDoc);
    }
    setUploading(false);
    setIsAnalyzing(false);
    setPendingDoc(null);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleProcessFile(file);
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleProcessFile(file);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="h-full w-full overflow-y-auto flex flex-col items-center justify-center p-6 sm:p-12 relative bg-[#FAF9F6]">
      <div className="max-w-4xl w-full text-center space-y-8 my-auto py-8">
        {/* Top Hero Badges */}
        <div className="space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-stone-100 border border-stone-200 text-stone-700 text-xs font-semibold tracking-wide">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>AI Legal Risk Copilot &bull; Zero Hallucination Engine</span>
          </div>

          <h1
            className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-stone-900 leading-[1.15]"
            style={{ fontFamily: "'Newsreader', serif" }}
          >
            Never Sign a Bad Contract Again.
          </h1>

          <p className="text-sm sm:text-base text-stone-600 max-w-2xl mx-auto leading-relaxed">
            LegalCompass stress-tests your agreements against hidden liabilities, unilateral termination traps, and IP forfeitures—transforming complex legalese into clear negotiation leverage.
          </p>
        </div>

        {/* Error Notice if Document Rejected */}
        {errorMessage && (
          <div className="max-w-xl mx-auto p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 text-left animate-in fade-in duration-200">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-rose-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <h4 className="text-xs font-bold text-rose-900 uppercase tracking-wide">
                  Document Rejection Notice
                </h4>
                <p className="text-xs text-rose-700 mt-1 leading-relaxed">
                  {errorMessage}
                </p>
                <p className="text-[11px] text-rose-600/90 mt-2">
                  Please upload a standard contract (e.g. Master Services Agreement, Lease, NDA, or Terms of Service) to begin analysis.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setErrorMessage(null)}
                className="text-rose-400 hover:text-rose-700 p-1 rounded-md"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}

        {/* Dynamic State: Progress or Dropzone */}
        {isAnalyzing ? (
          <div className="max-w-md mx-auto py-4 space-y-4">
            {analyzingFileMeta && (
              <div className="flex items-center justify-center gap-2 px-3.5 py-1.5 rounded-full bg-stone-100 border border-stone-200 text-stone-600 text-xs font-medium max-w-md mx-auto truncate">
                <FileText className="h-3.5 w-3.5 text-stone-500 flex-shrink-0" />
                <span className="truncate font-semibold text-stone-800">{analyzingFileMeta.name}</span>
                <span className="text-stone-300">&bull;</span>
                <span>{analyzingFileMeta.sizeFormatted}</span>
              </div>
            )}
            <AnalysisProgress
              isVisible={isAnalyzing}
              isReady={Boolean(pendingDoc)}
              onComplete={handleAnalysisComplete}
            />
          </div>
        ) : (
          <div className="max-w-3xl mx-auto space-y-6">
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.txt"
              className="hidden"
              onChange={handleFileInputChange}
            />

            {/* Minimalist Dropzone */}
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-2xl p-8 sm:p-10 text-center cursor-pointer transition-all duration-200 bg-white ${
                isDragging
                  ? 'border-stone-800 bg-stone-50/80 scale-[0.99] shadow-md'
                  : 'border-stone-300 hover:border-stone-400 hover:shadow-sm'
              }`}
            >
              <div className="h-12 w-12 rounded-xl bg-stone-100 text-stone-700 flex items-center justify-center mx-auto mb-3 border border-stone-200 group-hover:scale-105 transition-transform">
                <UploadCloud className="h-6 w-6 text-stone-600" />
              </div>

              <h3 className="text-sm sm:text-base font-semibold text-stone-900">
                Drop your contract PDF, DOCX, or TXT here
              </h3>
              <p className="text-xs text-stone-500 mt-1">
                or <span className="text-stone-800 underline underline-offset-2 font-medium">browse local files</span> from your computer
              </p>

              <div className="mt-4 flex items-center justify-center gap-3 text-[11px] text-stone-400 font-medium">
                <span>PDF, DOCX, TXT</span>
                <span>&bull;</span>
                <span>Up to 25MB</span>
                <span>&bull;</span>
                <span>Exact 1:1 Page Extraction</span>
              </div>
            </div>

            {/* Feature Highlights */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 text-left">
              <div className="p-3.5 rounded-xl bg-white border border-stone-200 shadow-sm">
                <div className="h-7 w-7 rounded-lg bg-rose-50 text-rose-700 border border-rose-200 flex items-center justify-center mb-2">
                  <ShieldAlert className="h-4 w-4" />
                </div>
                <div className="text-xs font-semibold text-stone-900">
                  Substantive Risk Audit
                </div>
                <p className="text-[11px] text-stone-500 mt-1 leading-relaxed">
                  Identifies predatory liabilities, unilateral cancellations, and hidden lock-ins.
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-white border border-stone-200 shadow-sm">
                <div className="h-7 w-7 rounded-lg bg-stone-100 text-stone-800 border border-stone-200 flex items-center justify-center mb-2">
                  <Search className="h-4 w-4" />
                </div>
                <div className="text-xs font-semibold text-stone-900">
                  Verbatim Traceability
                </div>
                <p className="text-[11px] text-stone-500 mt-1 leading-relaxed">
                  Every finding links directly to exact clauses and page offsets with zero hallucinations.
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-white border border-stone-200 shadow-sm">
                <div className="h-7 w-7 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center justify-center mb-2">
                  <FileCheck className="h-4 w-4" />
                </div>
                <div className="text-xs font-semibold text-stone-900">
                  Counsel-Ready Briefs
                </div>
                <p className="text-[11px] text-stone-500 mt-1 leading-relaxed">
                  Generates downloadable Attorney Briefs with structured counter-amendment redlines.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Disclaimer */}
        <div className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-stone-100 border border-stone-200 text-stone-500 text-[11px]">
          <Scale className="h-3.5 w-3.5 flex-shrink-0" />
          <span>Informational preparation aid &bull; Not formal legal counsel</span>
        </div>
      </div>
    </div>
  );
};
