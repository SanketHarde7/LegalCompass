import React, { useState, useRef, useCallback, useEffect } from 'react';
import {
  X,
  UploadCloud,
  FileText,
  AlertTriangle,
  Layers,
} from 'lucide-react';
import type { ContractDocument } from '../../types/contract';
import { uploadContract } from '../../services/api';
import { useAppStore } from '../../store/useAppStore';
import { AnalysisProgress } from './AnalysisProgress';

export interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onDocumentLoaded?: (doc: ContractDocument) => void;
  initialTab?: string;
}

interface UploadedFileMeta {
  name: string;
  sizeFormatted: string;
  estimatedPages: number;
}

export const UploadModal: React.FC<UploadModalProps> = ({
  isOpen,
  onClose,
  onDocumentLoaded,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [fileMeta, setFileMeta] = useState<UploadedFileMeta | null>(null);
  const [pendingDoc, setPendingDoc] = useState<ContractDocument | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const setDocument = useAppStore((state) => state.setDocument);
  const setUploading = useAppStore((state) => state.setUploading);

  // Clear errors when opening modal
  useEffect(() => {
    if (isOpen) {
      setErrorMessage(null);
    }
  }, [isOpen]);

  // Close on Escape key press (when not analyzing)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen && !isAnalyzing) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, isAnalyzing, onClose]);

  const resetState = useCallback(() => {
    setIsAnalyzing(false);
    setPendingDoc(null);
    setFileMeta(null);
    setIsDragging(false);
    setErrorMessage(null);
  }, []);

  const handleClose = () => {
    if (isAnalyzing) return; // Prevent closing mid-analysis
    resetState();
    onClose();
  };

  const handleAnalysisComplete = useCallback(() => {
    if (!pendingDoc) return;

    setDocument(pendingDoc);

    if (onDocumentLoaded) {
      onDocumentLoaded(pendingDoc);
    }

    setUploading(false);
    setIsAnalyzing(false);
    resetState();
    onClose();
  }, [pendingDoc, setDocument, onDocumentLoaded, setUploading, resetState, onClose]);

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024 * 1024) {
      return `${Math.round(bytes / 1024)} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const processFile = async (file: File) => {
    const isDocx = file.name.endsWith('.docx');
    const isPdf = file.name.endsWith('.pdf');
    const isTxt = file.name.endsWith('.txt');

    if (!isDocx && !isPdf && !isTxt) {
      setErrorMessage('Unsupported file format. Please upload a PDF (.pdf), Word (.docx), or plain text (.txt) document.');
      return;
    }

    if (file.size > 25 * 1024 * 1024) {
      setErrorMessage('File exceeds the 25MB boundary limit. Please select a smaller contract document.');
      return;
    }

    setErrorMessage(null);

    // Estimate pages: inspect buffer for PDF "/Type /Page" tokens if possible, else heuristic
    let estimatedPages = Math.max(1, Math.round(file.size / (48 * 1024)));
    try {
      if (isPdf) {
        const slice = await file.slice(0, 500000).text();
        const matches = slice.match(/\/Type\s*\/Page[^s]/g);
        if (matches && matches.length > 0) {
          estimatedPages = matches.length;
        }
      }
    } catch {
      // Fallback heuristic
    }

    setFileMeta({
      name: file.name,
      sizeFormatted: formatFileSize(file.size),
      estimatedPages,
    });

    setPendingDoc(null);
    setUploading(true);
    setIsAnalyzing(true);

    try {
      const realDoc = await uploadContract(file);
      setPendingDoc(realDoc);
    } catch (err: any) {
      console.warn('Backend upload encountered an error:', err);
      setUploading(false);
      setIsAnalyzing(false);
      setPendingDoc(null);

      const rejectionMsg =
        err?.message ||
        'The uploaded document does not appear to be a recognized legal contract or agreement. LegalCompass is specifically designed to analyze legal contracts (such as Master Services Agreements, Residential Leases, NDAs, or Terms of Service) with enforceable contractual terms.';
      setErrorMessage(rejectionMsg);
    }
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
    if (file) processFile(file);
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4 animate-in fade-in duration-200"
      onClick={(e) => e.target === e.currentTarget && handleClose()}
    >
      <div className="relative bg-[#FAF9F6] rounded-2xl shadow-2xl border border-stone-200 max-w-2xl w-full overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-6 border-b border-stone-200 bg-white/90 backdrop-blur-sm flex items-center justify-between flex-shrink-0">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-stone-400">
                Document Ingestion
              </span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-stone-100 text-stone-600 border border-stone-200">
                OCR &bull; AI Parser
              </span>
            </div>
            <h2
              className="text-xl font-bold text-stone-900 tracking-tight mt-0.5"
              style={{ fontFamily: "'Newsreader', serif" }}
            >
              Upload Contract
            </h2>
          </div>

          <button
            type="button"
            onClick={handleClose}
            disabled={isAnalyzing}
            className="p-1.5 rounded-lg bg-stone-100 hover:bg-stone-200 text-stone-500 hover:text-stone-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            title="Close (Esc)"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 overflow-y-auto flex-1">
          {errorMessage && (
            <div className="mb-5 p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-900 animate-in fade-in duration-200">
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
                    Tip: Upload a Master Services Agreement (MSA), Residential Apartment Lease, Non-Disclosure Agreement (NDA), or commercial terms of service.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setErrorMessage(null)}
                  className="text-rose-400 hover:text-rose-700 p-1 rounded-md"
                  title="Dismiss error"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}

          {isAnalyzing ? (
            <div className="py-4 space-y-4">
              {/* File Meta Badge */}
              {fileMeta && (
                <div className="flex items-center justify-center gap-2 px-3.5 py-1.5 rounded-full bg-stone-100 border border-stone-200 text-stone-600 text-xs font-medium max-w-md mx-auto truncate">
                  <FileText className="h-3.5 w-3.5 text-stone-500 flex-shrink-0" />
                  <span className="truncate font-semibold text-stone-800">{fileMeta.name}</span>
                  <span className="text-stone-300">&bull;</span>
                  <span>{fileMeta.sizeFormatted}</span>
                  <span className="text-stone-300">&bull;</span>
                  <span className="flex items-center gap-1">
                    <Layers className="h-3 w-3" /> ~{fileMeta.estimatedPages} {fileMeta.estimatedPages === 1 ? 'page' : 'pages'}
                  </span>
                </div>
              )}

              <AnalysisProgress
                isVisible={isAnalyzing}
                isReady={Boolean(pendingDoc)}
                onComplete={handleAnalysisComplete}
              />
            </div>
          ) : (
            <div className="space-y-4">
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.txt"
                className="hidden"
                onChange={handleFileInputChange}
              />

              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all ${
                  isDragging
                    ? 'border-stone-900 bg-stone-100/80 scale-[0.99]'
                    : 'border-stone-300 bg-white hover:border-stone-400 hover:bg-stone-50/60'
                }`}
              >
                <div className="h-14 w-14 rounded-2xl bg-stone-100 text-stone-700 flex items-center justify-center mx-auto mb-3 border border-stone-200">
                  <UploadCloud className="h-7 w-7 text-stone-600" />
                </div>

                <h4 className="text-sm font-semibold text-stone-800">
                  Drag contract PDF, DOCX, or TXT here
                </h4>
                <p className="text-xs text-stone-400 mt-1">
                  or click to browse your local files
                </p>

                <div className="mt-4 flex items-center justify-center gap-3 text-[11px] text-stone-400 font-medium">
                  <span className="flex items-center gap-1">
                    <FileText className="h-3 w-3" /> PDF / DOCX / TXT
                  </span>
                  <span>&bull;</span>
                  <span>Up to 25MB</span>
                  <span>&bull;</span>
                  <span>1:1 Page Extraction</span>
                </div>
              </div>

              <div className="flex items-center gap-2 p-3 rounded-lg bg-stone-100/70 border border-stone-200 text-stone-600 text-xs">
                <AlertTriangle className="h-4 w-4 text-stone-400 flex-shrink-0" />
                <span>
                  Legal contracts are parsed securely in-memory. Random text or non-legal documents will be rejected.
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-stone-200 bg-white/80 backdrop-blur-sm flex items-center justify-between flex-shrink-0">
          <span className="text-[11px] text-stone-400">
            {isAnalyzing
              ? 'Executing deep clause analysis...'
              : 'Informational preparation aid &bull; Not formal legal advice'}
          </span>

          <button
            type="button"
            onClick={handleClose}
            disabled={isAnalyzing}
            className="px-4 py-2 rounded-lg bg-white border border-stone-200 text-stone-600 hover:bg-stone-50 text-xs font-medium transition-colors shadow-sm disabled:opacity-40"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};
