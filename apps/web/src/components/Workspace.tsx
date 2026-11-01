"use client";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, getTokens } from "@/lib/api";
import { isFinal } from "@/lib/format";
import { useApi, useUser } from "@/lib/hooks";
import type { AiResponse, ProblemDetail, RunResult, Submission } from "@/lib/types";
import { DifficultyBadge, ErrorState, RichText, Skeleton, VerdictBadge } from "./ui";

const Editor = dynamic(() => import("./MonacoEditor"), {
  ssr: false,
  loading: () => <div className="skeleton h-full min-h-[320px] w-full" aria-label="Loading editor" />,
});

const MONACO_LANG: Record<string, string> = { python: "python", cpp: "cpp", java: "java", javascript: "javascript" };
const LANG_LABEL: Record<string, string> = { python: "Python 3", cpp: "C++17", java: "Java", javascript: "JavaScript" };
type Tab = "statement" | "code";
type ConsoleTab = "console" | "verdict" | "history" | "ai";

export function Workspace({ slug, contestId, contestSlug }: { slug: string; contestId?: string; contestSlug?: string }) {
  const { data: problem, error, loading, reload } = useApi<ProblemDetail>(`/problems/${slug}`);
  const { user, ready } = useUser();
  const [lang, setLang] = useState("python");
  const [code, setCode] = useState("");
  const [fontSize, setFontSize] = useState(14);
  const [stdin, setStdin] = useState("");
  const [tab, setTab] = useState<Tab>("statement");
  const [consoleTab, setConsoleTab] = useState<ConsoleTab>("console");
  const [run, setRun] = useState<RunResult | null>(null);
  const [running, setRunning] = useState(false);
  const [sub, setSub] = useState<Submission | null>(null);
  const [history, setHistory] = useState<Submission[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [split, setSplit] = useState(42);
  const [ai, setAi] = useState<{ enabled: boolean } | null>(null);
  const [aiText, setAiText] = useState<AiResponse | null>(null);
  const [aiBusy, setAiBusy] = useState(false);
  const polling = useRef<ReturnType<typeof setTimeout> | null>(null);

  // load draft or starter template for the chosen language
  useEffect(() => {
    if (!problem) return;
    let saved: string | null = null;
    try { saved = localStorage.getItem(`codearena.draft.${slug}.${lang}`); } catch { /* ignore */ }
    setCode(saved ?? problem.templates[lang] ?? "");
    if (!stdin && problem.samples[0]) setStdin(problem.samples[0].input);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [problem, lang, slug]);

  useEffect(() => {
    if (!problem || !code) return;
    const t = setTimeout(() => { try { localStorage.setItem(`codearena.draft.${slug}.${lang}`, code); } catch { /* ignore */ } }, 400);
    return () => clearTimeout(t);
  }, [code, slug, lang, problem]);

  useEffect(() => { api<{ enabled: boolean }>("/ai/status").then(setAi).catch(() => setAi({ enabled: false })); }, []);

  const loadHistory = useCallback(async () => {
    if (!problem || !getTokens()) return;
    try { setHistory(await api<Submission[]>(`/submissions?problem_id=${problem.id}&limit=15`)); } catch { /* shown empty */ }
  }, [problem]);
  useEffect(() => { void loadHistory(); }, [loadHistory, user]);
  useEffect(() => () => { if (polling.current) clearTimeout(polling.current); }, []);

  const resetCode = () => { if (problem) setCode(problem.templates[lang] ?? ""); };
  const needLogin = ready && !user;

  async function onRun() {
    if (!problem) return;
    setMsg(null); setRunning(true); setConsoleTab("console");
    try { setRun(await api<RunResult>("/run", { method: "POST", json: { language: lang, source_code: code, stdin, problem_id: problem.id } })); }
    catch (e) { setMsg((e as ApiError).message); setRun(null); }
    finally { setRunning(false); }
  }

  async function onSubmit() {
    if (!problem) return;
    setMsg(null); setConsoleTab("verdict");
    try {
      const created = await api<{ submission_id: string; status: Submission["status"] }>("/submissions", {
        method: "POST", headers: { "Idempotency-Key": crypto.randomUUID() },
        json: { problem_id: problem.id, language: lang, source_code: code, contest_id: contestId ?? null },
      });
      setSub({ id: created.submission_id, status: created.status } as Submission);
      const poll = async () => {
        try {
          const s = await api<Submission>(`/submissions/${created.submission_id}`);
          setSub(s);
          if (isFinal(s.status)) { void loadHistory(); return; }
        } catch (e) { setMsg((e as ApiError).message); return; }
        polling.current = setTimeout(poll, 800); // polling fallback; WS endpoint also available
      };
      void poll();
    } catch (e) { setMsg((e as ApiError).message); }
  }

  async function onAi(kind: "hint" | "explain") {
    if (!problem) return;
    setAiBusy(true); setMsg(null); setConsoleTab("ai");
    try { setAiText(await api<AiResponse>(`/ai/${kind}`, { method: "POST", json: { problem_id: problem.id, code: kind === "explain" ? code : null, level: 1 } })); }
    catch (e) { setMsg((e as ApiError).message); }
    finally { setAiBusy(false); }
  }

  const drag = (e: React.PointerEvent) => {
    const el = e.currentTarget.parentElement!;
    const move = (ev: PointerEvent) => { const r = el.getBoundingClientRect(); setSplit(Math.min(70, Math.max(25, ((ev.clientX - r.left) / r.width) * 100))); };
    const up = () => { window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up); };
    window.addEventListener("pointermove", move); window.addEventListener("pointerup", up);
  };

  if (loading) return <Skeleton rows={8} />;
  if (error || !problem) return <ErrorState error={error ?? new ApiError(404, "NOT_FOUND", "Problem not found.")} retry={reload} />;

  const statement = (
    <article className="prose-problem space-y-5 overflow-y-auto p-5 text-sm" aria-label="Problem statement">
      <header>
        <h1 className="text-xl font-semibold">{problem.title}</h1>
        <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-muted">
          <DifficultyBadge level={problem.difficulty} />
          <span>{problem.time_limit_ms} ms</span><span>{Math.round(problem.memory_limit_kb / 1024)} MB</span>
          {problem.tags.map((t) => <span key={t} className="rounded bg-raised px-2 py-0.5">{t}</span>)}
        </div>
      </header>
      {/* Statement is rendered as plain text, never as HTML: no XSS surface. */}
      <RichText text={problem.statement} />
      {problem.input_format && <section><h2 className="mb-1 font-semibold">Input</h2><RichText text={problem.input_format} /></section>}
      {problem.output_format && <section><h2 className="mb-1 font-semibold">Output</h2><RichText text={problem.output_format} /></section>}
      {problem.constraints && <section><h2 className="mb-1 font-semibold">Constraints</h2><p className="font-mono text-xs">{problem.constraints}</p></section>}
      {problem.samples.map((s, i) => (
        <section key={i}>
          <h2 className="mb-1 font-semibold">Example {i + 1}</h2>
          <div className="grid gap-2 sm:grid-cols-2">
            <pre className="overflow-x-auto rounded bg-raised p-3 font-mono text-xs"><span className="mb-1 block text-muted">Input</span>{s.input}</pre>
            <pre className="overflow-x-auto rounded bg-raised p-3 font-mono text-xs"><span className="mb-1 block text-muted">Output</span>{s.expected_output}</pre>
          </div>
        </section>
      ))}
    </article>
  );

  const editor = (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex flex-wrap items-center gap-2 border-b border-line p-2">
        <label className="sr-only" htmlFor="lang">Language</label>
        <select id="lang" className="input !w-auto" value={lang} onChange={(e) => setLang(e.target.value)} data-testid="language">
          {problem.languages.map((l) => <option key={l} value={l}>{LANG_LABEL[l] ?? l}</option>)}
        </select>
        <button className="btn btn-ghost" onClick={() => setFontSize((s) => Math.max(11, s - 1))} aria-label="Decrease font size">A−</button>
        <button className="btn btn-ghost" onClick={() => setFontSize((s) => Math.min(22, s + 1))} aria-label="Increase font size">A+</button>
        <button className="btn btn-ghost" onClick={resetCode}>Reset</button>
        <button className="btn btn-ghost" onClick={() => navigator.clipboard?.writeText(code)}>Copy</button>
      </div>
      <div className="min-h-[320px] flex-1" data-testid="editor">
        <Editor height="100%" language={MONACO_LANG[lang]} value={code} theme="vs-dark" onChange={(v) => setCode(v ?? "")}
          options={{ fontSize, minimap: { enabled: false }, scrollBeyondLastLine: false, automaticLayout: true, tabSize: 4, ariaLabel: "Code editor" }} />
      </div>
      <div className="border-t border-line">
        <div role="tablist" className="flex items-center gap-1 border-b border-line px-2 pt-1">
          {(["console", "verdict", "history", ...(ai?.enabled ? ["ai"] : [])] as ConsoleTab[]).map((t) => (
            <button key={t} role="tab" aria-selected={consoleTab === t} onClick={() => setConsoleTab(t)}
              className={`rounded-t px-3 py-1.5 text-xs capitalize ${consoleTab === t ? "bg-raised text-ink" : "text-muted"}`}>{t === "ai" ? "AI help" : t}</button>
          ))}
          <div className="ml-auto flex gap-2 pb-1">
            <button className="btn btn-ghost !py-1" onClick={onRun} disabled={running || needLogin} data-testid="run">{running ? "Running…" : "Run"}</button>
            <button className="btn btn-primary !py-1" onClick={onSubmit} disabled={needLogin} data-testid="submit">Submit</button>
          </div>
        </div>
        <div className="h-52 overflow-y-auto p-3 text-sm" role="tabpanel">
          {needLogin && <p className="mb-2 rounded bg-raised p-2 text-xs">Please <Link className="text-cyan underline" href="/login">sign in</Link> to run or submit code.</p>}
          {msg && <p role="alert" className="mb-2 text-xs text-bad">{msg}</p>}
          {consoleTab === "console" && (
            <div className="space-y-2">
              <label className="text-xs text-muted" htmlFor="stdin">Custom input</label>
              <textarea id="stdin" className="input h-16 font-mono text-xs" value={stdin} onChange={(e) => setStdin(e.target.value)} />
              {run && (
                <div>
                  <p className="text-xs text-muted">Status: {run.status}{run.runtime_ms != null && ` · ${run.runtime_ms} ms`}</p>
                  {/* program output is untrusted text; React escapes it */}
                  <pre className="mt-1 whitespace-pre-wrap rounded bg-raised p-2 font-mono text-xs">{run.compile_output || run.stdout || "(no output)"}</pre>
                </div>
              )}
            </div>
          )}
          {consoleTab === "verdict" && (!sub ? <p className="text-muted">Submit your solution to see the verdict.</p> : (
            <div className="space-y-2">
              <VerdictBadge status={sub.status} />
              {isFinal(sub.status) && (
                <p className="text-xs text-muted">Passed {sub.passed_tests}/{sub.total_tests} tests{sub.runtime_ms != null && ` · ${sub.runtime_ms} ms`}{sub.memory_kb != null && ` · ${(sub.memory_kb / 1024).toFixed(1)} MB`}</p>
              )}
              {sub.status === "INTERNAL_ERROR" && <p className="text-xs text-muted">The judge had a problem — this is not your code&apos;s fault. Try submitting again.</p>}
              {sub.compile_output && <pre className="whitespace-pre-wrap rounded bg-raised p-2 font-mono text-xs">{sub.compile_output}</pre>}
            </div>
          ))}
          {consoleTab === "history" && (history.length === 0 ? <p className="text-muted">No submissions yet.</p> : (
            <table className="w-full text-xs"><thead className="text-left text-muted"><tr><th>When</th><th>Lang</th><th>Verdict</th><th>Tests</th></tr></thead>
              <tbody>{history.map((h) => <tr key={h.id} className="border-t border-line"><td className="py-1.5">{new Date(h.created_at).toLocaleTimeString()}</td><td>{h.language}</td><td><VerdictBadge status={h.status} /></td><td>{h.passed_tests}/{h.total_tests}</td></tr>)}</tbody></table>
          ))}
          {consoleTab === "ai" && (
            <div className="space-y-2">
              <div className="flex gap-2">
                <button className="btn btn-ghost" disabled={aiBusy || needLogin} onClick={() => onAi("hint")}>Get a hint</button>
                <button className="btn btn-ghost" disabled={aiBusy || needLogin || !code} onClick={() => onAi("explain")}>Explain my code</button>
              </div>
              <p className="text-xs text-muted">Only the public statement{" "}(and your code, when you press Explain) is sent to the AI provider.</p>
              {aiBusy && <p className="text-xs text-muted">Thinking…</p>}
              {aiText && <div><p className="whitespace-pre-wrap">{aiText.text}</p><p className="mt-2 text-xs text-warn">{aiText.disclaimer} · {aiText.remaining_quota} left today</p></div>}
            </div>
          )}
        </div>
      </div>
    </div>
  );

  return (
    <div className="-mx-4 -my-8">
      {contestSlug && <div className="border-b border-line bg-raised px-4 py-2 text-xs">Contest mode · <Link className="text-cyan" href={`/contests/${contestSlug}`}>back to contest</Link> · <Link className="text-cyan" href={`/contests/${contestSlug}/leaderboard`}>scoreboard</Link></div>}
      {/* mobile: statement/editor become tabs */}
      <div role="tablist" className="flex border-b border-line lg:hidden">
        {(["statement", "code"] as Tab[]).map((t) => <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)} className={`flex-1 py-2 text-sm capitalize ${tab === t ? "border-b-2 border-violet" : "text-muted"}`}>{t}</button>)}
      </div>
      <div className="hidden h-[calc(100vh-3.5rem)] lg:flex">
        <div style={{ width: `${split}%` }} className="flex flex-col overflow-hidden">{statement}</div>
        <div role="separator" aria-orientation="vertical" aria-label="Resize panels" tabIndex={0} onPointerDown={drag}
          onKeyDown={(e) => { if (e.key === "ArrowLeft") setSplit((s) => Math.max(25, s - 3)); if (e.key === "ArrowRight") setSplit((s) => Math.min(70, s + 3)); }}
          className="w-1.5 cursor-col-resize bg-line hover:bg-violet" />
        <div className="flex min-w-0 flex-1 flex-col border-l border-line">{editor}</div>
      </div>
      <div className="lg:hidden">{tab === "statement" ? statement : <div className="flex min-h-[70vh] flex-col">{editor}</div>}</div>
    </div>
  );
}
