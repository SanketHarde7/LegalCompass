import React, { useRef, useState, useEffect } from 'react';
import {
  Compass,
  Upload,
  Download,
  Scale,
  FileText,
  CheckCircle2,
  ChevronDown,
  Check,
  Sparkles,
  Plus,
} from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';
import { exportConsultationBrief } from '../../services/api';
import { type PresetKey } from '../../services/mockData';

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
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const document = useAppStore((state) => state.document);
  const activePresetKey = useAppStore((state) => state.activePresetKey);
  const isUploading = useAppStore((state) => state.isUploading);
  const backendConnected = useAppStore((state) => state.backendConnected);
  const checkBackendStatus = useAppStore((state) => state.checkBackendStatus);
  const loadPreset = useAppStore((state) => state.loadPreset);

  // Check backend health on mount and periodically
  useEffect(() => {
    checkBackendStatus();
    const interval = setInterval(checkBackendStatus, 15000);
    return () => clearInterval(interval);
  }, [checkBackendStatus]);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    window.addEventListener('mousedown', handleClickOutside);
    return () => window.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelectPreset = (key: PresetKey) => {
    loadPreset(key);
    setIsDropdownOpen(false);
  };

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

          {/* Preset Selector Dropdown Pill (Visible ONLY when document !== null) */}
          {document && (
            <div className="relative" ref={dropdownRef}>
              <button
                type="button"
                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-stone-50 hover:bg-stone-100/80 border border-stone-200 text-xs text-stone-700 transition-all group"
              >
                <FileText className="h-3.5 w-3.5 text-stone-400 group-hover:text-stone-600 flex-shrink-0" />
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

                <ChevronDown
                  className={`h-3.5 w-3.5 text-stone-400 transition-transform ${
                    isDropdownOpen ? 'rotate-180 text-stone-700' : ''
                  }`}
                />
              </button>

            {/* Dropdown Menu */}
            {isDropdownOpen && (
              <div className="absolute top-full left-0 mt-1.5 w-80 bg-white rounded-xl shadow-xl border border-stone-200 py-1.5 z-50 animate-in fade-in slide-in-from-top-1 duration-150">
                <div className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-stone-400 flex items-center justify-between">
                  <span>Demo Contract Presets</span>
                  <Sparkles className="h-3 w-3 text-stone-400" />
                </div>

                {/* Preset 1 */}
                <button
                  type="button"
                  onClick={() => handleSelectPreset('freelance')}
                  className="w-full text-left px-3 py-2 text-xs hover:bg-stone-50 flex items-center justify-between transition-colors group"
                >
                  <div className="min-w-0 pr-2">
                    <div className="font-medium text-stone-800 group-hover:text-stone-900 truncate">
                      Freelance Master Services Agreement
                    </div>
                    <div className="text-[11px] text-stone-400 truncate">
                      Sample_Freelance_Master_Services_Agreement.pdf
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
                      42/100
                    </span>
                    {(activePresetKey === 'freelance' || (!activePresetKey && document?.sessionId.includes('freelance'))) && (
                      <Check className="h-3.5 w-3.5 text-stone-900" />
                    )}
                  </div>
                </button>

                {/* Preset 2 */}
                <button
                  type="button"
                  onClick={() => handleSelectPreset('lease')}
                  className="w-full text-left px-3 py-2 text-xs hover:bg-stone-50 flex items-center justify-between transition-colors group"
                >
                  <div className="min-w-0 pr-2">
                    <div className="font-medium text-stone-800 group-hover:text-stone-900 truncate">
                      Residential Apartment Lease
                    </div>
                    <div className="text-[11px] text-stone-400 truncate">
                      Metro_Apartment_Lease_2026.pdf
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                      55/100
                    </span>
                    {activePresetKey === 'lease' && (
                      <Check className="h-3.5 w-3.5 text-stone-900" />
                    )}
                  </div>
                </button>

                {/* Preset 3 */}
                <button
                  type="button"
                  onClick={() => handleSelectPreset('nda')}
                  className="w-full text-left px-3 py-2 text-xs hover:bg-stone-50 flex items-center justify-between transition-colors group"
                >
                  <div className="min-w-0 pr-2">
                    <div className="font-medium text-stone-800 group-hover:text-stone-900 truncate">
                      Mutual Standard NDA
                    </div>
                    <div className="text-[11px] text-stone-400 truncate">
                      Mutual_Standard_NDA_v3.pdf
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      89/100
                    </span>
                    {activePresetKey === 'nda' && (
                      <Check className="h-3.5 w-3.5 text-stone-900" />
                    )}
                  </div>
                </button>

                {/* Preset 4: Airtight Master Services Agreement */}
                <button
                  type="button"
                  onClick={() => handleSelectPreset('airtight')}
                  className="w-full text-left px-3 py-2 text-xs hover:bg-stone-50 flex items-center justify-between transition-colors group"
                >
                  <div className="min-w-0 pr-2">
                    <div className="font-medium text-stone-800 group-hover:text-stone-900 truncate">
                      Airtight Master Services Agreement
                    </div>
                    <div className="text-[11px] text-stone-400 truncate">
                      Airtight_Master_Services_Agreement.pdf (10 Pages)
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      100/100
                    </span>
                    {activePresetKey === 'airtight' && (
                      <Check className="h-3.5 w-3.5 text-stone-900" />
                    )}
                  </div>
                </button>

                <div className="my-1 border-t border-stone-100" />

                {/* Open Full Upload Modal */}
                <button
                  type="button"
                  onClick={() => {
                    setIsDropdownOpen(false);
                    onOpenUploadModal?.();
                  }}
                  className="w-full text-left px-3 py-2 text-xs text-stone-600 hover:bg-stone-50 hover:text-stone-900 flex items-center gap-2 transition-colors font-medium"
                >
                  <Plus className="h-3.5 w-3.5 text-stone-400" />
                  <span>Upload custom contract or view modal...</span>
                </button>
              </div>
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
                : 'FastAPI Backend: Offline (Using Local Presets)'
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
