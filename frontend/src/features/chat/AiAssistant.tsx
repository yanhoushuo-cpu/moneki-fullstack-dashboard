import { useEffect, useMemo, useRef, useState } from 'react';
import { ArrowUp, Bot, DatabaseZap, RotateCcw, Sparkles } from 'lucide-react';

import { api } from '../../api/client';
import type { ChatMessage as HistoryMessage, ChatResponse, DashboardAction } from '../../api/types';
import { ChatMessage } from './ChatMessage';
import { EvidenceCard } from './EvidenceCard';
import { SuggestionChips } from './SuggestionChips';

const STARTER_QUESTIONS = [
  '牛肉poke 六月卖了多少钱？',
  '五月呢？',
  '哪个品类的门店营业额最高？',
  '客单价最近是涨了还是跌了？',
  '这批数据有哪些质量问题？',
];

interface Exchange {
  question: string;
  response: ChatResponse;
}

interface AiAssistantProps {
  onApplyDashboardAction: (action: DashboardAction) => void;
}

export function AiAssistant({ onApplyDashboardAction }: AiAssistantProps) {
  const [input, setInput] = useState('');
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const [lastQuestion, setLastQuestion] = useState('');
  const [error, setError] = useState<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);
  const streamRef = useRef<HTMLDivElement | null>(null);

  const history = useMemo<HistoryMessage[]>(
    () => exchanges.flatMap((exchange) => [
      { role: 'user' as const, content: exchange.question },
      { role: 'assistant' as const, content: exchange.response.answer },
    ]).slice(-8),
    [exchanges],
  );

  useEffect(() => () => controllerRef.current?.abort(), []);
  useEffect(() => {
    if (streamRef.current) streamRef.current.scrollTop = streamRef.current.scrollHeight;
  }, [exchanges, pendingQuestion, error]);

  async function ask(questionValue: string) {
    const question = questionValue.trim();
    if (!question || pendingQuestion) return;

    const controller = new AbortController();
    controllerRef.current?.abort();
    controllerRef.current = controller;
    setInput('');
    setError(null);
    setLastQuestion(question);
    setPendingQuestion(question);

    try {
      const response = await api.ask(question, history, controller.signal);
      setExchanges((current) => [...current, { question, response }].slice(-4));
    } catch (requestError) {
      if (requestError instanceof DOMException && requestError.name === 'AbortError') return;
      setInput(question);
      setError('暂时无法完成分析，请检查服务连接后重试。');
    } finally {
      if (controllerRef.current === controller) setPendingQuestion(null);
    }
  }

  const latestSuggestions = exchanges.at(-1)?.response.suggestions ?? STARTER_QUESTIONS;

  return (
    <section className="panel assistant-panel" aria-labelledby="assistant-title">
      <header className="assistant-header">
        <div className="assistant-title-row">
          <span className="assistant-mark"><Sparkles size={17} /></span>
          <div><p className="section-kicker">VERIFIABLE AI</p><h2 id="assistant-title">经营问数助手</h2></div>
        </div>
        <span className="assistant-status"><i /> 已连接可信数据</span>
      </header>

      <div className="chat-stream" ref={streamRef} aria-live="polite">
        {exchanges.length === 0 && !pendingQuestion && (
          <div className="assistant-welcome">
            <Bot size={25} />
            <strong>用自然语言查经营数据</strong>
            <p>每个数字都来自白名单分析工具，并附带可展开的查询证据。</p>
          </div>
        )}
        {exchanges.map((exchange, exchangeIndex) => (
          <div className="exchange" key={`${exchange.question}-${exchangeIndex}`}>
            <ChatMessage role="user">{exchange.question}</ChatMessage>
            <ChatMessage role="assistant">
              <p>{exchange.response.answer}</p>
              <span className={`answer-badge ${exchange.response.status}`}>
                {exchange.response.status === 'answered' ? '已核验' : exchange.response.status === 'unsupported' ? '超出范围' : '服务降级'}
                {' · '}{exchange.response.mode === 'provider' ? '模型规划' : '本地规则'}
              </span>
              {exchange.response.evidence.length > 0 && (
                <details className="evidence-disclosure">
                  <summary>{exchange.response.evidence.length} 条可核验证据</summary>
                  <div className="evidence-list">
                    {exchange.response.evidence.map((item, index) => <EvidenceCard evidence={item} index={index} key={`${item.tool}-${index}`} />)}
                  </div>
                </details>
              )}
              {exchange.response.dashboard_action && (
                <button className="apply-dashboard-button" type="button" onClick={() => onApplyDashboardAction(exchange.response.dashboard_action!)}>
                  <DatabaseZap size={15} /> 应用到看板
                </button>
              )}
            </ChatMessage>
          </div>
        ))}
        {pendingQuestion && (
          <div className="exchange">
            <ChatMessage role="user">{pendingQuestion}</ChatMessage>
            <ChatMessage role="assistant"><span className="thinking-dots" aria-label="正在分析"><i /><i /><i /></span></ChatMessage>
          </div>
        )}
        {error && (
          <div className="chat-error" role="alert"><span>{error}</span><button type="button" onClick={() => ask(lastQuestion)}><RotateCcw size={14} /> 重试</button></div>
        )}
      </div>

      <div className="assistant-controls">
        <SuggestionChips suggestions={latestSuggestions.slice(0, 5)} disabled={Boolean(pendingQuestion)} onSelect={ask} />
        <form className="chat-composer" onSubmit={(event) => { event.preventDefault(); void ask(input); }}>
          <label className="sr-only" htmlFor="assistant-question">向 AI 提问</label>
          <textarea
            id="assistant-question"
            aria-label="向 AI 提问"
            rows={1}
            maxLength={500}
            placeholder="例如：哪家店本月增长最快？"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                void ask(input);
              }
            }}
          />
          <button type="submit" aria-label="发送问题" disabled={!input.trim() || Boolean(pendingQuestion)}><ArrowUp size={18} /></button>
        </form>
        <small className="assistant-note">AI 只负责理解问题，所有数字由确定性分析服务计算。</small>
      </div>
    </section>
  );
}
