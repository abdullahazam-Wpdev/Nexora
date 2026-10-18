"use client";
import { useEffect, useState } from "react";
type Task = {
  id: string;
  status: string;
  diff?: string;
  error?: string;
  candidate_sha256?: string;
  seconds?: number;
  events: { role: string; action: string; detail: unknown }[];
};
async function call(path: string, body?: unknown, method?: string) {
  const r = await fetch(path, {
    method: method || (body ? "POST" : "GET"),
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (r.status === 204) return {};
  const d = await r.json();
  if (!r.ok) throw new Error(d.detail || "Request failed");
  return d;
}
export default function AgentPanel({ view }: { view: "code" | "memory" }) {
  const [repositories, setRepositories] = useState<
    { id: string; path: string }[]
  >([]);
  const [repo, setRepo] = useState("");
  const [root, setRoot] = useState("");
  const [path, setPath] = useState("solution.py");
  const [goal, setGoal] = useState("");
  const [acceptance, setAcceptance] = useState("");
  const [task, setTask] = useState<Task | null>(null);
  const [history, setHistory] = useState<Task[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [entries, setEntries] = useState<
    { id: string; content: string; provenance: string }[]
  >([]);
  const [memory, setMemory] = useState("");
  const [query, setQuery] = useState("");
  async function refresh() {
    if (view === "code") {
      const r = await call("/api/agent/repositories");
      setRepositories(r);
      if (r.length && !repo) setRepo(r[0].id);
      setHistory(await call("/api/agent/tasks"));
    } else
      setEntries(
        (await call("/api/knowledge/entries?q=" + encodeURIComponent(query)))
          .entries,
      );
  }
  useEffect(() => {
    refresh().catch((e) => setError(e.message));
  }, [view]);
  useEffect(() => {
    if (!task || !["queued", "running"].includes(task.status)) return;
    const id = setInterval(
      () =>
        call("/api/agent/tasks/" + task.id)
          .then(setTask)
          .catch((e) => setError(e.message)),
      1000,
    );
    return () => clearInterval(id);
  }, [task?.id, task?.status]);
  async function act(fn: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    try {
      await fn();
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="agent-panel">
      <h1>{view === "code" ? "NEXORA Code" : "Project memory"}</h1>
      <p>
        {view === "code"
          ? "Propose one Python file change, verify in isolation, then review before applying. Local SmolLM2 remains a limited reference model."
          : "Owner-controlled notes, separate from conversations and training. Stored text never grants tool permissions."}
      </p>
      {error && (
        <p role="alert" className="cowork-error">
          {error}
        </p>
      )}
      {view === "code" ? (
        <>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              act(async () => {
                const r = await call("/api/agent/repositories", { path: root });
                setRepo(r.id);
                setRoot("");
              });
            }}
          >
            <label>
              Authorize a project directory
              <input
                aria-label="Project directory"
                value={root}
                onChange={(e) => setRoot(e.target.value)}
                placeholder="/absolute/path/to/disposable-project"
                required
              />
            </label>
            <button disabled={busy}>Register project</button>
          </form>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              act(async () =>
                setTask(
                  await call("/api/agent/tasks", {
                    repository_id: repo,
                    path,
                    goal,
                    acceptance,
                    provider: "ollama",
                    max_attempts: 2,
                  }),
                ),
              );
            }}
          >
            <label>
              Registered project
              <select
                value={repo}
                onChange={(e) => setRepo(e.target.value)}
                required
              >
                <option value="">Choose a project</option>
                {repositories.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.path}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Python file
              <input
                value={path}
                onChange={(e) => setPath(e.target.value)}
                required
              />
            </label>
            <label>
              Goal
              <textarea
                aria-label="Coding goal"
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                required
              />
            </label>
            <label>
              Acceptance assertions
              <textarea
                aria-label="Acceptance checks"
                value={acceptance}
                onChange={(e) => setAcceptance(e.target.value)}
                placeholder="assert add(2, 3) == 5"
                required
              />
            </label>
            <button disabled={busy || !repo}>Propose and test</button>
          </form>
          <nav>
            {history.slice(0, 5).map((t) => (
              <button
                key={t.id}
                onClick={() =>
                  call("/api/agent/tasks/" + t.id)
                    .then(setTask)
                    .catch((e) => setError(e.message))
                }
              >
                {t.id.slice(0, 8)} · {t.status}
              </button>
            ))}
          </nav>
          {task && (
            <article>
              <h2>
                Task {task.id.slice(0, 8)} · {task.status}
              </h2>
              <ol>
                {task.events.map((event, i) => (
                  <li key={i}>
                    <strong>
                      {event.role} · {event.action}
                    </strong>
                    <pre>{JSON.stringify(event.detail, null, 2)}</pre>
                  </li>
                ))}
              </ol>
              {task.error && <p>{task.error}</p>}
              {task.diff && (
                <>
                  <h3>Proposed diff</h3>
                  <pre>{task.diff}</pre>
                </>
              )}
              {task.status === "awaiting_approval" && (
                <button
                  disabled={busy}
                  onClick={() =>
                    act(async () =>
                      setTask(
                        await call(`/api/agent/tasks/${task.id}/approve`, {
                          candidate_sha256: task.candidate_sha256,
                        }),
                      ),
                    )
                  }
                >
                  Approve this verified diff and apply
                </button>
              )}
              {["queued", "running", "awaiting_approval"].includes(
                task.status,
              ) && (
                <button
                  disabled={busy}
                  onClick={() =>
                    act(async () => {
                      await call(`/api/agent/tasks/${task.id}/cancel`, {});
                      setTask(await call(`/api/agent/tasks/${task.id}`));
                    })
                  }
                >
                  Cancel task
                </button>
              )}
            </article>
          )}
        </>
      ) : (
        <>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              act(async () => {
                await call("/api/knowledge/entries", {
                  kind: "project",
                  project: "local",
                  content: memory,
                  provenance: "Owner-entered project note",
                  retention_days: 30,
                });
                setMemory("");
              });
            }}
          >
            <label>
              New project note
              <textarea
                aria-label="Memory note"
                value={memory}
                onChange={(e) => setMemory(e.target.value)}
                required
              />
            </label>
            <button disabled={busy}>Save for 30 days</button>
          </form>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              act(refresh);
            }}
          >
            <label>
              Search memory
              <input value={query} onChange={(e) => setQuery(e.target.value)} />
            </label>
            <button>Search</button>
          </form>
          {entries.map((m) => (
            <article key={m.id}>
              <pre>{m.content}</pre>
              <small>{m.provenance}</small>
              <button
                onClick={() =>
                  act(async () => {
                    await call(
                      "/api/knowledge/entries/" + m.id,
                      undefined,
                      "DELETE",
                    );
                  })
                }
              >
                Delete note
              </button>
            </article>
          ))}
        </>
      )}
    </section>
  );
}
