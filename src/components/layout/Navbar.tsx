import React, { useState, useEffect } from 'react';
import {
  Compass,
  Upload,
  Download,
  Scale,
  FileText,
  CheckCircle2,
} from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';
import { exportConsultationBrief } from '../../services/api';

export interface NavbarProps {
  onOpenBriefModal?: () => void;
  onOpenUploadModal?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  onOpenBriefModal,
  onOpenUploadModal,
}) => {
  const [isExporting, setIsExporting] = useState(false);
  const [downloadSuccess, setDownloadSuccess] = useState(false);

  const document = useAppStore((state) => state.document);
  const isUploading = useAppStore((state) => state.isUploading);
  const backendConnected = useAppStore((state) => state.backendConnected);
  const checkBackendStatus = useAppStore((state) => state.checkBackendStatus);

  // Check backend health on mount and periodically
  useEffect(() => {
    checkBackendStatus();
    const interval = setInterval(checkBackendStatus, 15000);
    return () => clearInterval(interval);
  }, [checkBackendStatus]);

  const handleExportBrief = async () => {
    if (onOpenBriefModal) {
      onOpenBriefModal();
      return;
    }

    if (!document) return;
    try {
      setIsExporting(true);
      const blob = await exportConsultationBrief(document.sessionId);
      const url = window.URL.createObjectURL(blob);
      const link = window.document.createElement('a');
      link.href = url;
      link.download = `LegalCompass_Attorney_Brief_${document.sessionId}.pdf`;
      window.document.body.appendChild(link);
      link.click();
      window.document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      setDownloadSuccess(true);
      setTimeout(() => setDownloadSuccess(false), 3000);
    } catch (err) {
      console.error('Failed to export consultation brief:', err);
    } finally {
      setIsExporting(false);
    }
  };

  const fairnessScore = document?.overallFairnessScore ?? null;

  return (
    <header className="w-full h-14 bg-white/90 backdrop-blur-sm border-b border-stone-200 sticky top-0 z-50 flex-shrink-0">
      <div className="max-w-full mx-auto px-4 sm:px-6 h-full flex items-center justify-between gap-3">
        {/* Left: Branding & Preset Switcher */}
        <div className="flex items-center gap-3 min-w-0">
          <button
            type="button"
            onClick={() => {
              if (document) {
                // Return to home / landing
                useAppStore.getState().setDocument(null);
              }
            }}
            className="flex items-center gap-2 group flex-shrink-0"
            title="LegalCompass Home"
          >
            <div className="h-8 w-8 rounded-lg bg-stone-900 flex items-center justify-center shadow-sm group-hover:bg-stone-800 transition-colors">
              <Compass className="h-4.5 w-4.5 text-white" />
            </div>
            <div className="flex items-center">
              <span className="font-bold text-sm tracking-tight text-stone-900">
                LegalCompass
              </span>
              <span className="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded bg-stone-100 text-stone-400 border border-stone-200 ml-2">
                v1.0
              </span>
            </div>
          </button>

          {/* Active Contract Info Pill (Visible ONLY when document !== null) */}
          {document && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-stone-50 border border-stone-200 text-xs text-stone-700">
              <FileText className="h-3.5 w-3.5 text-stone-400 flex-shrink-0" />
              <div className="flex items-center gap-1.5 min-w-0">
                <span className="text-stone-400 hidden md:inline">Contract:</span>
                <span className="font-medium text-stone-800 truncate max-w-[130px] sm:max-w-[190px] md:max-w-[220px]">
                  {document.filename}
                </span>
              </div>

              {fairnessScore !== null && (
                <span
                  className={`px-1.5 py-0.5 rounded text-[10px] font-bold border ${
                    fairnessScore < 50
                      ? 'bg-rose-50 text-rose-700 border-rose-200/70'
                      : fairnessScore < 75
                      ? 'bg-amber-50 text-amber-700 border-amber-200/70'
                      : 'bg-emerald-50 text-emerald-700 border-emerald-200/70'
                  }`}
                >
                  {fairnessScore}/100
                </span>
              )}
            </div>
          )}
      </div>

        {/* Center: Legal Disclaimer */}
        <div className="hidden md:flex items-center justify-center flex-1">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-stone-50 border border-stone-200 text-stone-500 text-xs">
            <Scale className="h-3.5 w-3.5 flex-shrink-0" />
            <span>Informational &amp; Preparation Aid · Not Formal Legal Advice</span>
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2.5 flex-shrink-0">
          {/* Backend Status Indicator */}
          <div
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium border transition-all ${
              backendConnected
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200 shadow-sm'
                : 'bg-amber-50 text-amber-700 border-amber-200'
            }`}
            title={
              backendConnected
                ? 'FastAPI Backend: Connected (Live LLM & FastEmbed)'
                : 'FastAPI Backend: Offline'
            }
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                backendConnected ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'
              }`}
            />
            <span className="font-mono text-[10px]">
              {backendConnected ? 'Live AI' : 'Offline'}
            </span>
          </div>

          {/* Action buttons (Visible ONLY when document !== null) */}
          {document && (
            <>
              <button
                type="button"
                onClick={onOpenUploadModal}
                disabled={isUploading}
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white hover:bg-stone-50 border border-stone-200 text-stone-700 hover:text-stone-900 text-xs font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm group"
                title="Upload or Switch Contract (Ctrl+K / ⌘K)"
              >
                <Upload className={`h-3.5 w-3.5 text-stone-400 ${isUploading ? 'animate-bounce' : ''}`} />
                <span className="hidden sm:inline">{isUploading ? 'Analyzing...' : 'Upload Contract'}</span>
                <kbd className="hidden xl:inline-block px-1.5 py-0.5 text-[10px] font-mono font-medium rounded bg-stone-100 text-stone-400 border border-stone-200 group-hover:border-stone-300">
                  ⌘K
                </kbd>
              </button>

              <button
                type="button"
                onClick={handleExportBrief}
                disabled={isExporting}
                className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-stone-900 hover:bg-stone-800 text-stone-50 text-xs font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm group"
                title="Export Lawyer Brief (Ctrl+P / ⌘P)"
              >
                {downloadSuccess ? (
                  <>
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                    <span className="hidden sm:inline">Downloaded</span>
                  </>
                ) : (
                  <>
                    <Download className={`h-3.5 w-3.5 ${isExporting ? 'animate-spin' : ''}`} />
                    <span className="hidden sm:inline">
                      {isExporting ? 'Exporting...' : 'Export Lawyer Brief'}
                    </span>
                    <span className="sm:hidden">Export</span>
                    <kbd className="hidden xl:inline-block px-1.5 py-0.5 text-[10px] font-mono font-medium rounded bg-stone-800 text-stone-300 border border-stone-700">
                      ⌘P
                    </kbd>
                  </>
                )}
              </button>
            </>
          )}
        </div>
      </div>
    </header>
  );
};
