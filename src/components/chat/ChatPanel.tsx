import React, { useEffect, useRef, useCallback } from 'react';
import { MessageSquareText, Sparkles } from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';
import { sendChatMessage } from '../../services/api';
import { MessageItem } from './MessageItem';
import { ChatInput } from './ChatInput';
import { ActionChips } from './ActionChips';

export const ChatPanel: React.FC = () => {
  const chatBottomRef = useRef<HTMLDivElement>(null);
  const lastProcessedUserMsgIdRef = useRef<string | null>(null);

  const document = useAppStore((state) => state.document);
  const chatMessages = useAppStore((state) => state.chatMessages);
  const isStreaming = useAppStore((state) => state.isStreaming);
  const selectedClauseId = useAppStore((state) => state.selectedClauseId);
  const selectClause = useAppStore((state) => state.selectClause);
  const addUserMessage = useAppStore((state) => state.addUserMessage);
  const appendAssistantToken = useAppStore((state) => state.appendAssistantToken);
  const appendAssistantCitations = useAppStore((state) => state.appendAssistantCitations);
  const finalizeAssistantMessage = useAppStore((state) => state.finalizeAssistantMessage);
  const setStreaming = useAppStore((state) => state.setStreaming);

  const backendConnected = useAppStore((state) => state.backendConnected);
  const clauses = document?.clauses ?? [];
  const selectedClause = clauses.find((c) => c.id === selectedClauseId);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const handleTriggerAssistant = useCallback(async (promptText: string) => {
    if (!document) return;
    const assistantMsgId = `msg_asst_${Date.now()}`;
    setStreaming(true);
    try {
      // Pass conversational memory (prior 6 message turns excluding the current user message)
      const memoryTurns = chatMessages
        .slice(0, -1)
        .slice(-6)
        .map((m) => ({
          role: m.role,
          content: m.content,
        }));

      // Build comprehensive canonical contract context for the full active document
      const allClauses = document.clauses;
      const canonicalClauses = allClauses.map((c) => ({
        id: c.id,
        title: c.title,
        text: c.originalText,
        originalText: c.originalText,
        riskLevel: c.riskLevel,
        unfairnessScore: c.unfairnessScore,
        clauseKind: c.clauseKind,
        isRiskBearing: c.isRiskBearing,
        riskReasons: c.riskReasons,
        category: c.category,
        plainSummary: c.plainSummary,
        suggestion: c.suggestion,
        pageNumber: c.pageNumber,
      }));

      // Pass active document context so backend has complete canonical metadata even if RAG session expired
      const contractContext = {
        filename: document.filename,
        overallFairnessScore: document.overallFairnessScore,
        totalPages: document.totalPages,
        clauseIndex: allClauses.map((c) => ({
          id: c.id,
          title: c.title,
          riskLevel: c.riskLevel,
          pageNumber: c.pageNumber,
        })),
        clauses: canonicalClauses,
      };

      const finalMessage = await sendChatMessage(
        document.sessionId,
        promptText,
        (token) => appendAssistantToken(assistantMsgId, token),
        (citationIds) => appendAssistantCitations(assistantMsgId, citationIds),
        memoryTurns,
        selectedClauseId || undefined,
        contractContext
      );
      finalizeAssistantMessage({ ...finalMessage, id: assistantMsgId });
    } catch (err) {
      console.error('Failed to stream chat response:', err);
      appendAssistantToken(assistantMsgId, '\n\n[Communication interrupted. Please try again.]');
    } finally {
      setStreaming(false);
    }
  }, [document, chatMessages, selectedClauseId, appendAssistantToken, appendAssistantCitations, finalizeAssistantMessage, setStreaming]);

  useEffect(() => {
    if (!document || isStreaming) return;
    const lastMessage = chatMessages[chatMessages.length - 1];
    if (lastMessage && lastMessage.role === 'user' && lastMessage.id !== lastProcessedUserMsgIdRef.current) {
      lastProcessedUserMsgIdRef.current = lastMessage.id;
      handleTriggerAssistant(lastMessage.content);
    }
  }, [chatMessages, isStreaming, document, handleTriggerAssistant]);

  const handleSendMessage = (messageText: string) => {
    if (isStreaming) return;
    addUserMessage(messageText);
  };

  const handleSelectScenario = (scenarioPrompt: string) => {
    if (isStreaming) return;
    addUserMessage(scenarioPrompt);
  };

  return (
    <div className="flex-1 h-full min-h-0 flex flex-col overflow-hidden bg-white">
      {/* Tier 1: Header */}
      <div className="flex-shrink-0 px-5 py-3 border-b border-stone-200 bg-stone-50/40 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-lg bg-stone-900 text-white flex items-center justify-center shadow-xs">
            <MessageSquareText className="h-4 w-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-stone-900 tracking-tight">
              Legal Risk Copilot
            </h2>
            <p className="text-[11px] text-stone-500">
              Interactive what-if simulator &amp; counter-clause generator
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {selectedClause && (
            <div className="hidden xl:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-stone-100 text-stone-600 text-[11px] max-w-[170px] truncate border border-stone-200">
              <span className="text-stone-400 font-medium">Context:</span>
              <span className="truncate font-semibold">{selectedClause.title}</span>
            </div>
          )}

          <div
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold border ${
              backendConnected
                ? 'bg-emerald-50 text-emerald-800 border-emerald-200 shadow-2xs'
                : 'bg-stone-100 text-stone-700 border-stone-200'
            }`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                backendConnected ? 'bg-emerald-500 animate-pulse' : 'bg-stone-400'
              }`}
            />
            <span>{backendConnected ? 'Connected' : 'Offline'}</span>
          </div>
        </div>
      </div>

      {/* Tier 2: Messages Stream */}
      <div className="flex-1 min-h-0 overflow-y-auto p-5 space-y-4 bg-white">
        {chatMessages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-8">
            <div className="h-12 w-12 rounded-xl bg-stone-100 border border-stone-200 flex items-center justify-center mb-3">
              <Sparkles className="h-6 w-6 text-stone-400" />
            </div>
            <h3 className="text-sm font-semibold text-stone-700">Legal Risk Copilot Ready</h3>
            <p className="text-xs text-stone-400 mt-1 max-w-sm leading-relaxed">
              Ask about potential liabilities, termination risks, or simulate custom what-if scenarios.
            </p>
          </div>
        ) : (
          chatMessages.map((msg) => (
            <MessageItem key={msg.id} message={msg} onClauseClick={selectClause} />
          ))
        )}
        <div ref={chatBottomRef} />
      </div>

      {/* Tier 3: Input & Actions - Pinned to Bottom */}
      <div className="flex-shrink-0 border-t border-stone-200 bg-white p-4 space-y-3">
        <ActionChips onSelectScenario={handleSelectScenario} isStreaming={isStreaming} />
        <ChatInput onSend={handleSendMessage} isStreaming={isStreaming} />
      </div>
    </div>
  );
};
