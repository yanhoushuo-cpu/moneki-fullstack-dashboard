import { Bot, UserRound } from 'lucide-react';

interface ChatMessageProps {
  role: 'user' | 'assistant';
  children: React.ReactNode;
}

export function ChatMessage({ role, children }: ChatMessageProps) {
  return (
    <div className={`chat-message ${role}`}>
      <span className="chat-avatar" aria-hidden="true">
        {role === 'assistant' ? <Bot size={15} /> : <UserRound size={15} />}
      </span>
      <div className="chat-bubble">{children}</div>
    </div>
  );
}
