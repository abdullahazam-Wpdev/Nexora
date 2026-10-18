"use client";
import { useState, useEffect } from "react";
import {
  Activity,
  ArrowUpRight,
  ArrowRight,
  Box,
  Check,
  ChevronRight,
  Cpu,
  Database,
  FlaskConical,
  HardDrive,
  Layers,
  LayoutDashboard,
  Loader2,
  MessageSquare,
  Moon,
  Play,
  RefreshCw,
  Settings,
  ShieldCheck,
  Sun,
  Terminal,
  Workflow,
} from "lucide-react";
const sections = [
  ["Overview", LayoutDashboard],
  ["Core Model Lab", Box],
  ["Dataset Manager", Database],
  ["Training Experiments", FlaskConical],
  ["Evaluation Center", ShieldCheck],
  ["Model Playground", MessageSquare],
  ["System Health", Activity],
  ["Storage", HardDrive],
  ["Settings", Settings],
] as const;
type Experiment = {
  id: string;
  name: string;
  status: string;
  steps: number;
  parameters: number;
  seconds: number;
  test_loss: number | null;
  history: { step: number; train_loss: number; validation_loss: number }[];
  config: {
    dim: number;
    layers: number;
    heads: number;
    context: number;
    vocab_size: number;
  };
  warning: string;
};
type Health = {
  status: string;
  cpu_percent: number;
  threads: number;
  memory_total: number;
  memory_available: number;
  disk_total: number;
  disk_free: number;
  storage_path: string;
  device: string;
  database: string;
};
type Dataset = {
  id: string;
  documents: number;
  license: string;
  provenance: string;
  approved: boolean;
};
const gb = (n: number) => `${(n / 1024 ** 3).toFixed(1)} GB`;
export default function Home() {
  const [section, setSection] = useState("Overview"),
    [dark, setDark] = useState(true),
    [health, setHealth] = useState<Health | null>(null),
    [runs, setRuns] = useState<Experiment[]>([]),
    [datasets, setDatasets] = useState<Dataset[]>([]),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true),
    [busy, setBusy] = useState(false),
    [running, setRunning] = useState(false),
    [prompt, setPrompt] = useState("2 + 3 ="),
    [output, setOutput] = useState(""),
    [notice, setNotice] = useState("");
  async function api(path: string, body?: unknown) {
    const r = await fetch(
      "/api/" + path,
      body
        ? {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          }
        : undefined,
    );
    const data = await r.json();
    if (!r.ok)
      throw Error(
        typeof data.detail === "string"
          ? data.detail
          : JSON.stringify(data.detail),
      );
    return data;
  }
  async function refresh() {
    try {
      const [h, e, d, t] = await Promise.all([
        api("health"),
        api("experiments"),
        api("datasets"),
        api("training"),
      ]);
      setHealth(h);
      setRuns(e);
      setDatasets(d);
      setRunning(t.running);
      setError("");
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 8000);
    setDark(localStorage.getItem("nexora-theme") !== "light");
    return () => clearInterval(timer);
  }, []);
  async function train(resume = false) {
    setBusy(true);
    setNotice("");
    try {
      await api("training", { steps: 160, resume });
      setRunning(true);
      setNotice(
        "CPU training started. Results update when the checkpoint is saved.",
      );
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  async function generate() {
    setBusy(true);
    try {
      const r = await api("generate", { prompt, max_tokens: 32 });
      setOutput(r.text);
      setError("");
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  const model = runs[0],
    last = model?.history.at(-1);
  function chart() {
    if (!model)
      return (
        <div className="empty">
          Run the first experiment to see measured loss.
        </div>
      );
    const hist = model.history,
      max =
        Math.max(...hist.flatMap((h) => [h.train_loss, h.validation_loss])) *
        1.1;
    const points = (key: "train_loss" | "validation_loss") =>
      hist
        .map(
          (h, i) =>
            `${45 + (i * 600) / Math.max(1, hist.length - 1)},${205 - (h[key] / max) * 170}`,
        )
        .join(" ");
    return (
      <>
        <div className="legend">
          <span>
            <i />
            Training loss
          </span>
          <span>
            <i className="purple" />
            Validation loss
          </span>
        </div>
        <svg
          viewBox="0 0 680 245"
          role="img"
          aria-label="Measured training and validation loss by step"
        >
          {[0, 1, 2, 3].map((i) => (
            <g key={i}>
              <line
                x1="45"
                y1={35 + i * 57}
                x2="645"
                y2={35 + i * 57}
                stroke="var(--line)"
                strokeDasharray="3 5"
              />
              <text x="6" y={40 + i * 57} fill="var(--muted)" fontSize="11">
                {(max * (1 - i / 3)).toFixed(1)}
              </text>
            </g>
          ))}
          <polyline
            points={points("validation_loss")}
            fill="none"
            stroke="#a78bfa"
            strokeWidth="2"
          />
          <polyline
            points={points("train_loss")}
            fill="none"
            stroke="#70e5b5"
            strokeWidth="2.5"
          />
          <text x="45" y="236" fill="var(--muted)" fontSize="11">
            Step 1
          </text>
          <text x="587" y="236" fill="var(--muted)" fontSize="11">
            Step {model.steps}
          </text>
        </svg>
      </>
    );
  }
  return (
    <div className={dark ? "shell" : "shell light"}>
      <aside>
        <a href="#" className="brand" onClick={() => setSection("Overview")}>
          <span className="brandmark">N</span>NEXORA
          <span className="os">OS</span>
        </a>
        <div className="workspace">
          <div className="workspaceIcon">
            <Layers size={19} />
          </div>
          <div>
            Research workspace<small>Local environment</small>
          </div>
          <ChevronRight size={14} />
        </div>
        <div className="navlabel">WORKSPACE</div>
        <nav>
          {sections.map(([name, Icon]) => (
            <button
              key={name}
              aria-label={name}
              className={section === name ? "active" : ""}
              onClick={() => {
                setSection(name);
                setNotice("");
              }}
            >
              <Icon size={17} />
              {name}
              {name === "Core Model Lab" && (
                <span className="navtag">CORE</span>
              )}
            </button>
          ))}
        </nav>
        <div className="navlabel futureLabel">ON THE HORIZON</div>
        <div className="future">
          <Workflow size={16} />
          Digital workforce<span>Planned</span>
        </div>
        <div className="future">
          <Terminal size={16} />
          NEXORA Code<span>Planned</span>
        </div>
        <div className="sidebarBottom">
          <div className="local">
            <i className={health ? "dot" : "dot offline"} />
            {health ? "Local system connected" : "Connecting to system"}
          </div>
          <p>
            Independent by design.
            <br />
            Built one experiment at a time.
          </p>
          <div className="profile">
            <div className="avatar">N</div>
            <div>
              Local researcher<small>Owner · this machine</small>
            </div>
          </div>
        </div>
      </aside>
      <div className="main">
        <header>
          <div>
            NEXORA AI OS <ChevronRight size={13} />
            <span>{section}</span>
          </div>
          <div className="headerRight">
            <span className="env">
              <i className="dot" />
              LOCAL / CPU
            </span>
            <button
              className="iconbtn"
              aria-label="Toggle color theme"
              onClick={() => {
                setDark(!dark);
                localStorage.setItem("nexora-theme", dark ? "light" : "dark");
              }}
            >
              {dark ? <Sun size={17} /> : <Moon size={17} />}
            </button>
          </div>
        </header>
        <main>
          <div className="titleRow">
            <div>
              <div className="eyebrow">YOUR INDEPENDENT AI WORKSPACE</div>
              <h1>
                {section === "Overview" ? "Intelligence starts here." : section}
              </h1>
              <p>
                {section === "Overview"
                  ? "Train, evaluate, and explore your own models. Entirely on your machine."
                  : "A transparent view of your local research and infrastructure."}
              </p>
            </div>
            <button
              className="secondary"
              onClick={refresh}
              aria-label="Refresh system data"
            >
              <RefreshCw size={15} />
              Refresh
            </button>
          </div>
          {error && (
            <div className="alert" role="alert">
              {error} <button onClick={refresh}>Retry connection</button>
            </div>
          )}
          {notice && (
            <div className="notice" role="status">
              {notice}
            </div>
          )}
          {loading && (
            <div className="notice">
              <Loader2 size={16} className="spin" />
              Connecting to local backend…
            </div>
          )}
          {section === "Overview" && (
            <>
              <section className="hero">
                <div>
                  <div className="heroBadge">
                    <span className="dot" />
                    NEXORA CORE · FIRST RESEARCH MILESTONE
                  </div>
                  <h2>
                    Small model.
                    <br />
                    <span>Independent foundation.</span>
                  </h2>
                  <p>
                    A decoder-only Transformer, trained from random weights.
                    <br />
                    Real experiments. Reproducible progress. Your research.
                  </p>
                  <div className="heroActions">
                    <button
                      className="primary"
                      onClick={() => setSection("Core Model Lab")}
                    >
                      Open Model Lab
                      <ArrowRight size={16} />
                    </button>
                    <button
                      className="textbtn"
                      onClick={() => setSection("Model Playground")}
                    >
                      Try local inference
                      <ArrowUpRight size={16} />
                    </button>
                  </div>
                </div>
                <div className="orb" aria-hidden="true">
                  <div className="orbit one" />
                  <div className="orbit two" />
                  <div className="orbit three" />
                  <div className="coreShape">
                    N<span>CORE</span>
                  </div>
                  <div className="orbLabel">
                    RANDOM WEIGHTS → ORIGINAL MODEL
                  </div>
                </div>
              </section>
              <div className="statgrid">
                <div className="stat">
                  <span>
                    Registered models
                    <Box size={16} />
                  </span>
                  <strong>
                    {runs.length}
                    <small>local</small>
                  </strong>
                  <p>Independently initialized</p>
                </div>
                <div className="stat">
                  <span>
                    Completed training steps
                    <Activity size={16} />
                  </span>
                  <strong>{model?.steps ?? "—"}</strong>
                  <p>
                    {model
                      ? `${model.parameters.toLocaleString()} parameters`
                      : "No completed experiment"}
                  </p>
                </div>
                <div className="stat">
                  <span>
                    Approved datasets
                    <Database size={16} />
                  </span>
                  <strong>{datasets.length}</strong>
                  <p>Provenance recorded</p>
                </div>
                <div className="stat">
                  <span>
                    Available memory
                    <Cpu size={16} />
                  </span>
                  <strong>{health ? gb(health.memory_available) : "—"}</strong>
                  <p>
                    {health
                      ? `of ${gb(health.memory_total)} system memory`
                      : "Awaiting system metrics"}
                  </p>
                </div>
              </div>
              <div className="twoColumns">
                <section className="panel">
                  <div className="panelHead">
                    <div>
                      <h3>Learning, measured.</h3>
                      <p>Latest experiment · next-token prediction</p>
                    </div>
                    <span className="chip">
                      {model ? "COMPLETED" : "NO RUNS"}
                    </span>
                  </div>
                  {chart()}
                </section>
                <section className="panel system">
                  <div className="panelHead">
                    <h3>System at a glance</h3>
                    <Activity size={17} />
                  </div>
                  {[
                    ["Compute backend", "CPU · float32"],
                    ["Database", health?.database ?? "—"],
                    ["Training job", running ? "Running" : "Idle"],
                    ["API connection", health ? "Healthy" : "Unavailable"],
                  ].map(([a, b]) => (
                    <div className="systemRow" key={a}>
                      <span>{a}</span>
                      <strong>{b}</strong>
                    </div>
                  ))}
                  <div className="storageBar">
                    <div>
                      <span>Internal storage</span>
                      <span>
                        {health ? `${gb(health.disk_free)} free` : "—"}
                      </span>
                    </div>
                    <div className="track">
                      <i
                        style={{
                          width: health
                            ? `${100 * (1 - health.disk_free / health.disk_total)}%`
                            : "0%",
                        }}
                      />
                    </div>
                  </div>
                  <button
                    className="textbtn"
                    onClick={() => setSection("System Health")}
                  >
                    View system details
                    <ArrowUpRight size={14} />
                  </button>
                </section>
              </div>
              <div className="sectionHeading">
                <h3>Your research, in motion</h3>
                <span>FOUNDATION FIRST</span>
              </div>
              <div className="quickgrid">
                {[
                  [
                    "01",
                    "Curate your data",
                    "Approved, traceable datasets.",
                    "Dataset Manager",
                    Database,
                  ],
                  [
                    "02",
                    "Run an experiment",
                    "Train from scratch on your CPU.",
                    "Training Experiments",
                    FlaskConical,
                  ],
                  [
                    "03",
                    "Explore your model",
                    "Inspect real local generation.",
                    "Model Playground",
                    MessageSquare,
                  ],
                ].map(([n, title, desc, dest, Icon]: any) => (
                  <button
                    className="quick"
                    key={n}
                    onClick={() => setSection(dest)}
                  >
                    <div>
                      <span>{n}</span>
                      <Icon size={19} />
                    </div>
                    <h3>
                      {title}
                      <ArrowUpRight size={16} />
                    </h3>
                    <p>{desc}</p>
                  </button>
                ))}
              </div>
            </>
          )}
          {section === "Core Model Lab" && (
            <>
              <section className="panel">
                <div className="panelHead">
                  <div>
                    <h2>NEXORA Core / Tiny</h2>
                    <p>Independent decoder-only autoregressive Transformer</p>
                  </div>
                  <span className="chip">RESEARCH</span>
                </div>
                <div className="statgrid">
                  {model &&
                    Object.entries(model.config).map(([k, v]) => (
                      <div className="stat" key={k}>
                        <span>{k}</span>
                        <strong>{v}</strong>
                      </div>
                    ))}
                </div>
                <p>
                  Byte-level BPE · RoPE · RMSNorm · SwiGLU · AdamW · causal
                  attention
                </p>
                <div className="notice">
                  {model?.warning ??
                    "Train the first CPU experiment to register a checkpoint."}
                </div>
                <button
                  className="primary"
                  disabled={busy || running}
                  onClick={() => train()}
                >
                  <Play size={16} />
                  {running
                    ? "Training in progress"
                    : "Train from scratch · 160 steps"}
                </button>
              </section>
            </>
          )}
          {section === "Training Experiments" && (
            <section className="panel">
              <div className="panelHead">
                <div>
                  <h3>Training experiments</h3>
                  <p>
                    Two microbatches per optimizer step · gradient clipping ·
                    warmup and cosine decay
                  </p>
                </div>
                <button
                  className="primary"
                  disabled={running || busy}
                  onClick={() => train(!!model)}
                >
                  <Play size={15} />
                  {running
                    ? "Running"
                    : model
                      ? "Resume · 160 steps"
                      : "Start training"}
                </button>
              </div>
              {chart()}
              <div className="tableWrap">
                <table>
                  <thead>
                    <tr>
                      <th>Experiment</th>
                      <th>Steps</th>
                      <th>Parameters</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {runs.map((r) => (
                      <tr key={r.id}>
                        <td>{r.name}</td>
                        <td>{r.steps}</td>
                        <td>{r.parameters.toLocaleString()}</td>
                        <td>
                          <span className="chip">{r.status}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
          {section === "Dataset Manager" && (
            <>
              <section className="panel">
                <div className="panelHead">
                  <div>
                    <h3>Approved datasets</h3>
                    <p>
                      Deduplicated documents · SHA-256 provenance · disjoint
                      document splits
                    </p>
                  </div>
                  <Database size={20} />
                </div>
                {datasets.length ? (
                  datasets.map((d) => (
                    <div className="dataset" key={d.id}>
                      <div className="datasetIcon">
                        <Database size={22} />
                      </div>
                      <div>
                        <h3>{d.id}</h3>
                        <p>{d.provenance}</p>
                        <span className="chip">{d.license}</span>{" "}
                        <span className="muted">
                          {d.documents} documents · approved
                        </span>
                      </div>
                      <Check size={18} />
                    </div>
                  ))
                ) : (
                  <div className="empty">No approved datasets yet.</div>
                )}
              </section>
              <section className="panel">
                <h3>Ingestion requires explicit approval</h3>
                <p>
                  Submit documents, license, provenance and approved=true
                  through POST /api/datasets. Unapproved sources, duplicate-only
                  corpora, detected credentials and email addresses are
                  rejected.
                </p>
                <a
                  href="http://127.0.0.1:8000/docs"
                  target="_blank"
                  rel="noreferrer"
                  className="textbtn"
                >
                  Open interactive API documentation
                  <ArrowUpRight size={15} />
                </a>
              </section>
            </>
          )}
          {section === "Evaluation Center" && (
            <>
              <div className="statgrid">
                <div className="stat">
                  <span>Held-out test loss</span>
                  <strong>{model?.test_loss?.toFixed(3) ?? "—"}</strong>
                  <p>Cross entropy · arithmetic fixture</p>
                </div>
                <div className="stat">
                  <span>Latest train loss</span>
                  <strong>{last?.train_loss.toFixed(3) ?? "—"}</strong>
                  <p>Measured training batch</p>
                </div>
                <div className="stat">
                  <span>Latest validation loss</span>
                  <strong>{last?.validation_loss.toFixed(3) ?? "—"}</strong>
                  <p>Held-out document split</p>
                </div>
              </div>
              <section className="panel">
                <h3>Evaluation scope</h3>
                <p>
                  These measurements validate the training pipeline on a tiny
                  arithmetic corpus. They do not demonstrate reasoning, broad
                  language ability or instruction following. Standardized
                  language benchmarks remain planned.
                </p>
                {chart()}
              </section>
            </>
          )}
          {section === "Model Playground" && (
            <section className="panel playground">
              <div className="panelHead">
                <div>
                  <h3>Talk to the checkpoint</h3>
                  <p>
                    NEXORA Core / Tiny · deterministic greedy decoding · CPU
                  </p>
                </div>
                <span className="chip">LOCAL INFERENCE</span>
              </div>
              <div className="notice">
                Research model trained on arithmetic fixtures. It is not a chat
                assistant; output may be repetitive or incorrect.
              </div>
              <label htmlFor="prompt">Prompt</label>
              <textarea
                id="prompt"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                maxLength={256}
              />
              <button
                className="primary"
                disabled={busy || !model || !prompt.trim()}
                onClick={generate}
              >
                {busy ? (
                  <Loader2 className="spin" size={16} />
                ) : (
                  <Play size={16} />
                )}
                Generate 32 tokens
              </button>
              <label htmlFor="generated">Model output</label>
              <pre id="generated" aria-live="polite">
                {output || "Generated tokens will appear here."}
              </pre>
            </section>
          )}
          {section === "System Health" && (
            <section className="panel">
              <h3>Live machine telemetry</h3>
              {health &&
                Object.entries(health).map(([k, v]) => (
                  <div className="systemRow" key={k}>
                    <span>{k.replaceAll("_", " ")}</span>
                    <code>{String(v)}</code>
                  </div>
                ))}
            </section>
          )}
          {section === "Storage" && (
            <section className="panel">
              <HardDrive size={30} />
              <h2>Research lives on your machine.</h2>
              <p>
                Datasets, checkpoints and SQLite records are excluded from Git.
              </p>
              <div className="systemRow">
                <span>Artifact root</span>
                <code>{health?.storage_path ?? "—"}</code>
              </div>
              <div className="systemRow">
                <span>Free space</span>
                <strong>{health ? gb(health.disk_free) : "—"}</strong>
              </div>
              <p>
                Set NEXORA_STORAGE before starting both services to use an
                external SSD or another mounted directory. Stop services before
                copying artifacts.
              </p>
            </section>
          )}
          {section === "Settings" && (
            <section className="panel">
              <h3>Workspace settings</h3>
              <div className="systemRow">
                <span>Appearance</span>
                <button className="secondary" onClick={() => setDark(!dark)}>
                  {dark ? "Switch to light" : "Switch to dark"}
                </button>
              </div>
              <div className="systemRow">
                <span>External model APIs</span>
                <span>Not configured · no charges</span>
              </div>
              <div className="systemRow">
                <span>Network access</span>
                <span>Localhost only</span>
              </div>
              <div className="systemRow">
                <span>Identity</span>
                <span>Local owner · authentication planned</span>
              </div>
              <p>
                Advanced agents, terminal execution, public deployment and
                multimodal capabilities are tracked in the project roadmap.
              </p>
            </section>
          )}
          <footer>
            <span>
              <i className="dot" />
              NEXORA AI OS <span className="muted">/ research preview 0.1</span>
            </span>
            <span>Local-first. Independently built.</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
