import React, { useState, useRef, useEffect } from 'react';
import { ragApi } from '../lib/api';
import './ChatRAG.css';

interface Source {
  document: string;
  full_text?: string;
  metadata: {
    filename?: string;
    mittente?: string;
    data?: string;
    data_ricezione?: string;
    categoria?: string;
    oggetto?: string;
    email_id?: string;
    similarity_score?: number;
  };
  distance?: number;
  similarity_score?: number;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  timestamp: Date;
  isGeneratedPrompt?: boolean;
  isAiResponse?: boolean;
}

interface RAGStats {
  total_documents: number;
  collection_name: string;
}

const ChatRAG: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showSources, setShowSources] = useState<{ [key: string]: boolean }>({});
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const [nResults, setNResults] = useState(5);
  const [useAiResponse, setUseAiResponse] = useState(true);
  const [useOpenAI, setUseOpenAI] = useState(false);
  const [stats, setStats] = useState<RAGStats | null>(null);
  const [filterCategoria, setFilterCategoria] = useState('');
  const [filterMittente, setFilterMittente] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadStats();
    setMessages([{
      id: 'welcome',
      role: 'assistant',
      content: 'Ciao! Sono l\'assistente SNALS. Posso cercare informazioni nei documenti indicizzati e rispondere alle tue domande. Come posso aiutarti?',
      timestamp: new Date()
    }]);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadStats = async () => {
    try {
      const response = await ragApi.getStatistics();
      setStats(response.data);
    } catch (err) {
      console.error('Error loading RAG stats:', err);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!inputValue.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    const questionText = inputValue.trim();
    setInputValue('');
    setIsLoading(true);
    setError(null);

    try {
      // Build filters
      const filters: any = {};
      if (filterCategoria) filters.filter_categoria = filterCategoria;
      if (filterMittente) filters.filter_mittente = filterMittente;

      if (useAiResponse) {
        // Call backend chat endpoint for AI-generated response
        const response = await ragApi.chat({
          query: questionText,
          n_results: nResults,
          use_openai: useOpenAI,
          ...filters
        });

        const chatResult = response.data;
        const sources: Source[] = (chatResult.sources || []).map((doc: any) => ({
          document: doc.document || doc.text || '',
          full_text: doc.full_text || doc.document || '',
          metadata: doc.metadata || {},
          similarity_score: doc.similarity_score || 0
        }));

        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: chatResult.answer || 'Nessuna risposta generata.',
          sources: sources,
          timestamp: new Date(),
          isAiResponse: true
        };

        setMessages(prev => [...prev, assistantMessage]);
      } else {
        // Query RAG for documents only (no AI response)
        const response = await ragApi.query({
          query: questionText,
          n_results: nResults,
          ...filters
        });

        const ragResults = response.data;
        const sources: Source[] = (ragResults.documents || []).map((doc: any) => ({
          document: doc.full_text || doc.document || doc.text || '',
          full_text: doc.full_text || '',
          metadata: doc.metadata || {},
          similarity_score: doc.similarity_score || 0
        }));

        // Generate prompt with RAG data
        const getDocumentName = (source: Source): string => {
          if (source.metadata.filename) return source.metadata.filename;
          if (source.metadata.oggetto) return source.metadata.oggetto;
          if (source.metadata.email_id) return `Email #${source.metadata.email_id}`;
          return 'Documento senza nome';
        };

        let contextSection = '';
        if (sources.length > 0) {
          contextSection = `\n\n--- DOCUMENTI RILEVANTI DALLA KNOWLEDGE BASE ---\n\n`;
          sources.forEach((source) => {
            const docName = getDocumentName(source);
            const relevance = source.similarity_score ? `(${(source.similarity_score * 100).toFixed(0)}% rilevanza)` : '';
            contextSection += `[${docName}] ${relevance}\n`;
            if (source.metadata.oggetto && source.metadata.filename) {
              contextSection += `Oggetto: ${source.metadata.oggetto}\n`;
            }
            if (source.metadata.mittente) {
              contextSection += `Mittente: ${source.metadata.mittente}\n`;
            }
            if (source.metadata.data_ricezione) {
              contextSection += `Data: ${new Date(source.metadata.data_ricezione).toLocaleDateString('it-IT')}\n`;
            }
            if (source.metadata.categoria) {
              contextSection += `Categoria: ${source.metadata.categoria}\n`;
            }
            contextSection += `Contenuto:\n${source.document}\n`;
            contextSection += `---\n\n`;
          });
        } else {
          contextSection = '\n\n[Nessun documento rilevante trovato nella knowledge base]\n\n';
        }

        const generatedPrompt = `Sei un assistente AI per il sindacato SNALS (Sindacato Nazionale Autonomo Lavoratori Scuola).

DOMANDA DELL'UTENTE:
"${questionText}"
${contextSection}
ISTRUZIONI:
Basandoti ESCLUSIVAMENTE sui documenti forniti sopra, rispondi alla domanda dell'utente in modo chiaro e professionale.
- Se i documenti contengono informazioni rilevanti, cita le fonti specifiche
- Se i documenti non contengono informazioni sufficienti, indicalo chiaramente
- Non inventare informazioni non presenti nei documenti
- Formatta la risposta in modo leggibile

RISPOSTA:`;

        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: generatedPrompt,
          sources: sources,
          timestamp: new Date(),
          isGeneratedPrompt: true
        };

        setMessages(prev => [...prev, assistantMessage]);
      }
    } catch (err: any) {
      console.error('Error querying RAG:', err);
      const errorDetail = err.response?.data?.detail || err.message || 'Errore durante la ricerca nei documenti';
      setError(errorDetail);

      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Mi dispiace, si è verificato un errore: ${errorDetail}`,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const toggleSources = (messageId: string) => {
    setShowSources(prev => ({
      ...prev,
      [messageId]: !prev[messageId]
    }));
  };

  const copyToClipboard = async (text: string, messageId: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedMessageId(messageId);
      setTimeout(() => setCopiedMessageId(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
      setError('Errore durante la copia');
    }
  };

  const clearChat = () => {
    setMessages([{
      id: 'welcome',
      role: 'assistant',
      content: 'Chat resettata. Come posso aiutarti?',
      timestamp: new Date()
    }]);
    setError(null);
  };

  return (
    <div className="chat-rag-container">
      <div className="chat-header">
        <h1>💬 Chat con Knowledge Base SNALS</h1>
        <p className="chat-subtitle">
          {stats ? `${stats.total_documents} documenti indicizzati` : 'Caricamento...'}
        </p>
        <div className="chat-controls">
          {/* Mode Toggle */}
          <div className="mode-toggle">
            <label className="toggle-label">
              <input
                type="checkbox"
                checked={useAiResponse}
                onChange={(e) => setUseAiResponse(e.target.checked)}
              />
              <span className="toggle-text">
                {useAiResponse ? '🤖 Risposta AI' : '📋 Solo Prompt'}
              </span>
            </label>
          </div>

          {/* OpenAI Toggle (only visible when AI response is enabled) */}
          {useAiResponse && (
            <div className="mode-toggle">
              <label className="toggle-label">
                <input
                  type="checkbox"
                  checked={useOpenAI}
                  onChange={(e) => setUseOpenAI(e.target.checked)}
                />
                <span className="toggle-text">
                  {useOpenAI ? '🌐 OpenAI' : '🏠 Locale (Ollama)'}
                </span>
              </label>
            </div>
          )}

          <label className="results-control">
            <span>Documenti:</span>
            <select value={nResults} onChange={(e) => setNResults(parseInt(e.target.value))}>
              <option value={3}>3</option>
              <option value={5}>5</option>
              <option value={10}>10</option>
              <option value={15}>15</option>
            </select>
          </label>

          <button
            className="filter-toggle-button"
            onClick={() => setShowFilters(!showFilters)}
          >
            🔍 Filtri {showFilters ? '▲' : '▼'}
          </button>

          <button className="clear-chat-button" onClick={clearChat}>
            🗑️ Nuova Chat
          </button>
        </div>

        {/* Filters Panel */}
        {showFilters && (
          <div className="filters-panel">
            <div className="filter-group">
              <label>Categoria:</label>
              <select value={filterCategoria} onChange={(e) => setFilterCategoria(e.target.value)}>
                <option value="">Tutte</option>
                <option value="interpello">Interpello</option>
                <option value="comunicazione_ust_usr">Comunicazione UST/USR</option>
                <option value="convocazione_riunione">Convocazione Riunione</option>
                <option value="richiesta_assistenza">Richiesta Assistenza</option>
                <option value="informativa_sindacale">Informativa Sindacale</option>
              </select>
            </div>
            <div className="filter-group">
              <label>Mittente contiene:</label>
              <input
                type="text"
                placeholder="es: info@snals.it"
                value={filterMittente}
                onChange={(e) => setFilterMittente(e.target.value)}
              />
            </div>
          </div>
        )}
      </div>

      <div className="chat-messages">
        {messages.map((message) => (
          <div key={message.id} className={`message message-${message.role}`}>
            <div className="message-avatar">
              {message.role === 'user' ? '👤' : message.isAiResponse ? (useOpenAI ? '🌐' : '🤖') : '📋'}
            </div>
            <div className="message-content-wrapper">
              <div className="message-content">
                {message.isGeneratedPrompt ? (
                  <pre className="message-text prompt-text">{message.content}</pre>
                ) : (
                  <div className="message-text ai-response">{message.content}</div>
                )}
              </div>

              {message.role === 'assistant' && message.id !== 'welcome' && (
                <div className="message-actions">
                  <button
                    className="copy-button"
                    onClick={() => copyToClipboard(message.content, message.id)}
                    title={message.isGeneratedPrompt ? 'Copia prompt' : 'Copia risposta'}
                  >
                    {copiedMessageId === message.id ? '✅ Copiato!' : '📋 Copia'}
                  </button>
                  {message.isAiResponse && (
                    <span className="response-badge">
                      {useOpenAI ? 'OpenAI' : 'Ollama'}
                    </span>
                  )}
                </div>
              )}

              {message.sources && message.sources.length > 0 && (
                <div className="message-sources">
                  <button
                    className="sources-toggle"
                    onClick={() => toggleSources(message.id)}
                  >
                    📚 {message.sources.length} {message.sources.length === 1 ? 'documento' : 'documenti'}
                    {showSources[message.id] ? ' ▼' : ' ▶'}
                  </button>

                  {showSources[message.id] && (
                    <div className="sources-list">
                      {message.sources.map((source, idx) => {
                        const docName = source.metadata.filename
                          || source.metadata.oggetto
                          || (source.metadata.email_id ? `Email #${source.metadata.email_id}` : `Documento ${idx + 1}`);

                        const relevance = source.similarity_score
                          ? (source.similarity_score * 100).toFixed(0)
                          : source.distance
                            ? ((1 - source.distance) * 100).toFixed(0)
                            : null;

                        return (
                          <div key={idx} className="source-item">
                            <div className="source-header">
                              <strong>📄 {docName}</strong>
                              {relevance && (
                                <span className="source-relevance">
                                  Rilevanza: {relevance}%
                                </span>
                              )}
                            </div>
                            <div className="source-metadata">
                              {source.metadata.oggetto && source.metadata.filename && (
                                <span className="metadata-item">📝 {source.metadata.oggetto}</span>
                              )}
                              {source.metadata.mittente && (
                                <span className="metadata-item">✉️ {source.metadata.mittente}</span>
                              )}
                              {(source.metadata.data || source.metadata.data_ricezione) && (
                                <span className="metadata-item">
                                  📅 {new Date(source.metadata.data || source.metadata.data_ricezione || '').toLocaleDateString('it-IT')}
                                </span>
                              )}
                              {source.metadata.categoria && (
                                <span className="metadata-item">🏷️ {source.metadata.categoria}</span>
                              )}
                            </div>
                            <div className="source-text">
                              {(source.full_text || source.document || '').substring(0, 500)}
                              {(source.full_text || source.document || '').length > 500 && '...'}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              <div className="message-timestamp">
                {message.timestamp.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })}
              </div>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="message message-assistant">
            <div className="message-avatar">{useAiResponse ? '🤖' : '🔍'}</div>
            <div className="message-content-wrapper">
              <div className="message-content loading">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
                <span className="loading-text">
                  {useAiResponse ? 'Genero risposta...' : 'Ricerca documenti...'}
                </span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {error && (
        <div className="chat-error">
          ⚠️ {error}
        </div>
      )}

      <form className="chat-input-form" onSubmit={handleSendMessage}>
        <input
          ref={inputRef}
          type="text"
          className="chat-input"
          placeholder="Fai una domanda sui documenti..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          disabled={isLoading}
        />
        <button
          type="submit"
          className="chat-send-button"
          disabled={isLoading || !inputValue.trim()}
        >
          {isLoading ? '⏳' : useAiResponse ? '🤖' : '🔍'} {useAiResponse ? 'Chiedi' : 'Cerca'}
        </button>
      </form>

      <div className="chat-info">
        <p>💡 <strong>Modalità:</strong> {useAiResponse
          ? `Risposta AI (${useOpenAI ? 'OpenAI GPT-4' : 'Ollama locale'}) - La tua domanda viene elaborata dall'AI usando i documenti trovati.`
          : 'Solo prompt - Genera un prompt con i documenti trovati da copiare e usare con un LLM esterno.'
        }</p>
      </div>
    </div>
  );
};

export default ChatRAG;
