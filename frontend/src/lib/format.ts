/* Tiny formatting helpers ported from the Daybreak prototype's `bn` object. */

export function cls(...c: Array<string | false | null | undefined>): string {
  return c.filter(Boolean).join(" ");
}

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");
}

export function formatMoney(n: number, currency = "USD"): string {
  return `${currency === "USD" ? "$" : currency + " "}${n.toLocaleString()}`;
}

export function daysBetween(a: string | Date, b: string | Date): number {
  const da = new Date(a);
  const db = new Date(b);
  return Math.round((db.getTime() - da.getTime()) / (1000 * 60 * 60 * 24)) + 1;
}

export function pluralize(n: number, s: string): string {
  return `${n} ${s}${n === 1 ? "" : "s"}`;
}

export function fmtDate(s?: string | Date | null): string {
  if (!s) return "";
  return new Date(s).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function fmtDateShort(s?: string | Date | null): string {
  if (!s) return "";
  return new Date(s).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

export function fmtDateRange(a: string | Date, b: string | Date): string {
  const da = new Date(a);
  const db = new Date(b);
  if (da.getMonth() === db.getMonth() && da.getFullYear() === db.getFullYear()) {
    return `${da.toLocaleDateString("en-GB", { day: "numeric" })} – ${db.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}`;
  }
  return `${fmtDate(a)} – ${fmtDate(b)}`;
}

/* Stable colour token chosen from a string. */
const AV_PALETTE = ["av-1", "av-2", "av-3", "av-4", "av-5", "av-6", "av-7", "av-8"];

export function avFrom(s: string): string {
  let h = 0;
  for (const ch of s) h = (h * 31 + ch.charCodeAt(0)) | 0;
  return AV_PALETTE[Math.abs(h) % AV_PALETTE.length];
}
