import React from 'react';
import {
  Sparkles,
  Briefcase,
  Clock,
  ShieldAlert,
  Code,
  Key,
  Home,
  DollarSign,
  FileText,
} from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';

export interface ActionChipScenario {
  id: string;
  label: string;
  prompt: string;
  iconType: 'briefcase' | 'code' | 'clock' | 'shield' | 'key' | 'home' | 'dollar' | 'file';
}

export interface ActionChipsProps {
  onSelectScenario: (prompt: string) => void;
  isStreaming: boolean;
}

export const ActionChips: React.FC<ActionChipsProps> = ({ onSelectScenario, isStreaming }) => {
  const document = useAppStore((state) => state.document);

  // Determine which scenario set to show based on contract topic
  let currentScenarios: ActionChipScenario[] = [];

  const lowerName = document?.filename?.toLowerCase() || '';

  if (lowerName.includes('lease') || lowerName.includes('apartment') || lowerName.includes('tenan')) {
    currentScenarios = [
      {
        id: 'lease_entry',
        label: 'Can landlord enter unannounced?',
        prompt: 'Can the landlord enter my apartment without advance 24-hour notice under this lease?',
        iconType: 'home',
      },
      {
        id: 'lease_rent',
        label: 'What if rent increases 20%?',
        prompt: 'How does the automatic 20% rent escalation work upon expiration of the initial lease term?',
        iconType: 'dollar',
      },
      {
        id: 'lease_deposit',
        label: 'Security deposit deductions',
        prompt: 'Can the landlord deduct ordinary wear and tear from my security deposit upon move out?',
        iconType: 'shield',
      },
    ];
  } else if (lowerName.includes('nda') || lowerName.includes('confidential')) {
    currentScenarios = [
      {
        id: 'nda_lawyer',
        label: 'Can I share with my attorney?',
        prompt: 'Am I legally allowed to disclose this agreement or confidential items to my personal lawyer and accountant?',
        iconType: 'briefcase',
      },
      {
        id: 'nda_term',
        label: 'Does confidentiality expire in 2 years?',
        prompt: 'What happens to confidential trade secrets and general information after the 2-year survivability term?',
        iconType: 'clock',
      },
      {
        id: 'nda_subpoena',
        label: 'What if subpoenaed by court?',
        prompt: 'What are my obligations if confidential information is compelled by judicial subpoena or legal process?',
        iconType: 'shield',
      },
    ];
  } else {
    // Services or general commercial agreement
    currentScenarios = [
      {
        id: 'free_cancel',
        label: 'What if the client cancels midway?',
        prompt: 'What happens to my unpaid hours and completed work if the client cancels the contract midway?',
        iconType: 'briefcase',
      },
      {
        id: 'free_ip',
        label: 'Can I reuse my code?',
        prompt: 'Can I reuse my pre-existing code and libraries under the intellectual property assignment clause?',
        iconType: 'code',
      },
      {
        id: 'free_payment',
        label: 'Payment past 30 days',
        prompt: 'What are my remedies if the client delays payment past 30 days under the current payment terms?',
        iconType: 'dollar',
      },
    ];
  }

  const renderIcon = (type: ActionChipScenario['iconType']) => {
    switch (type) {
      case 'briefcase':
        return <Briefcase className="h-3.5 w-3.5 text-stone-400" />;
      case 'code':
        return <Code className="h-3.5 w-3.5 text-stone-400" />;
      case 'clock':
        return <Clock className="h-3.5 w-3.5 text-stone-400" />;
      case 'shield':
        return <ShieldAlert className="h-3.5 w-3.5 text-stone-400" />;
      case 'key':
        return <Key className="h-3.5 w-3.5 text-stone-400" />;
      case 'home':
        return <Home className="h-3.5 w-3.5 text-stone-400" />;
      case 'dollar':
        return <DollarSign className="h-3.5 w-3.5 text-stone-400" />;
      case 'file':
      default:
        return <FileText className="h-3.5 w-3.5 text-stone-400" />;
    }
  };

  return (
    <div className="w-full pb-1">
      <div className="flex items-center gap-1.5 mb-2 px-1 text-[11px] font-semibold text-stone-400">
        <Sparkles className="h-3 w-3 text-stone-400" />
        <span>Try a &ldquo;What-If&rdquo; scenario for this contract:</span>
      </div>
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        {currentScenarios.map((item) => (
          <button
            key={item.id}
            type="button"
            disabled={isStreaming}
            onClick={() => onSelectScenario(item.prompt)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-white border border-stone-200 text-stone-600 hover:bg-stone-50 hover:border-stone-300 hover:text-stone-800 whitespace-nowrap active:scale-95 transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-sm flex-shrink-0"
          >
            {renderIcon(item.iconType)}
            <span>{item.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
};
