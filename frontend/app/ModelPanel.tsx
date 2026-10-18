"use client";
import { useEffect, useState } from "react";
type Catalog = {
  nvidia: { id: string; status: string }[];
  fcc: {
    providers: { provider_id: string; display_name: string }[];
    aliases: { id: string; display_name: string }[];
  };
  fcc_available_models: string[];
  fcc_error: string | null;
};
export default function ModelPanel() {
  const [data, setData] = useState<Catalog | null>(null);
  const [error, setError] = useState("");
  const [q, setQ] = useState("");
  useEffect(() => {
    fetch("/api/models/catalog")
      .then(async (r) => {
        if (!r.ok) throw Error("Catalog unavailable");
        setData(await r.json());
      })
      .catch((e) => setError(e.message));
  }, []);
  return (
    <section className="agent-panel">
      <h1>Model catalog</h1>
      <p>
        Provider support and routing names do not install model weights or grant
        free access. Account terms and quotas apply.
      </p>
      <label>
        Search catalog
        <input
          aria-label="Search models"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
      </label>
      {error && <p role="alert">{error}</p>}
      {data && (
        <>
          <h2>NVIDIA requested models</h2>
          {data.nvidia
            .filter((m) => m.id.includes(q.toLowerCase()))
            .map((m) => (
              <article key={m.id}>
                <strong>{m.id}</strong>
                <p>{m.status}</p>
              </article>
            ))}
          <h2>FCC configured upstream models</h2>
          {data.fcc_error && <p>{data.fcc_error}</p>}
          {data.fcc_available_models.map((m) => (
            <p key={m}>{m}</p>
          ))}
          <h2>FCC routing aliases</h2>
          <p>
            All aliases currently route to the local SmolLM2 reference. They are
            not Claude models.
          </p>
          {data.fcc.aliases
            .filter((m) => m.id.includes(q.toLowerCase()))
            .map((m) => (
              <p key={m.id}>{m.id}</p>
            ))}
          <h2>FCC provider support ({data.fcc.providers.length})</h2>
          {data.fcc.providers
            .filter((m) =>
              (m.provider_id + " " + m.display_name)
                .toLowerCase()
                .includes(q.toLowerCase()),
            )
            .map((m) => (
              <p key={m.provider_id}>
                {m.display_name} · {m.provider_id}
              </p>
            ))}
        </>
      )}
    </section>
  );
}
