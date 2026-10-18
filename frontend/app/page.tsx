"use client";
import { useEffect, useRef, useState } from "react";
import {
  Plus,
  ArrowUp,
  MessageSquare,
  FlaskConical,
  Terminal,
  Cpu,
  Sun,
  Moon,
  Copy,
  Check,
  Pencil,
  Square,
  Maximize2,
  X,
} from "lucide-react";

type Thread = { id: string; title: string };
type Message = { id: number; role: string; text: string; provider: string };
type Block =
  | { type: "text"; content: string }
  | { type: "code"; lang: string; content: string };
type Canvas = { title: string; lang: string; code: string };

async function api(path: string, options?: RequestInit) {
  const res = await fetch(`/api/cowork${path}`, options);
  if (res.status === 204) return null;
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Request failed");
  return data;
}

// Split a message into plain-text and fenced-code segments so code blocks
// can get their own copy/canvas actions instead of being flattened into
// one undifferentiated <pre>.
function parseBlocks(text: string): Block[] {
  const blocks: Block[] = [];
  const fence = /```(\w*)\n([\s\S]*?)```/g;
  let cursor = 0;
  let match: RegExpExecArray | null;
  while ((match = fence.exec(text))) {
    if (match.index > cursor) {
      blocks.push({ type: "text", content: text.slice(cursor, match.index) });
    }
    blocks.push({ type: "code", lang: match[1] || "text", content: match[2] });
    cursor = match.index + match[0].length;
  }
  if (cursor < text.length) {
    blocks.push({ type: "text", content: text.slice(cursor) });
  }
  return blocks.length ? blocks : [{ type: "text", content: text }];
}

function CopyButton({ value, label }: { value: string; label: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      className="cowork-icon-btn"
      aria-label={label}
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(value);
          setCopied(true);
          setTimeout(() => setCopied(false), 1600);
        } catch {
          /* clipboard unavailable (e.g. insecure context); nothing to show */
        }
      }}
    >
      {copied ? <Check size={13} /> : <Copy size={13} />}
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

