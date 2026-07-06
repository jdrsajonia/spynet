import { useState, useRef, useEffect, useMemo } from "react";
import { call } from "../api";

// Sugerencias rápidas que el usuario puede clickear para preguntar.
const SUGGESTIONS = [
  "Summarize this analysis",
  "What technologies does this site use?",
  "How secure is this site?",
  "Where is this site hosted?",
  "Is the SSL certificate valid?",
];

// ── Mini-renderer Markdown (sin dependencias) ────────────────────────────────
// Renderiza HTML estándar (<p>, <ul>, <ol>, <li>, <h2>-<h5>, <pre>, <code>)
function MiniMarkdown({ text }) {
  const html = useMemo(() => renderMarkdown(text || ""), [text]);
  return <div className="ai-md" dangerouslySetInnerHTML={{ __html: html }} />;
}

function renderMarkdown(text) {
  if (!text) return "";

  // Escapar HTML básico excepto lo que nosotros generemos
  const lines = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .split("\n");

  let html = "";
  let inUl = false;
  let inOl = false;
  let inLi = false;
  let inPre = false;
  let inP = false;
  let preContent = [];

  function closeLi() {
    if (inLi) { html += "</li>\n"; inLi = false; }
  }
  function closeLists() {
    closeLi();
    if (inUl) { html += "</ul>\n"; inUl = false; }
    if (inOl) { html += "</ol>\n"; inOl = false; }
  }
  function closeP() {
    if (inP) { html += "</p>\n"; inP = false; }
  }
  function closeAll() {
    closeP();
    closeLists();
  }

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const trimmed = rawLine.trim();

    // 1. Code blocks (```)
    if (trimmed.startsWith("```")) {
      if (inPre) {
        html += `<pre><code>${preContent.join("\n")}</code></pre>\n`;
        inPre = false;
        preContent = [];
      } else {
        closeAll();
        inPre = true;
      }
      continue;
    }
    if (inPre) {
      preContent.push(rawLine);
      continue;
    }

    // 2. Blank lines
    if (!trimmed) {
      closeAll();
      continue;
    }

    // 3. Headers (#, ##, ###, ####)
    const hMatch = trimmed.match(/^(#{1,4})\s+(.+)$/);
    if (hMatch) {
      closeAll();
      const level = Math.min(hMatch[1].length + 1, 5); // # -> h2, ## -> h3, ### -> h4, #### -> h5
      html += `<h${level}>${formatInline(hMatch[2])}</h${level}>\n`;
      continue;
    }

    // 4. Unordered list (- , * , • )
    const ulMatch = trimmed.match(/^[•\-\*]\s+(.+)$/);
    if (ulMatch) {
      closeP();
      if (inOl) { closeLi(); html += "</ol>\n"; inOl = false; }
      if (!inUl) { html += "<ul>\n"; inUl = true; }
      else { closeLi(); }
      html += `<li>${formatInline(ulMatch[1])}`;
      inLi = true;
      continue;
    }

    // 5. Ordered list (1. , 2. )
    const olMatch = trimmed.match(/^(\d+)\.\s+(.+)$/);
    if (olMatch) {
      closeP();
      if (inUl) { closeLi(); html += "</ul>\n"; inUl = false; }
      if (!inOl) { html += "<ol>\n"; inOl = true; }
      else { closeLi(); }
      html += `<li>${formatInline(olMatch[2])}`;
      inLi = true;
      continue;
    }

    // 6. Continuation of list item (indented line after bullet)
    if ((inUl || inOl) && inLi && (rawLine.startsWith("  ") || rawLine.startsWith("\t"))) {
      html += `<br>${formatInline(trimmed)}`;
      continue;
    }

    // 7. Normal paragraph line
    closeLists();
    if (!inP) {
      html += `<p>${formatInline(trimmed)}`;
      inP = true;
    } else {
      html += `<br>${formatInline(trimmed)}`;
    }
  }

  closeAll();
  if (inPre) {
    html += `<pre><code>${preContent.join("\n")}</code></pre>\n`;
  }

  return html;
}

function formatInline(str) {
  return str
    // Bold: **text** or __text__
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/__(.+?)__/g, "<strong>$1</strong>")
    // Italic: *text* or _text_
    .replace(/(?<!\w)\*([^*\n]+?)\*(?!\w)/g, "<em>$1</em>")
    .replace(/(?<!\w)_([^_\n]+?)_(?!\w)/g, "<em>$1</em>")
    // Inline code: `text`
    .replace(/`([^`\n]+?)`/g, "<code>$1</code>");
}

// ── Componente principal ─────────────────────────────────────────────────────

export default function AiChatPanel({ analysis }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const scrollRef = useRef(null);
  const prevIdRef = useRef(null);

  // Resetear el chat cuando cambia el análisis (nueva URL).
  useEffect(() => {
    const id = analysis?.id ?? analysis?.url;
    if (id && id !== prevIdRef.current) {
      prevIdRef.current = id;
      setMessages([]);
      setInput("");
      setError(null);
    }
  }, [analysis?.id, analysis?.url]);

  // Auto-scroll al final del chat cuando llega un mensaje nuevo.
  useEffect(() => {
    const el = scrollRef.current;
    if (el) {
      // Usar requestAnimationFrame para esperar a que el DOM se pinte
      requestAnimationFrame(() => {
        el.scrollTop = el.scrollHeight;
      });
    }
  }, [messages, loading]);

  if (!analysis) return null;

  // Construir el historial de la conversación para enviar al backend.
  function buildHistory() {
    return messages.map((m) => ({ role: m.role, content: m.content }));
  }

  async function send(question) {
    const q = (question || input).trim();
    if (!q || loading) return;

    setInput("");
    setError(null);

    const userMsg = { role: "user", content: q };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const history = buildHistory();
      const { status, body } = await call("/ai-analyses/", {
        method: "POST",
        body: JSON.stringify({ question: q, analysis, history }),
      });

      if (body?.success && body.data?.answer) {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: body.data.answer,
            provider: body.data.provider,
          },
        ]);
      } else {
        const errMsg = body?.error?.message || `Error ${status}`;
        setError(errMsg);
      }
    } catch {
      setError("Could not connect to the backend.");
    } finally {
      setLoading(false);
    }
  }

  function handleKey(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  // Provider display helpers
  function providerLabel(provider) {
    if (provider === "gemini") return "Gemini";
    if (provider === "local-fallback") return "Local";
    if (provider === "local") return "Local";
    return provider || "";
  }

  function isLocalProvider(provider) {
    return provider === "local" || provider === "local-fallback";
  }

  return (
    <article className="card ai-chat" id="ai-chat-panel">
      <h3 className="ai-chat__title">
        <span className="ai-chat__icon">✦</span> AI Assistant
      </h3>

      {/* Sugerencias rápidas (solo si no hay mensajes) */}
      {messages.length === 0 && (
        <div className="ai-chat__welcome">
          <p className="ai-chat__welcome-text">
            Ask anything about the analysis of <strong>{analysis.domain || analysis.url}</strong>
          </p>
          <div className="ai-chat__suggestions">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                className="ai-chat__chip"
                onClick={() => send(s)}
                disabled={loading}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Mensajes */}
      <div className="ai-chat__messages" ref={scrollRef}>
        {messages.map((m, i) => (
          <div
            key={i}
            className={`ai-chat__msg ai-chat__msg--${m.role}`}
          >
            <div className="ai-chat__msg-label">
              {m.role === "user" ? "You" : "AI Assistant"}
              {m.provider && m.role === "assistant" && (
                <span className={`ai-chat__provider${m.provider === "gemini" ? " ai-chat__provider--gemini" : ""}`}>
                  {providerLabel(m.provider)}
                </span>
              )}
            </div>
            <div className="ai-chat__msg-text">
              {m.role === "assistant" ? (
                <MiniMarkdown text={m.content} />
              ) : (
                m.content
              )}
            </div>
            {/* Aviso discreto cuando no hay IA externa */}
            {m.role === "assistant" && isLocalProvider(m.provider) && (
              <div className="ai-chat__local-notice">
                Generated without an external AI configured.
              </div>
            )}
          </div>
        ))}

        {/* Indicador de carga */}
        {loading && (
          <div className="ai-chat__msg ai-chat__msg--assistant">
            <div className="ai-chat__msg-label">AI Assistant</div>
            <div className="ai-chat__loading">
              <span className="ai-chat__loading-text">Analyzing the context</span>
              <span className="ai-chat__dot" />
              <span className="ai-chat__dot" />
              <span className="ai-chat__dot" />
            </div>
          </div>
        )}
      </div>

      {/* Error inline */}
      {error && <div className="ai-chat__error">{error}</div>}

      {/* Input */}
      <div className="ai-chat__input-row">
        <input
          className="ai-chat__input"
          type="text"
          placeholder="Ask about this analysis..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
          disabled={loading}
          id="ai-chat-input"
        />
        <button
          className="ai-chat__send"
          onClick={() => send()}
          disabled={!input.trim() || loading}
          id="ai-chat-send"
        >
          {loading ? "..." : "Send"}
        </button>
      </div>
    </article>
  );
}
