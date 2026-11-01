// Dependency-free SVG charts. Text alternatives are provided for screen readers.
export function RatingChart({ points }: { points: { rating: number; label: string }[] }) {
  if (points.length < 2) return <p className="text-sm text-muted">Rating history appears after your first rated contests.</p>;
  const W = 520, H = 160, P = 24;
  const lo = Math.min(...points.map((p) => p.rating)) - 40, hi = Math.max(...points.map((p) => p.rating)) + 40;
  const x = (i: number) => P + (i * (W - 2 * P)) / (points.length - 1);
  const y = (r: number) => H - P - ((r - lo) / (hi - lo)) * (H - 2 * P);
  const d = points.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.rating).toFixed(1)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Rating history from ${points[0].rating} to ${points.at(-1)!.rating}`} className="w-full">
      <path d={d} fill="none" stroke="rgb(var(--violet))" strokeWidth="2" />
      {points.map((p, i) => <circle key={i} cx={x(i)} cy={y(p.rating)} r="3" fill="rgb(var(--cyan))"><title>{`${p.label}: ${p.rating}`}</title></circle>)}
      <text x={P} y={12} className="fill-muted text-[10px]">{hi}</text>
      <text x={P} y={H - 6} className="fill-muted text-[10px]">{lo}</text>
    </svg>
  );
}

export function Heatmap({ activity, weeks = 26 }: { activity: Record<string, number>; weeks?: number }) {
  const days: { date: string; n: number }[] = [];
  const end = new Date();
  for (let i = weeks * 7 - 1; i >= 0; i--) {
    const d = new Date(end); d.setDate(end.getDate() - i);
    const key = d.toISOString().slice(0, 10);
    days.push({ date: key, n: activity[key] ?? 0 });
  }
  const total = days.reduce((a, d) => a + d.n, 0);
  return (
    <figure>
      <svg viewBox={`0 0 ${weeks * 13} 91`} className="w-full" role="img" aria-label={`${total} submissions in the last ${weeks} weeks`}>
        {days.map((d, i) => {
          return (
            <rect key={d.date} x={Math.floor(i / 7) * 13} y={(i % 7) * 13} width="10" height="10" rx="2"
              style={{ fill: d.n === 0 ? "rgb(var(--raised))" : `rgb(var(--violet) / ${d.n < 2 ? 0.35 : d.n < 4 ? 0.65 : 1})` }}>
              <title>{`${d.date}: ${d.n} submission${d.n === 1 ? "" : "s"}`}</title>
            </rect>
          );
        })}
      </svg>
    </figure>
  );
}

export function Bars({ data, colors }: { data: Record<string, number>; colors?: Record<string, string> }) {
  const max = Math.max(1, ...Object.values(data));
  return (
    <ul className="space-y-2">
      {Object.entries(data).map(([k, v]) => (
        <li key={k} className="flex items-center gap-3 text-sm">
          <span className="w-20 capitalize text-muted">{k}</span>
          <span className="h-2 flex-1 overflow-hidden rounded bg-raised"><span className={`block h-full rounded ${colors?.[k] ?? "bg-violet"}`} style={{ width: `${(v / max) * 100}%` }} /></span>
          <span className="w-8 text-right tabular-nums">{v}</span>
        </li>
      ))}
    </ul>
  );
}
