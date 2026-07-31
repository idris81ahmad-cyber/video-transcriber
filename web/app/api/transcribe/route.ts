import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const maxDuration = 60;

/** Vercel serverless request body limit is ~4.5 MB on Hobby. */
const MAX_BYTES = 4 * 1024 * 1024;

type Provider = "xai" | "groq" | "openai";

type Word = {
  text: string;
  start: number;
  end: number;
  confidence?: number;
  speaker?: number;
};

type Segment = {
  id: number;
  start: number;
  end: number;
  text: string;
  speaker?: string;
};

function resolveProvider(): {
  provider: Provider;
  apiKey: string;
  model: string;
  url: string;
} {
  const xaiKey = process.env.XAI_API_KEY?.trim();
  const groqKey = process.env.GROQ_API_KEY?.trim();
  const openaiKey = process.env.OPENAI_API_KEY?.trim();
  const modelOverride = process.env.WHISPER_MODEL?.trim();

  if (xaiKey) {
    return {
      provider: "xai",
      apiKey: xaiKey,
      model: modelOverride || "grok-stt",
      url: "https://api.x.ai/v1/stt",
    };
  }

  if (groqKey) {
    return {
      provider: "groq",
      apiKey: groqKey,
      model: modelOverride || "whisper-large-v3",
      url: "https://api.groq.com/openai/v1/audio/transcriptions",
    };
  }

  if (openaiKey) {
    return {
      provider: "openai",
      apiKey: openaiKey,
      model: modelOverride || "whisper-1",
      url: "https://api.openai.com/v1/audio/transcriptions",
    };
  }

  throw new Error(
    "Missing API key. Set XAI_API_KEY, GROQ_API_KEY, or OPENAI_API_KEY in your Vercel project environment.",
  );
}

function wordsToSegments(words: Word[], gapThreshold = 0.6, maxDuration = 6): Segment[] {
  if (!words.length) return [];

  const segments: Segment[] = [];
  let bucket: Word[] = [];

  const flush = () => {
    if (!bucket.length) return;
    const start = bucket[0].start;
    const end = bucket[bucket.length - 1].end;
    const text = bucket
      .map((w) => w.text)
      .join(" ")
      .replace(/\s+/g, " ")
      .trim();
    const speaker =
      typeof bucket[0].speaker === "number" ? `SPEAKER_${bucket[0].speaker}` : undefined;
    if (text) {
      segments.push({
        id: segments.length,
        start,
        end,
        text,
        speaker,
      });
    }
    bucket = [];
  };

  for (const word of words) {
    if (!bucket.length) {
      bucket.push(word);
      continue;
    }
    const prev = bucket[bucket.length - 1];
    const gap = word.start - prev.end;
    const span = word.end - bucket[0].start;
    const speakerChanged =
      typeof word.speaker === "number" &&
      typeof prev.speaker === "number" &&
      word.speaker !== prev.speaker;

    if (speakerChanged || gap >= gapThreshold || span >= maxDuration) {
      flush();
    }
    bucket.push(word);
  }
  flush();
  return segments;
}

function extractErrorMessage(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== "object") return fallback;

  const obj = payload as Record<string, unknown>;

  if (typeof obj.error === "string" && obj.error.trim()) return obj.error;
  if (obj.error && typeof obj.error === "object") {
    const err = obj.error as Record<string, unknown>;
    if (typeof err.message === "string" && err.message.trim()) return err.message;
  }
  if (typeof obj.message === "string" && obj.message.trim()) return obj.message;
  if (typeof obj.detail === "string" && obj.detail.trim()) return obj.detail;

  return fallback;
}

async function parseUpstreamJson(
  res: Response,
): Promise<{ ok: true; data: unknown } | { ok: false; status: number; message: string }> {
  const contentType = res.headers.get("content-type") || "";
  const rawText = await res.text();

  if (!rawText.trim()) {
    return {
      ok: false,
      status: res.status || 502,
      message: `Empty response from speech API (${res.status || "no status"}).`,
    };
  }

  let data: unknown;
  try {
    data = JSON.parse(rawText);
  } catch {
    // Upstream sometimes returns plain text / HTML (auth walls, 413, gateway errors)
    const snippet = rawText.replace(/\s+/g, " ").slice(0, 240);
    return {
      ok: false,
      status: res.status || 502,
      message: `Speech API returned non-JSON (${res.status}). ${snippet}`,
    };
  }

  if (!res.ok) {
    return {
      ok: false,
      status: res.status >= 400 && res.status < 600 ? res.status : 502,
      message: extractErrorMessage(data, `Speech API error (${res.status})`),
    };
  }

  return { ok: true, data };
}

/** Build a real Blob so Node fetch multipart encoding is reliable. */
async function fileToBlob(file: File): Promise<{ blob: Blob; filename: string }> {
  const bytes = await file.arrayBuffer();
  const type = file.type || "application/octet-stream";
  const filename = file.name || "audio.mp3";
  return { blob: new Blob([bytes], { type }), filename };
}

