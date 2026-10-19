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
      <h1>Core research evaluations</h1>
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
