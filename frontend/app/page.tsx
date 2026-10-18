"use client";
import { useEffect, useRef, useState } from "react";
import {
  Plus,
  ArrowUp,
  MessageSquare,
  FlaskConical,
  Terminal,
  Cpu,
} from "lucide-react";
type Thread = { id: string; title: string };
type Message = { role: string; text: string; provider: string };
async function api(path: string, options?: RequestInit) {
  const res = await fetch(`/api/cowork${path}`, options);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Request failed");
  return data;
}
export default function Chat() {
  const scroll = useRef<HTMLDivElement>(null);
  const [threads, setThreads] = useState<Thread[]>([]);
  const [active, setActive] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState("");
  const [provider, setProvider] = useState("ollama");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    if (scroll.current) scroll.current.scrollTop = scroll.current.scrollHeight;
  }, [messages, busy]);
  async function refresh() {
    const all = await api("/threads");
    setThreads(all);
    return all;
  }
  async function select(id: string) {
    setActive(id);
    setMessages(await api(`/threads/${id}`));
    setError("");
  }
  async function fresh() {
    const t = await api("/threads", { method: "POST" });
    await refresh();
    await select(t.id);
    return t.id;
  }
  useEffect(() => {
    refresh()
      .then((all) => {
        if (all.length) select(all[0].id);
      })
      .catch((e) => setError(e.message));
  }, []);
  async function choose(value: string) {
    setBusy(true);
    setError("");
    try {
      if (value !== "core")
        await api("/runtime", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ provider: value }),
        });
      setProvider(value);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Runtime unavailable");
    } finally {
      setBusy(false);
    }
  }
  async function send(value = text) {
    if (!value.trim() || busy) return;
    setBusy(true);
    setError("");
    setText("");
    try {
      const id = active || (await fresh());
      setMessages((old) => [...old, { role: "user", text: value, provider }]);
      await api(`/threads/${id}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: value, provider }),
      });
      setMessages(await api(`/threads/${id}`));
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
      setText(value);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="cowork-shell">
      <aside className="cowork-sidebar">
        <a href="/" className="cowork-brand">
          <span className="cowork-mark">N</span> NEXORA <small>LOCAL AI</small>
        </a>
        <button
          className="cowork-new"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try {
              await fresh();
            } catch (e) {
              setError(
                e instanceof Error
                  ? e.message
                  : "Could not create conversation",
              );
            } finally {
              setBusy(false);
            }
          }}
        >
          <Plus size={17} /> New conversation
        </button>
        <div className="cowork-section">YOUR CONVERSATIONS</div>
        <nav>
          {threads.map((t) => (
            <button
              key={t.id}
              disabled={busy}
              className={
                active === t.id ? "cowork-thread selected" : "cowork-thread"
              }
              onClick={() => select(t.id).catch((e) => setError(e.message))}
            >
              <MessageSquare size={15} />
              <span>{t.title}</span>
            </button>
          ))}
        </nav>
        <div className="cowork-bottom">
          <a href="/research">
            <FlaskConical size={16} /> Model research
          </a>
          <span>
            <Cpu size={15} /> CPU · local storage
          </span>
          <small>
            Chats are saved locally. They do not automatically train the model.
          </small>
        </div>
      </aside>
      <main className="cowork-main">
        <header className="cowork-header">
          <div>
            <strong>Workspace</strong>
            <span> / Conversation</span>
          </div>
          <select
            aria-label="Inference provider"
            value={provider}
            disabled={busy}
            onChange={(e) => choose(e.target.value)}
          >
            <option value="ollama">SmolLM2 · local reference</option>
            <option value="core">NEXORA Core · research</option>
            <option value="localai">LocalAI · optional service</option>
            <option value="fcc">FCC → Ollama · optional proxy</option>
          </select>
        </header>
        <div className="cowork-scroll" ref={scroll}>
          {!messages.length ? (
            <section className="cowork-welcome">
              <div className="cowork-orbit">
                <Terminal size={29} />
              </div>
              <span className="cowork-eyebrow">
                YOUR LOCAL RESEARCH WORKSPACE
              </span>
              <h1>What shall we work on?</h1>
              <p>
                Talk with a local model, explore open APIs, and create files in
                your cowork workspace.
              </p>
              <div className="cowork-cards">
                {[
                  ["Explore your workspace", "/files"],
                  ["Find public APIs", "/catalog weather"],
                  ["See available actions", "/help"],
                ].map(([label, cmd]) => (
                  <button key={cmd} disabled={busy} onClick={() => send(cmd)}>
                    <span>{label}</span>
                    <code>{cmd}</code>
                    <ArrowUp size={16} />
                  </button>
                ))}
              </div>
            </section>
          ) : (
            <div className="cowork-messages">
              {messages.map((m, i) => (
                <article key={i} className={`cowork-message ${m.role}`}>
                  <div className="cowork-message-label">
                    {m.role === "user"
                      ? "You"
                      : m.role === "error"
                        ? "Action failed"
                        : m.provider}
                  </div>
                  <pre>{m.text}</pre>
                </article>
              ))}
              {busy && (
                <p className="cowork-thinking" role="status">
                  Working locally…
                </p>
              )}
            </div>
          )}
        </div>
        <div className="cowork-composer-wrap">
          {error && (
            <p role="alert" className="cowork-error">
              {error}
            </p>
          )}
          <form
            className="cowork-composer"
            onSubmit={(e) => {
              e.preventDefault();
              send();
            }}
          >
            <textarea
              aria-label="Message"
              placeholder="Ask a question, or use /help for workspace actions"
              value={text}
              maxLength={4000}
              disabled={busy}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
            />
            <div>
              <span>Local conversation · isolated file tools</span>
              <button aria-label="Send message" disabled={busy || !text.trim()}>
                <ArrowUp size={20} />
              </button>
            </div>
          </form>
          <p className="cowork-disclaimer">
            Small research models can give incorrect replies. Core predicts
            text; capable instruction following has not been demonstrated.
          </p>
        </div>
      </main>
    </div>
  );
}
