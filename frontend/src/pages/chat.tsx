import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/router";
import Head from "next/head";
import { Send, Activity, Upload, FileText, BookOpen } from "lucide-react";
import toast from "react-hot-toast";

const API_URL =
  typeof window !== "undefined"
    ? ""   // browser uses relative URLs → goes through Next.js proxy (no CORS)
    : "https://rag-based-medical-question-answering.onrender.com"; // SSR direct

interface Source {
  document_id: string;
  filename: string;
  title?: string;
  excerpt: string;
  relevance_score: number;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  confidence?: number;
  isWarning?: boolean;
}

export default function ChatPage() {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const userMsg = input.trim();
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: userMsg }]);
    setLoading(true);

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 180000);

      const res = await fetch(`${API_URL}/api/v1/query/medical-query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: userMsg, top_k: 3, query_type: "general" }),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Server error ${res.status}`);
      }

      const data = await res.json();
      const isWarning = data.agent_used === "Medical Topic Filter";
      setMessages(prev => [...prev, {
        role: "assistant",
        content: data.answer,
        sources: data.sources,
        confidence: data.confidence_score,
        isWarning,
      }]);
    } catch (err: any) {
      const msg = err.name === "AbortError"
        ? "The model is taking too long. Try a shorter question."
        : err.message;
      toast.error(msg);
      setMessages(prev => [...prev, { role: "assistant", content: `⚠️ ${msg}` }]);
    } finally {
      setLoading(false);
      textareaRef.current?.focus();
    }
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <>
      <Head><title>MediRAG AI</title></Head>
      <div style={{ display: "flex", flexDirection: "column", height: "100vh", background: "#0d0f1a", fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" }}>

        {/* ── Header ── */}
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "14px 24px", background: "#111827",
          borderBottom: "1px solid #1f2937", flexShrink: 0,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div style={{
              width: "38px", height: "38px", borderRadius: "10px",
              background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <Activity size={20} color="white" />
            </div>
            <div>
              <div style={{ color: "#f9fafb", fontWeight: 700, fontSize: "16px", lineHeight: 1.2 }}>MediRAG AI</div>
              <div style={{ color: "#6b7280", fontSize: "12px" }}>Healthcare Knowledge Assistant</div>
            </div>
          </div>
          <button
            onClick={() => router.push("/upload")}
            style={{
              display: "flex", alignItems: "center", gap: "6px",
              padding: "8px 16px", background: "#1f2937",
              border: "1px solid #374151", borderRadius: "8px",
              color: "#9ca3af", cursor: "pointer", fontSize: "13px", fontWeight: 500,
            }}
          >
            <Upload size={14} /> Upload Docs
          </button>
        </div>

        {/* ── Messages ── */}
        <div style={{ flex: 1, overflowY: "auto", padding: "24px 16px", display: "flex", flexDirection: "column", gap: "20px" }}>
          {messages.length === 0 && (
            <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center", padding: "40px 0" }}>
              <div style={{
                width: "72px", height: "72px", borderRadius: "18px",
                background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
                display: "flex", alignItems: "center", justifyContent: "center", marginBottom: "20px",
              }}>
                <BookOpen size={36} color="white" />
              </div>
              <h2 style={{ color: "#f9fafb", fontSize: "22px", fontWeight: 700, margin: "0 0 10px" }}>
                Ask me anything
              </h2>
              <p style={{ color: "#6b7280", fontSize: "14px", maxWidth: "380px", lineHeight: 1.6, margin: 0 }}>
                I can answer medical questions, general queries, and anything in between. Upload documents to enrich my knowledge base.
              </p>
              <div style={{ display: "flex", gap: "10px", marginTop: "24px", flexWrap: "wrap", justifyContent: "center" }}>
                {["What is hypertension?", "Explain diabetes management", "What causes fever?"].map(q => (
                  <button
                    key={q}
                    onClick={() => { setInput(q); textareaRef.current?.focus(); }}
                    style={{
                      padding: "8px 14px", background: "#1f2937", border: "1px solid #374151",
                      borderRadius: "20px", color: "#9ca3af", cursor: "pointer", fontSize: "13px",
                    }}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} style={{ display: "flex", justifyContent: msg.role === "user" ? "flex-end" : "flex-start", gap: "10px", alignItems: "flex-start", maxWidth: "800px", margin: "0 auto", width: "100%" }}>
              {msg.role === "assistant" && (
                <div style={{
                  width: "32px", height: "32px", borderRadius: "8px", flexShrink: 0,
                  background: msg.isWarning
                    ? "linear-gradient(135deg, #f59e0b, #ef4444)"
                    : "linear-gradient(135deg, #3b82f6, #8b5cf6)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}>
                  {msg.isWarning
                    ? <span style={{ fontSize: "16px" }}>⚕️</span>
                    : <Activity size={16} color="white" />}
                </div>
              )}
              <div style={{ maxWidth: "85%" }}>
                <div style={{
                  padding: "12px 16px",
                  background: msg.role === "user"
                    ? "linear-gradient(135deg, #3b82f6, #8b5cf6)"
                    : msg.isWarning
                      ? "rgba(245,158,11,0.08)"
                      : "#1f2937",
                  border: msg.role === "assistant"
                    ? msg.isWarning
                      ? "1px solid rgba(245,158,11,0.4)"
                      : "1px solid #374151"
                    : "none",
                  borderRadius: msg.role === "user" ? "18px 18px 4px 18px" : "18px 18px 18px 4px",
                  color: msg.isWarning ? "#fbbf24" : "#f9fafb",
                  fontSize: "14px", lineHeight: "1.7",
                  whiteSpace: "pre-wrap", wordBreak: "break-word",
                }}>
                  {msg.content}
                </div>
                {msg.sources && msg.sources.length > 0 && (
                  <div style={{ marginTop: "6px", display: "flex", flexWrap: "wrap", gap: "6px" }}>
                    {msg.sources.map((s, j) => (
                      <div key={j} style={{
                        display: "flex", alignItems: "center", gap: "4px",
                        padding: "4px 10px", background: "#111827",
                        border: "1px solid #374151", borderRadius: "12px",
                        color: "#6b7280", fontSize: "11px",
                      }}>
                        <FileText size={10} />
                        {s.title || s.filename}
                        {s.relevance_score > 0 && <span style={{ color: "#4b5563" }}>· {(s.relevance_score * 100).toFixed(0)}%</span>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div style={{ display: "flex", alignItems: "flex-start", gap: "10px", maxWidth: "800px", margin: "0 auto", width: "100%" }}>
              <div style={{
                width: "32px", height: "32px", borderRadius: "8px", flexShrink: 0,
                background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
                display: "flex", alignItems: "center", justifyContent: "center",
              }}>
                <Activity size={16} color="white" />
              </div>
              <div style={{
                padding: "12px 16px", background: "#1f2937", border: "1px solid #374151",
                borderRadius: "18px 18px 18px 4px", color: "#6b7280", fontSize: "14px",
                display: "flex", alignItems: "center", gap: "8px",
              }}>
                <span style={{ display: "inline-flex", gap: "3px" }}>
                  {[0, 150, 300].map(d => (
                    <span key={d} style={{
                      width: "6px", height: "6px", borderRadius: "50%",
                      background: "#4b5563", display: "inline-block",
                      animation: "bounce 1.2s infinite",
                      animationDelay: `${d}ms`,
                    }} />
                  ))}
                </span>
                Thinking… (LLM on CPU, may take ~30s)
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* ── Input ── */}
        <div style={{
          padding: "16px 24px", background: "#111827",
          borderTop: "1px solid #1f2937", flexShrink: 0,
        }}>
          <div style={{
            display: "flex", gap: "10px", alignItems: "flex-end",
            maxWidth: "800px", margin: "0 auto",
          }}>
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Ask anything… (Enter to send, Shift+Enter for new line)"
              rows={2}
              style={{
                flex: 1, padding: "12px 16px", background: "#1f2937",
                border: "1px solid #374151", borderRadius: "12px",
                color: "#f9fafb", fontSize: "14px", resize: "none",
                outline: "none", lineHeight: "1.5", fontFamily: "inherit",
                transition: "border-color 0.2s",
              }}
              onFocus={e => e.target.style.borderColor = "#3b82f6"}
              onBlur={e => e.target.style.borderColor = "#374151"}
            />
            <button
              onClick={sendMessage}
              disabled={loading || !input.trim()}
              style={{
                padding: "12px 20px", flexShrink: 0,
                background: loading || !input.trim() ? "#1f2937" : "linear-gradient(135deg, #3b82f6, #8b5cf6)",
                border: loading || !input.trim() ? "1px solid #374151" : "none",
                borderRadius: "12px", color: loading || !input.trim() ? "#4b5563" : "white",
                cursor: loading || !input.trim() ? "not-allowed" : "pointer",
                display: "flex", alignItems: "center", gap: "6px",
                fontSize: "14px", fontWeight: 600, transition: "all 0.2s",
              }}
            >
              <Send size={16} />
              Send
            </button>
          </div>
          <div style={{ textAlign: "center", marginTop: "8px", color: "#374151", fontSize: "11px" }}>
            Educational use only · Not a substitute for professional medical advice
          </div>
        </div>
      </div>

      <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
          40% { transform: translateY(-6px); opacity: 1; }
        }
      `}</style>
    </>
  );
}
