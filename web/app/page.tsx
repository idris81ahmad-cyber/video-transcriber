"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { toJson, toSrt, toTxt, toVtt, type TranscriptResult } from "@/lib/formats";

type FormatKey = "txt" | "srt" | "vtt" | "json";

const ACCEPT =
  "audio/*,video/*,.mp3,.mp4,.wav,.m4a,.webm,.ogg,.flac,.mpeg,.mpga,.oga";

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function downloadText(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function HomePage() {
  const [file, setFile] = useState<File | null>(null);
  const [language, setLanguage] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [result, setResult] = useState<TranscriptResult | null>(null);
  const [providerReady, setProviderReady] = useState<boolean | null>(null);
  const [activeTab, setActiveTab] = useState<FormatKey>("txt");

  useEffect(() => {
    fetch("/api/transcribe")
      .then((r) => r.json())
      .then((d) => setProviderReady(Boolean(d.ok)))
      .catch(() => setProviderReady(false));
  }, []);

  const outputs = useMemo(() => {
    if (!result) return null;
    return {
      txt: toTxt(result),
      srt: toSrt(result),
      vtt: toVtt(result),
      json: toJson(result),
    };
  }, [result]);

  const onFiles = useCallback((list: FileList | null) => {
    const next = list?.[0] || null;
    setFile(next);
    setResult(null);
    setError("");
    setStatus(next ? `Selected ${next.name}` : "");
  }, []);

  async function onTranscribe() {
    if (!file) {
      setError("Choose a video or audio file first.");
      return;
    }

    setBusy(true);
    setError("");
    setStatus("Uploading and transcribing… this may take a minute.");
    setResult(null);

    try {
      // Vercel Hobby request body limit is ~4.5 MB
      if (file.size > 4 * 1024 * 1024) {
        throw new Error(
          `File is ${(file.size / (1024 * 1024)).toFixed(1)} MB. Keep uploads under 4 MB on this free Vercel plan (compress or trim the audio).`,
        );
      }

      const body = new FormData();
      body.append("file", file);
      if (language.trim()) body.append("language", language.trim());

      const res = await fetch("/api/transcribe", {
        method: "POST",
        body,
      });

      const raw = await res.text();
      let data: {
        error?: string;
        text?: string;
        language?: string;
        duration?: number;
        segments?: Array<{ id?: number; start: number; end: number; text: string }>;
        provider?: string;
        model?: string;
      };

      try {
        data = raw ? JSON.parse(raw) : {};
      } catch {
        const snippet = raw.replace(/\s+/g, " ").slice(0, 160);
        if (res.status === 413) {
          throw new Error(
            "Upload too large for Vercel (max ~4.5 MB). Compress or use a shorter clip.",
          );
        }
        throw new Error(
          `Server returned non-JSON (${res.status}). ${snippet || "Empty body"}`,
        );
      }

      if (!res.ok) {
        throw new Error(data.error || `Request failed (${res.status})`);
      }

      setResult({
        text: data.text || "",
        language: data.language,
        duration: data.duration,
        segments: data.segments,
      });
      setStatus(
        `Done via ${data.provider}/${data.model}` +
          (data.language ? ` · language: ${data.language}` : "") +
          (typeof data.duration === "number" ? ` · ${data.duration.toFixed(1)}s` : ""),
      );
      setActiveTab("txt");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Transcription failed");
      setStatus("");
    } finally {
      setBusy(false);
    }
  }

  const stem = file?.name?.replace(/\.[^.]+$/, "") || "transcript";

  return (
    <main className="page">
      <header className="hero">
        <div className="badge">Video Transcriber · Whisper on Vercel</div>
        <h1>Turn video & audio into clean transcripts</h1>
        <p>
          Upload a clip, get timed subtitles and plain text. This Vercel app uses{" "}
          <strong>xAI Grok Speech-to-Text</strong> (or Groq/OpenAI). For fully offline
          Faster-Whisper, use the local Python CLI.
        </p>
      </header>

      <div className="grid">
        <section className="card">
          <h2>1. Upload media</h2>

          <div
            className={`dropzone${dragOver ? " dragover" : ""}`}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              onFiles(e.dataTransfer.files);
            }}
          >
            <input
              type="file"
              accept={ACCEPT}
              onChange={(e) => onFiles(e.target.files)}
            />
            <strong>Drop a file here, or click to browse</strong>
            <span>MP3, WAV, M4A, MP4, WEBM, OGG, FLAC · max 4 MB on Vercel Hobby</span>
          </div>

          {file && (
            <div className="file-chip">
              {file.name}
              <span style={{ opacity: 0.7 }}>({formatBytes(file.size)})</span>
            </div>
          )}

          <div className="row">
            <div className="field">
              <label htmlFor="language">Language (optional)</label>
              <input
                id="language"
                placeholder="auto-detect · e.g. en, fr, ha"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
              />
            </div>
            <div className="field">
              <label>Provider status</label>
              <input
                readOnly
                value={
                  providerReady === null
                    ? "Checking…"
                    : providerReady
                      ? "API key configured"
                      : "Missing XAI_API_KEY (or Groq/OpenAI)"
                }
              />
            </div>
          </div>

          <button className="btn" disabled={busy || !file} onClick={onTranscribe}>
            {busy ? "Transcribing…" : "Transcribe"}
          </button>

          {error ? (
            <div className="status error">{error}</div>
          ) : (
            <div className={`status${result ? " ok" : ""}`}>{status}</div>
          )}

          <p className="note">
            Fully local / offline mode stays on the Python package (
            <code>video-transcriber</code> CLI + Gradio). This web deploy uses a
            hosted Whisper API so it fits Vercel’s serverless limits.
          </p>
        </section>

        <section className="card">
          <h2>2. Results</h2>

          {!result || !outputs ? (
            <p className="empty">
              Your transcript, SRT, VTT, and JSON will appear here after a successful
              run.
            </p>
          ) : (
            <>
              <div className="meta">
                {result.language && <span className="pill">lang: {result.language}</span>}
                {typeof result.duration === "number" && (
                  <span className="pill">{result.duration.toFixed(1)}s audio</span>
                )}
                {result.segments && (
                  <span className="pill">{result.segments.length} segments</span>
                )}
              </div>

              <div className="tabs">
                {(["txt", "srt", "vtt", "json"] as FormatKey[]).map((key) => (
                  <button
                    key={key}
                    className={`tab${activeTab === key ? " active" : ""}`}
                    onClick={() => setActiveTab(key)}
                    type="button"
                  >
                    {key.toUpperCase()}
                  </button>
                ))}
              </div>

              <textarea
                className="output"
                readOnly
                value={outputs[activeTab]}
                spellCheck={false}
              />

              <div className="actions">
                <button
                  className="ghost"
                  type="button"
                  onClick={() =>
                    navigator.clipboard.writeText(outputs[activeTab]).catch(() => undefined)
                  }
                >
                  Copy {activeTab.toUpperCase()}
                </button>
                <button
                  className="ghost"
                  type="button"
                  onClick={() =>
                    downloadText(
                      `${stem}.${activeTab}`,
                      outputs[activeTab],
                      activeTab === "json" ? "application/json" : "text/plain",
                    )
                  }
                >
                  Download .{activeTab}
                </button>
                <button
                  className="ghost"
                  type="button"
                  onClick={() => {
                    downloadText(`${stem}.txt`, outputs.txt, "text/plain");
                    downloadText(`${stem}.srt`, outputs.srt, "text/plain");
                    downloadText(`${stem}.vtt`, outputs.vtt, "text/vtt");
                    downloadText(`${stem}.json`, outputs.json, "application/json");
                  }}
                >
                  Download all
                </button>
              </div>
            </>
          )}
        </section>
      </div>

      <footer className="footer">
        Open source Python engine on GitHub · MIT · Built for local power + cloud
        convenience
      </footer>
    </main>
  );
}