async function transcribeWithXai(
  file: File,
  apiKey: string,
  language: string,
): Promise<{
  text: string;
  language?: string;
  duration?: number;
  segments: Segment[];
}> {
  const { blob, filename } = await fileToBlob(file);

  // xAI requires non-file fields BEFORE `file` (file must be last).
  const outbound = new FormData();
  if (language) {
    outbound.append("language", language);
    outbound.append("format", "true");
  }
  outbound.append("file", blob, filename);

  const upstream = await fetch("https://api.x.ai/v1/stt", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
    },
    body: outbound,
  });

  const parsed = await parseUpstreamJson(upstream);
  if (!parsed.ok) {
    throw Object.assign(new Error(parsed.message), { status: parsed.status });
  }

  const data = parsed.data as {
    text?: string;
    language?: string;
    duration?: number;
    words?: Word[];
  };

  const words = Array.isArray(data.words) ? data.words : [];
  const segments = wordsToSegments(words);

  return {
    text: data.text || segments.map((s) => s.text).join(" ") || "",
    language: data.language || language || undefined,
    duration: data.duration,
    segments:
      segments.length > 0
        ? segments
        : data.text
          ? [{ id: 0, start: 0, end: data.duration || 0, text: data.text }]
          : [],
  };
}

async function transcribeOpenAiCompatible(
  file: File,
  apiKey: string,
  url: string,
  model: string,
  provider: "groq" | "openai",
  language: string,
): Promise<{
  text: string;
  language?: string;
  duration?: number;
  segments: Segment[];
}> {
  const { blob, filename } = await fileToBlob(file);

  const outbound = new FormData();
  outbound.append("model", model);
  outbound.append("response_format", "verbose_json");
  if (provider === "openai") {
    outbound.append("timestamp_granularities[]", "segment");
  }
  if (language) {
    outbound.append("language", language);
  }
  // file last for consistency
  outbound.append("file", blob, filename);

  const upstream = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
    },
    body: outbound,
  });

  const parsed = await parseUpstreamJson(upstream);
  if (!parsed.ok) {
    throw Object.assign(new Error(parsed.message), { status: parsed.status });
  }

  const data = parsed.data as {
    text?: string;
    language?: string;
    duration?: number;
    segments?: Array<{ id?: number; start: number; end: number; text: string }>;
  };

  return {
    text: data.text || "",
    language: data.language,
    duration: data.duration,
    segments: (data.segments || []).map((s, i) => ({
      id: s.id ?? i,
      start: s.start,
      end: s.end,
      text: s.text,
    })),
  };
}

export async function POST(req: NextRequest) {
  try {
    const { provider, apiKey, model, url } = resolveProvider();

    let form: FormData;
    try {
      form = await req.formData();
    } catch {
      return NextResponse.json(
        {
          error:
            "Could not read upload body. On Vercel Hobby the max request size is ~4.5 MB — try a shorter/smaller audio file.",
        },
        { status: 413 },
      );
    }

    const file = form.get("file");
    const language = String(form.get("language") || "").trim();

    if (!(file instanceof File)) {
      return NextResponse.json({ error: "No media file uploaded." }, { status: 400 });
    }

    if (file.size <= 0) {
      return NextResponse.json({ error: "Empty file." }, { status: 400 });
    }

    if (file.size > MAX_BYTES) {
      return NextResponse.json(
        {
          error: `File too large for this Vercel function (${(file.size / (1024 * 1024)).toFixed(1)} MB). Keep under ${MAX_BYTES / (1024 * 1024)} MB, or compress the audio.`,
        },
        { status: 413 },
      );
    }

    const result =
      provider === "xai"
        ? await transcribeWithXai(file, apiKey, language)
        : await transcribeOpenAiCompatible(file, apiKey, url, model, provider, language);

    if (!result.text?.trim() && !result.segments?.length) {
      return NextResponse.json(
        {
          error:
            "Speech API returned an empty transcript. Try another file, or set language to en.",
        },
        { status: 502 },
      );
    }

    return NextResponse.json({
      provider,
      model,
      text: result.text,
      language: result.language,
      duration: result.duration,
      segments: result.segments,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unexpected server error";
    const status =
      err && typeof err === "object" && "status" in err && typeof err.status === "number"
        ? err.status
        : message.includes("Missing API key")
          ? 503
          : 500;
    return NextResponse.json({ error: message }, { status });
  }
}

export async function GET() {
  const hasXai = Boolean(process.env.XAI_API_KEY?.trim());
  const hasGroq = Boolean(process.env.GROQ_API_KEY?.trim());
  const hasOpenAI = Boolean(process.env.OPENAI_API_KEY?.trim());
  return NextResponse.json({
    ok: hasXai || hasGroq || hasOpenAI,
    providers: {
      xai: hasXai,
      groq: hasGroq,
      openai: hasOpenAI,
    },
    limits: {
      maxUploadMb: MAX_BYTES / (1024 * 1024),
    },
  });
}
