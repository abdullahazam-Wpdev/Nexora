"use client";
import { useState } from "react";
type Hit = {
  doc_id: string;
  citation_id: string;
  title: string;
  source: string;
  text: string;
};
export default function DocumentPanel() {
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<Hit[]>([]);
  const [notice, setNotice] = useState("");
  async function search() {
    const r = await fetch(
      "/api/documents?project=local&q=" + encodeURIComponent(q),
    );
    const d = await r.json();
    if (!r.ok) throw Error(d.detail || "Search failed");
    setHits(d.matches);
  }
  async function act(fn: () => Promise<void>) {
    try {
      await fn();
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "Request failed");
    }
  }
  return (
    <section>
      <h2>Document retrieval</h2>
      <p>
        Owner-pasted reference text only. Documents are not training data or
        tool permissions.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          act(async () => {
            const r = await fetch("/api/documents", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                title,
                text,
                source: "urn:project:owner-document",
                project: "local",
              }),
            });
            const d = await r.json();
            if (!r.ok) throw Error(d.detail);
            setNotice("Indexed document " + d.id);
            setText("");
          });
        }}
      >
        <label>
          Document title
          <input
            required
            maxLength={200}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </label>
        <label>
          Document text
          <textarea
            aria-label="Document text"
            required
            maxLength={32000}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
        </label>
        <button>Index document</button>
      </form>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          act(search);
        }}
      >
        <label>
          Find document
          <input
            aria-label="Find document"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </label>
        <button>Search documents</button>
      </form>
      <p role="status">{notice}</p>
      {hits.map((h) => (
        <article key={h.citation_id}>
          <strong>{h.title}</strong>
          <p>{h.text}</p>
          <small>
            {h.source} · {h.citation_id}
          </small>
          <button
            onClick={() =>
              act(async () => {
                await fetch("/api/documents/" + h.doc_id + "?project=local", {
                  method: "DELETE",
                });
                await search();
              })
            }
          >
            Delete indexed document
          </button>
        </article>
      ))}
    </section>
  );
}
