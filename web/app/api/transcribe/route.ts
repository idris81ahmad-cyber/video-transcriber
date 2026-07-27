import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const maxDuration = 60;

const MAX_BYTES = 25 * 1024 * 1024; // 25 MB

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

  // Prefer xAI when available (Grok Speech-to-Text)
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

/** Group word-level timestamps into subtitle-friendly segments. */
function wordsToSegments(words: Word[], gapThreshold = 0.6, maxDuration = 6): Segment[] {
  if (!words.length) return [];

  const segments: Segment[] = [];
  let bucket: Word[] = [];

  const flush = () => {
    if (!bucket.length) return;
    const start = bucket[0].start;
    const end = bucket[bucket.length - 1].end;
    const text = bucket.map((w) => w.text).join(" ").replace(/\s+/g, " ").trim();
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
  const outbound = new FormData();
  outbound.append("file", file, file.name || "audio.mp3");
  if (language) {
    outbound.append("language", language);
    outbound.append("format", "true");
  }

  const upstream = await fetch("https://api.x.ai/v1/stt", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
    },
    body: outbound,
  });

  const rawText = await upstream.text();
  let payload: unknown;
  try {
    payload = JSON.parse(rawText);
  } catch {
    payload = { error: rawText };
  }

  if (!upstream.ok) {
    const message =
      typeof payload === "object" &&
      payload &&
      "error" in payload &&
      typeof (payload as { error?: { message?: string } | string }).error === "object"
        ? (payload as { error?: { message?: string } }).error?.message
        : typeof payload === "object" &&
            payload &&
            "error" in payload &&
            typeof (payload as { error?: string }).error === "string"
          ? (payload as { error: string }).error
          : `xAI STT error (${upstream.status})`;
    throw Object.assign(new Error(message || `Transcription failed (${upstream.status})`), {
      status: upstream.status >= 400 && upstream.status < 600 ? upstream.status : 502,
    });
  }

  const data = payload as {
    text?: string;
    language?: string;
    duration?: number;
    words?: Word[];
  };

  const words = data.words || [];
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
  const outbound = new FormData();
  outbound.append("file", file, file.name || "audio.mp3");
  outbound.append("model", model);
  outbound.append("response_format", "verbose_json");
  if (provider === "openai") {
    outbound.append("timestamp_granularities[]", "segment");
  }
  if (language) {
    outbound.append("language", language);
  }

  const upstream = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
    },
    body: outbound,
  });

  const rawText = await upstream.text();
  let payload: unknown;
  try {
    payload = JSON.parse(rawText);
  } catch {
    payload = { error: rawText };
  }

  if (!upstream.ok) {
    const message =
      typeof payload === "object" &&
      payload &&
      "error" in payload &&
      typeof (payload as { error?: { message?: string } | string }).error === "object"
        ? (payload as { error?: { message?: string } }).error?.message
        : typeof payload === "object" &&
            payload &&
            "error" in payload &&
            typeof (payload as { error?: string }).error === "string"
          ? (payload as { error: string }).error
          : `Upstream ${provider} error (${upstream.status})`;
    throw Object.assign(new Error(message || `Transcription failed (${upstream.status})`), {
      status: upstream.status >= 400 && upstream.status < 600 ? upstream.status : 502,
    });
  }

  const data = payload as {
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

    const form = await req.formData();
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
        { error: `File too large (max ${MAX_BYTES / (1024 * 1024)} MB on this plan).` },
        { status: 413 },
      );
    }

    const result =
      provider === "xai"
        ? await transcribeWithXai(file, apiKey, language)
        : await transcribeOpenAiCompatible(
            file,
            apiKey,
            url,
            model,
            provider,
            language,
          );

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
  });
}
