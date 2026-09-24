import { create } from 'zustand';
import type { ContractDocument, RiskLevel } from '../types/contract';
import type { ChatMessage } from '../types/chat';
import {
  MOCK_PRESETS,
  type PresetKey,
  mockFreelanceDocument,
} from '../services/mockData';
import { checkBackendHealth } from '../services/api';

export interface AppState {
  // State
  document: ContractDocument | null;
  activePresetKey: PresetKey | 'custom' | null;
  selectedClauseId: string | null;
  activeRiskFilter: RiskLevel | 'ALL';
  chatMessages: ChatMessage[];
  isUploading: boolean;
  isStreaming: boolean;
  backendConnected: boolean | null;
  activeViewMode: 'PAGE' | 'CARD';

  // Actions
  setViewMode: (mode: 'PAGE' | 'CARD') => void;
  loadMockDocument: () => void;
  loadPreset: (key: PresetKey) => void;
  setDocument: (document: ContractDocument | null, presetKey?: PresetKey | 'custom' | null) => void;
  selectClause: (id: string | null) => void;
  setRiskFilter: (filter: RiskLevel | 'ALL') => void;
  addUserMessage: (content: string) => string; // Returns created message ID
  appendAssistantToken: (messageId: string, token: string) => void;
  appendAssistantCitations: (messageId: string, clauseIds: string[]) => void;
  finalizeAssistantMessage: (message: ChatMessage) => void;
  setUploading: (isUploading: boolean) => void;
  setStreaming: (isStreaming: boolean) => void;
  checkBackendStatus: () => Promise<void>;
  resetSession: () => void;
}

export function isRiskBearingClause(c: {
  isRiskBearing?: boolean;
  clauseKind?: string;
  riskLevel?: string;
}): boolean {
  if (c.isRiskBearing === false) return false;
  const kind = (c.clauseKind || '').toUpperCase();
  if (kind === 'DEFINITION' || kind === 'HEADING' || kind === 'RECITAL' || kind === 'BOILERPLATE') {
    return false;
  }
  if (c.riskLevel === 'NEUTRAL') return false;
  return c.isRiskBearing === true || c.riskLevel === 'HIGH' || c.riskLevel === 'MEDIUM';
}

function generateAuditGreeting(doc: ContractDocument): ChatMessage {
  const highRisks = doc.clauses.filter(
    (c) => c.riskLevel === 'HIGH' && isRiskBearingClause(c)
  );
  const mediumRisks = doc.clauses.filter(
    (c) => c.riskLevel === 'MEDIUM' && isRiskBearingClause(c)
  );

  let riskDescription = '';
  let triggeredIds: string[] = [];

  if (highRisks.length >= 2) {
    riskDescription = `Key high-risk areas include **"${highRisks[0].title}"** and **"${highRisks[1].title}"**.`;
    triggeredIds = highRisks.map((c) => c.id);
  } else if (highRisks.length === 1) {
    riskDescription = `A key high-risk area includes **"${highRisks[0].title}"**.`;
    triggeredIds = [highRisks[0].id];
  } else if (mediumRisks.length > 0) {
    const medTitles = mediumRisks.slice(0, 2).map((c) => `"${c.title}"`).join(' and ');
    riskDescription = `No critical high-risk traps were detected. Moderate risk provisions to review include **${medTitles}**.`;
    triggeredIds = mediumRisks.slice(0, 2).map((c) => c.id);
  } else {
    riskDescription = 'No critical high-risk traps were detected. The audited operative provisions appear standard and balanced.';
    triggeredIds = [];
  }

  return {
    id: `msg_audit_${Date.now()}`,
    role: 'assistant',
    content: `I have completed an audit of **${doc.filename}**.\n\n${riskDescription}\n\nYou can click any **Simulate Scenario** button on the left, pick a quick question below, or type your own what-if scenario to see how this agreement behaves under pressure.`,
    timestamp: new Date().toISOString(),
    triggeredClauseIds: triggeredIds,
  };
}

