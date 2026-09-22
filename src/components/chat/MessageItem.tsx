import React from 'react';
import Markdown from 'react-markdown';
import { Sparkles, User, ExternalLink, Clock } from 'lucide-react';
import type { ChatMessage } from '../../types/chat';
import { useAppStore } from '../../store/useAppStore';
import { ScenarioCard } from './ScenarioCard';
import { CounterProposalBox } from './CounterProposalBox';

export interface MessageItemProps {
  message: ChatMessage;
  onClauseClick: (clauseId: string) => void;
}

export const MessageItem: React.FC<MessageItemProps> = ({ message, onClauseClick }) => {
  const isAssistant = message.role === 'assistant';
  const document = useAppStore((state) => state.document);
  const clauses = document?.clauses ?? [];

  const formatTime = (isoString: string) => {
    try {
      return new Date(isoString).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  const getClauseLabel = (clauseId: string) => {
    const found = clauses.find((c) => c.id === clauseId);
    return found ? found.title : clauseId.replace('_', ' ').toUpperCase();
  };

  return (
    <div className={`flex flex-col w-full ${isAssistant ? 'items-start' : 'items-end'}`}>
      <div
        className={`max-w-[92%] sm:max-w-[85%] rounded-2xl p-4 text-xs leading-relaxed ${
          isAssistant
            ? 'bg-white border border-stone-200/80 text-stone-700 rounded-tl-sm shadow-sm'
            : 'bg-stone-900 text-stone-50 rounded-tr-sm shadow-md'
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between gap-3 mb-2 pb-1.5 border-b border-stone-100 text-[10px] font-semibold uppercase tracking-wider">
          <div className="flex items-center gap-1.5">
            {isAssistant ? (
              <>
                <div className="h-5 w-5 rounded-full bg-stone-100 flex items-center justify-center">
                  <Sparkles className="h-3 w-3 text-stone-500" />
                </div>
                <span className="text-stone-500 font-bold">LegalCompass AI</span>
              </>
            ) : (
              <>
                <div className="h-5 w-5 rounded-full bg-stone-700 flex items-center justify-center">
                  <User className="h-3 w-3 text-stone-300" />
                </div>
                <span className="text-stone-300 font-bold">You</span>
              </>
            )}
          </div>
          <div className={`flex items-center gap-1 font-normal ${isAssistant ? 'text-stone-400' : 'text-stone-400'}`}>
            <Clock className="h-2.5 w-2.5" />
            <span>{formatTime(message.timestamp)}</span>
          </div>
        </div>

        {/* Message Body with Markdown */}
        <div className="prose-sm max-w-none">
          {isAssistant ? (
            <Markdown
              components={{
                h1: ({ children }) => <h1 className="text-base font-bold text-stone-900 mt-3 mb-1.5">{children}</h1>,
                h2: ({ children }) => <h2 className="text-sm font-bold text-stone-900 mt-3 mb-1.5">{children}</h2>,
                h3: ({ children }) => <h3 className="text-sm font-semibold text-stone-800 mt-2.5 mb-1">{children}</h3>,
                p: ({ children }) => <p className="text-xs text-stone-700 leading-relaxed mb-2">{children}</p>,
                strong: ({ children }) => <strong className="font-semibold text-stone-900">{children}</strong>,
                em: ({ children }) => <em className="italic text-stone-600">{children}</em>,
                ul: ({ children }) => <ul className="list-disc list-inside text-xs text-stone-700 space-y-0.5 ml-1 mb-2">{children}</ul>,
                ol: ({ children }) => <ol className="list-decimal list-inside text-xs text-stone-700 space-y-0.5 ml-1 mb-2">{children}</ol>,
                li: ({ children }) => <li className="text-xs text-stone-700 leading-relaxed">{children}</li>,
                blockquote: ({ children }) => (
                  <blockquote className="border-l-2 border-stone-300 pl-3 py-1 bg-stone-50/75 rounded-r text-xs text-stone-600 italic my-2">
                    {children}
                  </blockquote>
                ),
                code: ({ children }) => <code className="px-1 py-0.5 rounded bg-stone-100 text-stone-800 text-[11px] font-mono">{children}</code>,
              }}
            >
              {message.content}
            </Markdown>
          ) : (
            <p className="text-xs text-stone-100 leading-relaxed whitespace-pre-wrap">{message.content}</p>
          )}
        </div>

        {/* Cited Clauses */}
        {message.triggeredClauseIds && message.triggeredClauseIds.length > 0 && (
          <div className="mt-3 pt-2.5 border-t border-stone-100 flex flex-wrap items-center gap-1.5">
            <span className="text-[10px] font-bold text-stone-400 uppercase tracking-wide mr-1">
              Cited:
            </span>
            {message.triggeredClauseIds.map((cid) => (
              <button
                key={cid}
                type="button"
                onClick={() => onClauseClick(cid)}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-white hover:bg-stone-50 border border-stone-200 hover:border-stone-400 text-stone-700 text-[11px] font-medium transition-all active:scale-95 shadow-sm group"
              >
                <span className="truncate max-w-[200px]">{getClauseLabel(cid)}</span>
                <ExternalLink className="h-2.5 w-2.5 text-stone-400 opacity-60 group-hover:opacity-100 flex-shrink-0" />
              </button>
            ))}
          </div>
        )}

        {message.scenarioOutcome && <ScenarioCard outcome={message.scenarioOutcome} />}
        {message.counterProposal && <CounterProposalBox text={message.counterProposal} />}
      </div>
    </div>
  );
};
