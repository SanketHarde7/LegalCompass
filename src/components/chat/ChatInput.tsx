import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Sparkles } from 'lucide-react';

export interface ChatInputProps {
  onSend: (message: string) => void;
  isStreaming: boolean;
  placeholder?: string;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSend,
  isStreaming,
  placeholder = 'Ask a question or simulate a what-if scenario...',
}) => {
  const [text, setText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 140)}px`;
    }
  }, [text]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!text.trim() || isStreaming) return;
    onSend(text.trim());
    setText('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full relative">
      <div className="relative flex items-end gap-2 p-2 rounded-xl bg-white border border-stone-200 focus-within:border-stone-400 focus-within:ring-2 focus-within:ring-stone-300/30 shadow-sm transition-all">
        <textarea
          ref={textareaRef}
          rows={1}
          value={text}
          disabled={isStreaming}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isStreaming ? 'LegalCompass is evaluating the contract...' : placeholder}
          className="flex-1 max-h-36 bg-transparent border-0 resize-none px-3 py-1.5 text-sm text-stone-800 placeholder-stone-400 focus:outline-none focus:ring-0 leading-relaxed disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!text.trim() || isStreaming}
          className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-lg bg-stone-900 hover:bg-stone-800 text-stone-50 text-xs font-medium shadow-sm disabled:opacity-40 disabled:hover:bg-stone-900 disabled:cursor-not-allowed transition-all active:scale-95 flex-shrink-0"
        >
          {isStreaming ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              <span className="hidden sm:inline">Simulating...</span>
            </>
          ) : (
            <>
              <Sparkles className="h-3.5 w-3.5 opacity-70" />
              <span className="hidden sm:inline">Simulate What-If</span>
              <Send className="h-3.5 w-3.5" />
            </>
          )}
        </button>
      </div>
      <div className="flex items-center px-2 pt-1 text-[10px] text-stone-400">
        <span>
          <kbd className="px-1 py-0.5 rounded bg-stone-100 text-stone-500 font-mono border border-stone-200">Enter</kbd> to send, <kbd className="px-1 py-0.5 rounded bg-stone-100 text-stone-500 font-mono border border-stone-200">Shift+Enter</kbd> for newline
        </span>
      </div>
    </form>
  );
};
