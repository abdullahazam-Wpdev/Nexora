"use client";
import { useEffect, useState } from "react";
type Row = {
  id: string;
  parameters: number;
  training_completion_tokens: number;
  training_seconds: number;
  validation: { completion_loss: number };
  test: { completion_perplexity: number };
  quality: { tool_success: number; schema_valid: number; total: number };
  selected: boolean;
};
export default function EvaluationPanel() {
  const [phase10, setPhase10] = useState<{
    coding?: { summary?: { passed: number; failed: number; blocked: number } };
    answers?: { correct?: number; total?: number };
  } | null>(null);
  useEffect(() => {
    fetch("/api/evaluations/phase10")
      .then((r) => (r.ok ? r.json() : null))
      .then(setPhase10)
      .catch(() => {});
  }, []);
  const [phase9, setPhase9] = useState<{
    coding: {
      passed: number;
      supported_total: number;
      runtime_blocked: number;
    };
    retrieval: { passed: number; total: number };
    core: {
      tool_correct: number;
      tool_total: number;
      arguments_exact: number;
      instruction_exact: number;
      instruction_total: number;
    };
  } | null>(null);
  useEffect(() => {
    fetch("/api/evaluations/phase9")
      .then((r) => r.json())
      .then(setPhase9)
      .catch(() => {});
  }, []);
  const [rows, setRows] = useState<Row[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    fetch("/api/evaluations/phase8")
      .then(async (r) => {
        if (!r.ok) throw Error("Evaluation data unavailable");
        setRows((await r.json()).models);
      })
      .catch((e) => setError(e.message));
  }, []);
  return (
    <section className="agent-panel">
      <h1>Research and reliability evaluations</h1>
      {phase10?.coding?.summary && (
        <>
          <h2>Phase 10</h2>
          <p>
            Frozen coding suite: {phase10.coding.summary.passed} passed,{" "}
            {phase10.coding.summary.failed} failed,{" "}
            {phase10.coding.summary.blocked} blocked, of 31 total. External
            SmolLM2, no promotion. Harness corrections rescore saved proposals;
            no regenerated answers.
          </p>
          <p>
            Literal evidence verification: {phase10.answers?.correct}/
            {phase10.answers?.total}. This does not measure semantic correctness
            or model hallucination.
          </p>
        </>
      )}
      {phase9 && (
        <>
          <h2>Phase 9</h2>
          <p>
            Stable offline baseline: SmolLM2. Qwen candidate is disabled after
            memory-cap failures; its coding result below used an approved
            temporary 1,152 MiB profile.
          </p>
          <ul>
            <li>
              Expanded coding: {phase9.coding.passed}/
              {phase9.coding.supported_total}; {phase9.coding.runtime_blocked}{" "}
              additional cases blocked by missing runtimes.
            </li>
            <li>
              Literal source-field retrieval: {phase9.retrieval.passed}/
              {phase9.retrieval.total}.
            </li>
            <li>
              New Core pilot: {phase9.core.tool_correct}/
              {phase9.core.tool_total} correct tool choices;{" "}
              {phase9.core.arguments_exact}/{phase9.core.tool_total} exact
              arguments; {phase9.core.instruction_exact}/
              {phase9.core.instruction_total} exact instructions. Not promoted.
            </li>
          </ul>
          <p>
            These are different protocols, not interchangeable accuracy
            measures.
          </p>
        </>
      )}
      <h2>Phase 8 Core pilots</h2>
      <p>
        Independent, randomly initialized Core pilots. Synthetic completion-only
        losses do not measure general assistant capability. None of these
        checkpoints is promoted.
      </p>
      {error && <p role="alert">{error}</p>}
      <div style={{ overflowX: "auto" }}>
        <table>
          <thead>
            <tr>
              <th>Run</th>
              <th>Parameters</th>
              <th>Supervised tokens</th>
              <th>Train seconds</th>
              <th>Validation loss</th>
              <th>Test perplexity</th>
              <th>Tool accuracy</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>{r.id}</td>
                <td>{r.parameters}</td>
                <td>{r.training_completion_tokens}</td>
                <td>{r.training_seconds.toFixed(3)}</td>
                <td>{r.validation.completion_loss.toFixed(3)}</td>
                <td>{r.test.completion_perplexity.toFixed(3)}</td>
                <td>
                  {r.quality.tool_success}/{r.quality.total}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p>
        <a href="/research">Open training and research dashboard</a>
      </p>
    </section>
  );
}
