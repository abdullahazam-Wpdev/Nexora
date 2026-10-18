"use client";
import { useEffect, useState } from "react";
export default function SpeechPanel() {
  const [hosted, setHosted] = useState(false);
  const [consent, setConsent] = useState(false);
  const [rivaReady, setRivaReady] = useState(false);
  const [language, setLanguage] = useState("en");
  const [task, setTask] = useState("transcribe");
  const [configured, setConfigured] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    fetch("/api/speech/riva/status")
      .then((r) => r.json())
      .then((d) => setRivaReady(d.installed && d.key_configured))
      .catch(() => {});
    fetch("/api/nvidia/openai-models")
      .then((r) => r.json())
      .then((d) => setConfigured(d.whisper_configured))
      .catch(() => setError("Could not read speech service status"));
  }, []);
  return (
    <section className="agent-panel">
      <h1>Whisper Large V3</h1>
      <p>
        OpenAI speech recognition through a separately configured NVIDIA Speech
        NIM service. This is an audio model, not a text-chat assistant.
      </p>
      <p>
        {configured
          ? "Local speech service configured; inference availability will be checked on request."
          : "Speech service is not configured. No Whisper weights are installed on this laptop. See docs/OPENAI_NVIDIA_MODELS.md for setup and hardware requirements."}
      </p>
      <label>
        <input
          type="checkbox"
          checked={hosted}
          onChange={(e) => setHosted(e.target.checked)}
        />
        Use NVIDIA hosted Riva (requires API key)
      </label>
      {hosted && (
        <>
          <label>
            Language
            <input
              aria-label="Speech language"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
            />
          </label>
          <label>
            Task
            <select
              aria-label="Speech task"
              value={task}
              onChange={(e) => setTask(e.target.value)}
            >
              <option value="transcribe">Transcribe</option>
              <option value="translate">Translate to English</option>
            </select>
          </label>
          <label>
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
            />
            Allow sending this audio to NVIDIA; quota/cost may apply.
          </label>
          <p>
            {rivaReady
              ? "Riva client and key configured; recognition is not yet verified."
              : "Riva requires an installed client and a server-side NVIDIA key."}
          </p>
        </>
      )}
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          if (!file) return;
          setBusy(true);
          setError("");
          try {
            if (file.size > 2000000)
              throw new Error("Use a mono WAV file below 2 MB and 30 seconds.");
            const bytes = new Uint8Array(await file.arrayBuffer());
            let binary = "";
            for (const byte of bytes) binary += String.fromCharCode(byte);
            const r = await fetch(
              hosted ? "/api/speech/riva/transcribe" : "/api/speech/transcribe",
              {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  wav_base64: btoa(binary),
                  language: hosted ? language : "en-US",
                  task,
                  allow_hosted: consent,
                }),
              },
            );
            const data = await r.json();
            if (!r.ok) throw new Error(data.detail || "Transcription failed");
            setText(data.text);
          } catch (err) {
            setError(
              err instanceof Error ? err.message : "Transcription failed",
            );
          } finally {
            setBusy(false);
          }
        }}
      >
        <label>
          Audio WAV
          <input
            aria-label="Audio WAV"
            type="file"
            accept="audio/wav,.wav"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
        </label>
        <button
          disabled={
            !file || (hosted ? !rivaReady || !consent : !configured) || busy
          }
        >
          {task === "translate" && hosted
            ? "Translate audio"
            : "Transcribe audio"}
        </button>
      </form>
      {error && <p role="alert">{error}</p>}
      {text && <pre>{text}</pre>}
    </section>
  );
}
