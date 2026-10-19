"use client";
import { useEffect, useState } from "react";
type Task = {
  id: string;
  status: string;
  goal: string;
  plan_sha256: string;
  plan: {
    id: string;
    action: string;
    value: string | null;
    depends_on: string[];
  }[];
  events: { step: string; action: string; status: string }[];
  error?: string;
  evidence: { kind: string }[];
};
export default function ComputerPanel() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [task, setTask] = useState<Task | null>(null);
  const [value, setValue] = useState("NEXORA");
  const [error, setError] = useState("");
  async function call(path: string, body?: unknown) {
    const r = await fetch(
      "/api/computer" + path,
      body === undefined
        ? undefined
        : {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          },
    );
    const d = await r.json();
    if (!r.ok) throw Error(d.detail || "Browser task failed");
    return d;
  }
  async function act(fn: () => Promise<void>) {
    try {
      setError("");
      await fn();
      setTasks(await call("/tasks"));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Task failed");
    }
  }
  useEffect(() => {
    act(async () => {});
  }, []);
  useEffect(() => {
    if (!task || !["queued", "running"].includes(task.status)) return;
    const t = setInterval(
      () => act(async () => setTask(await call("/tasks/" + task.id))),
      1000,
    );
    return () => clearInterval(t);
  }, [task?.id, task?.status]);
  return (
    <section className="agent-panel">
      <h1>Isolated browser tasks</h1>
      <p>
        Review a plan, approve it, then verify a disposable local form. No
        personal browser profile, account login, uploads, messages, purchases or
        host commands.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          act(async () => setTask(await call("/tasks", { value })));
        }}
      >
        <label>
          Test display name
          <input
            aria-label="Test display name"
            value={value}
            maxLength={80}
            onChange={(e) => setValue(e.target.value)}
          />
        </label>
        <button>Create browser plan</button>
      </form>
      {error && <p role="alert">{error}</p>}
      <label>
        Task history
        <select
          aria-label="Browser task history"
          value={task?.id || ""}
          onChange={(e) =>
            act(async () => setTask(await call("/tasks/" + e.target.value)))
          }
        >
          <option value="">Choose a task</option>
          {tasks.map((t) => (
            <option key={t.id} value={t.id}>
              {t.goal} · {t.status}
            </option>
          ))}
        </select>
      </label>
      {task && (
        <article>
          <h2>{task.goal}</h2>
          <p role="status">{task.status}</p>
          <ol>
            {task.plan.map((s) => (
              <li key={s.id}>
                {s.action}: {s.value || "capture evidence"} · depends on{" "}
                {s.depends_on.join(", ") || "start"}
              </li>
            ))}
          </ol>
          {["awaiting_approval", "interrupted", "failed"].includes(
            task.status,
          ) && (
            <button
              onClick={() =>
                act(async () =>
                  setTask(
                    await call("/tasks/" + task.id + "/approve", {
                      plan_sha256: task.plan_sha256,
                    }),
                  ),
                )
              }
            >
              Approve exact browser plan
            </button>
          )}
          {!["completed", "cancelled"].includes(task.status) && (
            <button
              onClick={() =>
                act(async () =>
                  setTask(await call("/tasks/" + task.id + "/cancel", {})),
                )
              }
            >
              Cancel browser task
            </button>
          )}
          {task.error && <p role="alert">{task.error}</p>}
          <pre>
            {task.events
              .map((e) => e.step + " " + e.action + ": " + e.status)
              .join("\n")}
          </pre>
          {task.evidence.some((e) => e.kind === "screenshot") && (
            <img
              style={{ maxWidth: "100%" }}
              src={"/api/computer/tasks/" + task.id + "/screenshot"}
              alt="Verified disposable browser task screenshot"
            />
          )}
        </article>
      )}
    </section>
  );
}
