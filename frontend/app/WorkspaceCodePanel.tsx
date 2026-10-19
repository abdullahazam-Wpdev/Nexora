"use client";
import { useEffect, useState } from "react";
type Task = {
  id: string;
  status: string;
  diff?: string;
  error?: string;
  candidate_sha256?: string;
  events: { output?: string; failure?: string }[];
};
export default function WorkspaceCodePanel() {
  const [model, setModel] = useState("smollm2");
  const [qwenEnabled, setQwenEnabled] = useState(false);
  useEffect(() => {
    fetch("/api/assistant/status")
      .then((r) => r.json())
      .then((d) => setQwenEnabled(d.qwen_enabled))
      .catch(() => {});
  }, []);
  const [repositories, setRepositories] = useState<
    { id: string; path: string }[]
  >([]);
  const [repository, setRepository] = useState("");
  const [files, setFiles] = useState("solution.py");
  const [goal, setGoal] = useState("");
  const [acceptance, setAcceptance] = useState("");
  const [profile, setProfile] = useState("python");
  const [task, setTask] = useState<Task | null>(null);
  const [error, setError] = useState("");
  async function call(path: string, body?: unknown) {
    const r = await fetch(
      "/api/workspace-code" + path,
      body === undefined
        ? undefined
        : {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          },
    );
    const d = await r.json();
    if (!r.ok) throw Error(d.detail || "Coding task failed");
    return d;
  }
  async function act(fn: () => Promise<void>) {
    try {
      setError("");
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    }
  }
  useEffect(() => {
    fetch("/api/agent/repositories")
      .then((r) => r.json())
      .then(setRepositories)
      .catch(() => setError("Could not load registered projects"));
  }, []);
  useEffect(() => {
    if (!task || !["running", "queued"].includes(task.status)) return;
    const timer = setInterval(
      () => act(async () => setTask(await call("/tasks/" + task.id))),
      1000,
    );
    return () => clearInterval(timer);
  }, [task?.id, task?.status]);
  return (
    <section className="agent-panel">
      <h1>Scoped workspace coding</h1>
      <p>
        Qwen2.5-Coder is an evaluated external candidate, currently disabled
        after memory-cap failures. SmolLM2 remains the offline baseline. Up to
        four existing files; isolated Python/Node/TypeScript tests. Register a
        repository in NEXORA Code first. PHP and FastAPI runtime profiles remain
        blocked.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          act(async () =>
            setTask(
              await call("/tasks", {
                repository_id: repository,
                files: files
                  .split(",")
                  .map((s) => s.trim())
                  .filter(Boolean),
                goal,
                acceptance,
                profile,
                model,
                max_attempts: 2,
              }),
            ),
          );
        }}
      >
        <label>
          Model
          <select value={model} onChange={(e) => setModel(e.target.value)}>
            <option value="smollm2">SmolLM2 · weak offline baseline</option>
            <option value="qwen-coder" disabled={!qwenEnabled}>
              Qwen coder · requires verified memory profile
            </option>
          </select>
        </label>
        <label>
          Registered repository
          <select
            required
            value={repository}
            onChange={(e) => setRepository(e.target.value)}
          >
            <option value="">Select repository</option>
            {repositories.map((r) => (
              <option key={r.id} value={r.id}>
                {r.path}
              </option>
            ))}
          </select>
        </label>
        <label>
          Allowed files, comma separated
          <input value={files} onChange={(e) => setFiles(e.target.value)} />
        </label>
        <label>
          Execution profile
          <select value={profile} onChange={(e) => setProfile(e.target.value)}>
            <option value="python">Pure Python</option>
            <option value="node">Node modules</option>
            <option value="typescript">
              TypeScript transpilation and behavior
            </option>
            <option value="next-route">
              Web Request/Response unit profile
            </option>
            <option value="html">HTML/CSS static assertions</option>
          </select>
        </label>
        <label>
          Goal
          <textarea
            required
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
          />
        </label>
        <label>
          Owner acceptance tests
          <textarea
            required
            value={acceptance}
            onChange={(e) => setAcceptance(e.target.value)}
          />
        </label>
        <button
          disabled={task?.status === "running" || task?.status === "queued"}
        >
          Propose scoped patch and test
        </button>
      </form>
      {error && <p role="alert">{error}</p>}
      {task && (
        <article>
          <h2>{task.status}</h2>
          {task.error && <p role="alert">{task.error}</p>}
          <pre>{task.diff}</pre>
          {task.events.map((event, index) => (
            <pre key={index}>{event.output || event.failure}</pre>
          ))}
          {task.status === "awaiting_approval" && (
            <button
              onClick={() =>
                act(async () =>
                  setTask(
                    await call("/tasks/" + task.id + "/approve", {
                      candidate_sha256: task.candidate_sha256,
                    }),
                  ),
                )
              }
            >
              Approve exact tested files
            </button>
          )}
          {["queued", "running", "awaiting_approval"].includes(task.status) && (
            <button
              onClick={() =>
                act(async () =>
                  setTask(await call("/tasks/" + task.id + "/cancel", {})),
                )
              }
            >
              Cancel workspace task
            </button>
          )}
        </article>
      )}
    </section>
  );
}
