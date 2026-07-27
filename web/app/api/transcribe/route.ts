import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const maxDuration = 60;

const MAX_BYTES = 25 * 1024 * 1024; // 25 MB

type Provider = "groq" | "openai";

function resolveProvider(): { provider: Provider; apiKey: string; model: string; url: string } {
  const groqKey = process.env.GROQ_API_KEY?.trim();
  const openaiKey = process.env.OPENAI_API_KEY?.trim();
  const modelOverride = process.env.WHISPER_MODEL?.trim();

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
    "Missing API key. Set GROQ_API_KEY or OPENAI_API_KEY in your Vercel project environment.",
  );
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

    const outbound = new FormData();
    outbound.append("file", file, file.name || "audio.mp3");
    outbound.append("model", model);
    outbound.append("response_format", "verbose_json");
    // OpenAI supports timestamp_granularities; Groq is fine without it
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

      return NextResponse.json(
        { error: message || `Transcription failed (${upstream.status})` },
        { status: upstream.status >= 400 && upstream.status < 600 ? upstream.status : 502 },
      );
    }

    const data = payload as {
      text?: string;
      language?: string;
      duration?: number;
      segments?: Array<{ id?: number; start: number; end: number; text: string }>;
    };

    return NextResponse.json({
      provider,
      model,
      text: data.text || "",
      language: data.language,
      duration: data.duration,
      segments: (data.segments || []).map((s, i) => ({
        id: s.id ?? i,
        start: s.start,
        end: s.end,
        text: s.text,
      })),
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unexpected server error";
    const status = message.includes("Missing API key") ? 503 : 500;
    return NextResponse.json({ error: message }, { status });
  }
}

export async function GET() {
  const hasGroq = Boolean(process.env.GROQ_API_KEY?.trim());
  const hasOpenAI = Boolean(process.env.OPENAI_API_KEY?.trim());
  return NextResponse.json({
    ok: hasGroq || hasOpenAI,
    providers: {
      groq: hasGroq,
      openai: hasOpenAI,
    },
  });
}