export default function Chat() {
  const scroll = useRef<HTMLDivElement>(null);
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const controllerRef = useRef<AbortController | null>(null);
  const [threads, setThreads] = useState<Thread[]>([]);
  const [active, setActive] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState("");
  const [provider, setProvider] = useState("ollama");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [dark, setDark] = useState(true);
  const [canvas, setCanvas] = useState<Canvas | null>(null);
  useEffect(() => {
    setDark(localStorage.getItem("nexora-theme") !== "light");
  }, []);
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
    setNotice("");
    setText("");
    const controller = new AbortController();
    controllerRef.current = controller;
    try {
      const id = active || (await fresh());
      setMessages((old) => [
        ...old,
        { id: -1, role: "user", text: value, provider },
      ]);
      await api(`/threads/${id}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: value, provider }),
        signal: controller.signal,
      });
      setMessages(await api(`/threads/${id}`));
      await refresh();
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") {
        setNotice(
          "Stopped waiting. The local model may still finish this reply in the background; reopen the conversation to check.",
        );
        try {
          if (active) setMessages(await api(`/threads/${active}`));
        } catch {
          /* best-effort refresh only; the notice above already explains the state */
        }
      } else {
        setError(e instanceof Error ? e.message : "Request failed");
        setText(value);
      }
    } finally {
      setBusy(false);
      controllerRef.current = null;
    }
  }
  function stop() {
    controllerRef.current?.abort();
  }
  async function editMessage(m: Message) {
    if (busy || m.id < 0) return;
    setError("");
    try {
      await api(`/threads/${active}/messages/${m.id}`, { method: "DELETE" });
      setMessages(await api(`/threads/${active}`));
      setText(m.text);
      composerRef.current?.focus();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not edit that message");
    }
  }
  return (
    <div className={dark ? "cowork-shell" : "cowork-shell light"}>
      <aside className="cowork-sidebar">
        <div className="cowork-brand-row">
          <a href="/" className="cowork-brand">
            <span className="cowork-mark">N</span> NEXORA{" "}
            <small>LOCAL AI</small>
          </a>
          <button
            type="button"
            className="cowork-theme-toggle"
            aria-label="Toggle color theme"
            onClick={() => {
              setDark(!dark);
              localStorage.setItem("nexora-theme", dark ? "light" : "dark");
            }}
          >
            {dark ? <Sun size={15} /> : <Moon size={15} />}
          </button>
        </div>
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
              {messages.map((m) => (
                <article
                  key={m.id < 0 ? `pending-${m.text}` : m.id}
                  className={`cowork-message ${m.role}`}
                >
                  <div className="cowork-message-label">
                    <span>
                      {m.role === "user"
                        ? "You"
                        : m.role === "error"
                          ? "Action failed"
                          : m.provider}
                    </span>
                    <span className="cowork-message-actions">
                      {m.role === "user" && (
                        <button
                          type="button"
                          className="cowork-icon-btn"
                          aria-label="Edit and resend this message"
                          disabled={busy || m.id < 0}
                          onClick={() => editMessage(m)}
                        >
                          <Pencil size={13} /> Edit
                        </button>
                      )}
                      <CopyButton value={m.text} label="Copy message" />
                    </span>
                  </div>
                  {parseBlocks(m.text).map((block, bi) =>
                    block.type === "text" ? (
                      block.content.trim() && (
                        <pre key={bi}>{block.content.replace(/^\n+|\n+$/g, "")}</pre>
                      )
                    ) : (
                      <div className="cowork-code" key={bi}>
                        <div className="cowork-code-bar">
                          <span>{block.lang}</span>
                          <span className="cowork-code-actions">
                            <CopyButton value={block.content} label="Copy code" />
                            <button
                              type="button"
                              className="cowork-icon-btn"
                              aria-label="Open in canvas"
                              onClick={() =>
                                setCanvas({
                                  title: `${m.provider} · ${block.lang}`,
                                  lang: block.lang,
                                  code: block.content,
                                })
                              }
                            >
                              <Maximize2 size={13} /> Canvas
                            </button>
                          </span>
                        </div>
                        <pre>{block.content}</pre>
                      </div>
                    ),
                  )}
                </article>
              ))}
              {busy && (
                <p className="cowork-thinking" role="status">
                  Working locally…
                  <button
                    type="button"
                    className="cowork-stop-btn"
                    onClick={stop}
                  >
                    <Square size={11} /> Stop
                  </button>
                </p>
              )}
            </div>
          )}
        </div>
        <div className="cowork-composer-wrap">
          {notice && <p className="cowork-notice">{notice}</p>}
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
              ref={composerRef}
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
              {busy ? (
                <button
                  type="button"
                  aria-label="Stop generating"
                  className="cowork-stop"
                  onClick={stop}
                >
                  <Square size={14} />
                </button>
              ) : (
                <button aria-label="Send message" disabled={!text.trim()}>
                  <ArrowUp size={20} />
                </button>
              )}
            </div>
          </form>
          <p className="cowork-disclaimer">
            Small research models can give incorrect replies. Core predicts
            text; capable instruction following has not been demonstrated.
          </p>
        </div>
      </main>
      {canvas && (
        <div className="cowork-canvas-overlay" onClick={() => setCanvas(null)}>
          <aside
            className="cowork-canvas"
            onClick={(e) => e.stopPropagation()}
            aria-label="Code canvas"
          >
            <header>
              <strong>{canvas.title}</strong>
              <span className="cowork-canvas-actions">
                <CopyButton value={canvas.code} label="Copy code" />
                <button
                  type="button"
                  className="cowork-icon-btn"
                  aria-label="Close canvas"
                  onClick={() => setCanvas(null)}
                >
                  <X size={15} />
                </button>
              </span>
            </header>
            <div className="cowork-canvas-body">
              <pre>
                <code>{canvas.code}</code>
              </pre>
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}
