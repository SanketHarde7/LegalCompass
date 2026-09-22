import React, { useState } from 'react';
import {
  FileText,
  MessageSquareText,
} from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';
import { DocumentPanel } from '../document/DocumentPanel';
import { ChatPanel } from '../chat/ChatPanel';

export interface SplitPaneProps {
  onOpenUploadModal?: () => void;
}

export const SplitPane: React.FC<SplitPaneProps> = () => {
  const [mobileTab, setMobileTab] = useState<'document' | 'chat'>('document');

  const document = useAppStore((state) => state.document);
  const chatMessages = useAppStore((state) => state.chatMessages);
  const clauses = document?.clauses ?? [];

  if (!document) return null;

  return (
    <div className="w-full h-[calc(100vh-3.5rem)] flex flex-col overflow-hidden bg-[#FAF9F6]">
      {/* Mobile Tab Controller (<1024px) */}
      <div className="lg:hidden flex items-center justify-around border-b border-stone-200 bg-white px-4 py-2 flex-shrink-0">
        <button
          type="button"
          onClick={() => setMobileTab('document')}
          className={`flex-1 py-2 text-xs font-semibold rounded-lg flex items-center justify-center gap-2 transition-colors ${
            mobileTab === 'document'
              ? 'bg-stone-900 text-white shadow-sm'
              : 'text-stone-500 hover:text-stone-700'
          }`}
        >
          <FileText className="h-4 w-4" />
          <span>Risks &amp; Clauses</span>
          {clauses.length > 0 && (
            <span
              className={`px-1.5 py-0.5 rounded-full text-[10px] ${
                mobileTab === 'document'
                  ? 'bg-stone-700 text-stone-200'
                  : 'bg-stone-100 text-stone-500'
              }`}
            >
              {clauses.length}
            </span>
          )}
        </button>

        <button
          type="button"
          onClick={() => setMobileTab('chat')}
          className={`flex-1 py-2 text-xs font-semibold rounded-lg flex items-center justify-center gap-2 transition-colors ${
            mobileTab === 'chat'
              ? 'bg-stone-900 text-white shadow-sm'
              : 'text-stone-500 hover:text-stone-700'
          }`}
        >
          <MessageSquareText className="h-4 w-4" />
          <span>Simulation Chat</span>
          {chatMessages.length > 0 && (
            <span
              className={`px-1.5 py-0.5 rounded-full text-[10px] ${
                mobileTab === 'chat'
                  ? 'bg-stone-700 text-stone-200'
                  : 'bg-stone-100 text-stone-500'
              }`}
            >
              {chatMessages.length}
            </span>
          )}
        </button>
      </div>

      {/* Rigid 2-Panel Split Container */}
      <div className="flex-1 min-h-0 flex flex-col lg:flex-row overflow-hidden">
        {/* LEFT: Document & Clause Intelligence (55%) */}
        <section
          className={`w-full lg:w-[55%] h-full flex flex-col min-h-0 border-r border-stone-200/80 overflow-hidden bg-[#FAF9F6] ${
            mobileTab === 'document' ? 'flex' : 'hidden lg:flex'
          }`}
        >
          <DocumentPanel />
        </section>

        {/* RIGHT: Scenario Copilot Chat (45%) */}
        <section
          className={`w-full lg:w-[45%] h-full flex flex-col min-h-0 bg-white overflow-hidden ${
            mobileTab === 'chat' ? 'flex' : 'hidden lg:flex'
          }`}
        >
          <ChatPanel />
        </section>
      </div>
    </div>
  );
};
