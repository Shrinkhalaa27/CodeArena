export function timeUntil(iso: string, now = Date.now()): string {
  let s = Math.max(0, Math.floor((new Date(iso).getTime() - now) / 1000));
  const d = Math.floor(s / 86400); s -= d * 86400;
  const h = Math.floor(s / 3600); s -= h * 3600;
  const m = Math.floor(s / 60); s -= m * 60;
  return d > 0 ? `${d}d ${h}h ${m}m` : `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}
export const fmtDate = (iso: string) => new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
export const VERDICT_LABEL: Record<string, string> = {
  QUEUED: "Queued", COMPILING: "Compiling", RUNNING: "Running", ACCEPTED: "Accepted", WRONG_ANSWER: "Wrong Answer",
  TIME_LIMIT_EXCEEDED: "Time Limit Exceeded", MEMORY_LIMIT_EXCEEDED: "Memory Limit Exceeded",
  RUNTIME_ERROR: "Runtime Error", COMPILATION_ERROR: "Compilation Error", INTERNAL_ERROR: "Judge Error",
};
export const isFinal = (s: string) => !["QUEUED", "COMPILING", "RUNNING"].includes(s);