export const useAppStore = create<AppState>((set) => ({
  // Initial state
  document: null,
  activePresetKey: null,
  selectedClauseId: null,
  activeRiskFilter: 'ALL',
  activeViewMode: 'PAGE',
  chatMessages: [],
  isUploading: false,
  isStreaming: false,
  backendConnected: null,

  // Actions
  setViewMode: (mode) => set({ activeViewMode: mode }),
  loadMockDocument: () => {
    const greeting = generateAuditGreeting(mockFreelanceDocument);
    const firstRiskBearing =
      mockFreelanceDocument.clauses.find((c) => c.riskLevel === 'HIGH' && isRiskBearingClause(c))?.id ??
      mockFreelanceDocument.clauses.find((c) => isRiskBearingClause(c))?.id ??
      null;

    set({
      document: mockFreelanceDocument,
      activePresetKey: 'freelance',
      chatMessages: [greeting],
      selectedClauseId: firstRiskBearing,
      activeRiskFilter: 'ALL',
      isUploading: false,
      isStreaming: false,
    });
  },

  loadPreset: (key: PresetKey) => {
    const doc = MOCK_PRESETS[key];
    const greeting = generateAuditGreeting(doc);
    const firstRiskBearing =
      doc.clauses.find((c) => c.riskLevel === 'HIGH' && isRiskBearingClause(c))?.id ??
      doc.clauses.find((c) => c.riskLevel === 'MEDIUM' && isRiskBearingClause(c))?.id ??
      doc.clauses.find((c) => isRiskBearingClause(c))?.id ??
      null;

    set({
      document: doc,
      activePresetKey: key,
      chatMessages: [greeting],
      selectedClauseId: firstRiskBearing,
      activeRiskFilter: 'ALL',
      isUploading: false,
      isStreaming: false,
    });
  },

  setDocument: (document, presetKey = 'custom') => {
    if (!document) {
      set({
        document: null,
        activePresetKey: null,
        selectedClauseId: null,
        chatMessages: [],
        activeRiskFilter: 'ALL',
      });
      return;
    }

    // Select the first genuinely risk-bearing clause (HIGH first, then MEDIUM, then any risk-bearing)
    // If none are risk-bearing, selectedClauseId should be null
    const initialClauseId =
      document.clauses.find((c) => c.riskLevel === 'HIGH' && isRiskBearingClause(c))?.id ??
      document.clauses.find((c) => c.riskLevel === 'MEDIUM' && isRiskBearingClause(c))?.id ??
      document.clauses.find((c) => isRiskBearingClause(c))?.id ??
      null;

    const initialMessages: ChatMessage[] = [generateAuditGreeting(document)];

    set({
      document,
      activePresetKey: presetKey,
      selectedClauseId: initialClauseId,
      chatMessages: initialMessages,
      activeRiskFilter: 'ALL',
    });
  },

  selectClause: (id) => {
    set({ selectedClauseId: id });
  },

  setRiskFilter: (filter) => {
    set({ activeRiskFilter: filter });
  },

  addUserMessage: (content: string) => {
    const userMessageId = `msg_user_${Date.now()}`;
    const newMessage: ChatMessage = {
      id: userMessageId,
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };

    set((state) => ({
      chatMessages: [...state.chatMessages, newMessage],
    }));

    return userMessageId;
  },

  appendAssistantToken: (messageId: string, token: string) => {
    set((state) => {
      const existingIndex = state.chatMessages.findIndex((m) => m.id === messageId);
      if (existingIndex >= 0) {
        const updated = [...state.chatMessages];
        const target = updated[existingIndex];
        updated[existingIndex] = {
          ...target,
          content: target.content + token,
        };
        return { chatMessages: updated };
      }

      // If message does not exist yet, create a new streaming assistant message
      const newAssistantMsg: ChatMessage = {
        id: messageId,
        role: 'assistant',
        content: token,
        timestamp: new Date().toISOString(),
      };
      return { chatMessages: [...state.chatMessages, newAssistantMsg] };
    });
  },

  appendAssistantCitations: (messageId: string, clauseIds: string[]) => {
    set((state) => {
      const existingIndex = state.chatMessages.findIndex((m) => m.id === messageId);
      if (existingIndex >= 0) {
        const updated = [...state.chatMessages];
        const target = updated[existingIndex];
        const merged = Array.from(new Set([...(target.triggeredClauseIds || []), ...clauseIds]));
        updated[existingIndex] = {
          ...target,
          triggeredClauseIds: merged,
        };
        return { chatMessages: updated };
      }
      return state;
    });
  },

  finalizeAssistantMessage: (message: ChatMessage) => {
    set((state) => {
      const index = state.chatMessages.findIndex((m) => m.id === message.id);
      if (index >= 0) {
        const updated = [...state.chatMessages];
        updated[index] = message;
        return { chatMessages: updated };
      }
      return { chatMessages: [...state.chatMessages, message] };
    });
  },

  setUploading: (isUploading) => {
    set({ isUploading });
  },

  setStreaming: (isStreaming) => {
    set({ isStreaming });
  },

  checkBackendStatus: async () => {
    try {
      const health = await checkBackendHealth();
      set({ backendConnected: health.connected });
    } catch {
      set({ backendConnected: false });
    }
  },

  resetSession: () => {
    set({
      document: null,
      selectedClauseId: null,
      activeRiskFilter: 'ALL',
      chatMessages: [],
      isUploading: false,
      isStreaming: false,
    });
  },
}));
