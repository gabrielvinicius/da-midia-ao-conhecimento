// Horários da gravação: na tela (mm:ss), em legendas SRT e WebVTT.

const pad = (value: number, size = 2) => String(value).padStart(size, "0");

/** 75 → "01:15"; 3725 → "1:02:05". */
export const formatClock = (seconds: number | null | undefined): string => {
  if (seconds == null || !Number.isFinite(seconds)) return "";
  const s = Math.max(0, Math.floor(seconds));
  const clock = `${pad(Math.floor((s % 3600) / 60))}:${pad(s % 60)}`;
  return s >= 3600 ? `${Math.floor(s / 3600)}:${clock}` : clock;
};

const legendTime = (seconds: number, separator: "," | ".") => {
  const ms = Math.max(0, Math.round(seconds * 1000));
  const h = Math.floor(ms / 3_600_000);
  const m = Math.floor((ms % 3_600_000) / 60_000);
  const s = Math.floor((ms % 60_000) / 1000);
  return `${pad(h)}:${pad(m)}:${pad(s)}${separator}${pad(ms % 1000, 3)}`;
};

/** 75.5 → "00:01:15,500" (SRT). */
export const srtTime = (seconds: number) => legendTime(seconds, ",");

/** 75.5 → "00:01:15.500" (WebVTT). */
export const vttTime = (seconds: number) => legendTime(seconds, ".");

/** "1:02:05", "02:05" ou "125" → segundos; null se não for um horário. */
export const parseClock = (value: string): number | null => {
  const parts = value.trim().split(":").map(Number);
  if (!parts.length || parts.some((p) => !Number.isFinite(p) || p < 0)) return null;
  return parts.reduce((total, part) => total * 60 + part, 0);
};
