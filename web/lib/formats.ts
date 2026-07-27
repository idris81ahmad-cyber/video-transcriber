export type Segment = {
  id?: number;
  start: number;
  end: number;
  text: string;
};

export type TranscriptResult = {
  text: string;
  language?: string;
  duration?: number;
  segments?: Segment[];
};

function pad(n: number, width = 2): string {
  return String(n).padStart(width, "0");
}

/** Format seconds → SRT/VTT timestamp */
export function formatTimestamp(
  seconds: number,
  decimalMarker: "," | "." = ",",
): string {
  if (!Number.isFinite(seconds) || seconds < 0) seconds = 0;
  const totalMs = Math.round(seconds * 1000);
  const hours = Math.floor(totalMs / 3_600_000);
  const minutes = Math.floor((totalMs % 3_600_000) / 60_000);
  const secs = Math.floor((totalMs % 60_000) / 1000);
  const ms = totalMs % 1000;
  return `${pad(hours)}:${pad(minutes)}:${pad(secs)}${decimalMarker}${pad(ms, 3)}`;
}

export function toTxt(result: TranscriptResult): string {
  if (result.segments?.length) {
    return result.segments
      .map((s) => s.text.trim())
      .filter(Boolean)
      .join("\n");
  }
  return (result.text || "").trim();
}

export function toSrt(result: TranscriptResult): string {
  const segments = result.segments?.length
    ? result.segments
    : [{ start: 0, end: result.duration || 0, text: result.text || "" }];

  return segments
    .map((seg, i) => {
      const text = seg.text.trim();
      if (!text) return "";
      const start = formatTimestamp(seg.start, ",");
      const end = formatTimestamp(seg.end, ",");
      return `${i + 1}\n${start} --> ${end}\n${text}\n`;
    })
    .filter(Boolean)
    .join("\n");
}

export function toVtt(result: TranscriptResult): string {
  const segments = result.segments?.length
    ? result.segments
    : [{ start: 0, end: result.duration || 0, text: result.text || "" }];

  const body = segments
    .map((seg) => {
      const text = seg.text.trim();
      if (!text) return "";
      const start = formatTimestamp(seg.start, ".");
      const end = formatTimestamp(seg.end, ".");
      return `${start} --> ${end}\n${text}\n`;
    })
    .filter(Boolean)
    .join("\n");

  return `WEBVTT\n\n${body}`;
}

export function toJson(result: TranscriptResult): string {
  return JSON.stringify(result, null, 2);
}
