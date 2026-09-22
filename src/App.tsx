import React, { useEffect, useState } from 'react';
import { Navbar } from './components/layout/Navbar';
import { SplitPane } from './components/layout/SplitPane';
import { LandingHero } from './components/common/LandingHero';
import { LawyerBriefModal } from './components/common/LawyerBriefModal';
import { UploadModal } from './components/common/UploadModal';
import { useAppStore } from './store/useAppStore';

export const App: React.FC = () => {
  const [isBriefModalOpen, setIsBriefModalOpen] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [uploadModalTab, setUploadModalTab] = useState<'presets' | 'upload'>('upload');
  const document = useAppStore((state) => state.document);

  const handleOpenUpload = (tab: 'presets' | 'upload' = 'upload') => {
    setUploadModalTab(tab);
    setIsUploadModalOpen(true);
  };

  // Global Keyboard Shortcuts (Cmd+K / Ctrl+K & Cmd+P / Ctrl+P)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setUploadModalTab('upload');
        setIsUploadModalOpen((prev) => !prev);
      }

      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'p' && document) {
        e.preventDefault();
        setIsBriefModalOpen(true);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [document]);

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-[#FAF9F6]">
      <Navbar
        onOpenBriefModal={() => setIsBriefModalOpen(true)}
        onOpenUploadModal={() => handleOpenUpload('upload')}
      />
      <main className="flex-1 overflow-hidden">
        {document ? (
          <SplitPane onOpenUploadModal={() => handleOpenUpload('upload')} />
        ) : (
          <LandingHero />
        )}
      </main>
      <LawyerBriefModal
        isOpen={isBriefModalOpen}
        onClose={() => setIsBriefModalOpen(false)}
      />
      <UploadModal
        isOpen={isUploadModalOpen}
        initialTab={uploadModalTab}
        onClose={() => setIsUploadModalOpen(false)}
      />
    </div>
  );
};

export default App;
