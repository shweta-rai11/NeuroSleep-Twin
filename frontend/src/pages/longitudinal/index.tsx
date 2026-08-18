import { useEffect, useState } from "react";

import { api } from "@/api/client";
import { Card } from "@/components/layout/Card";
import type { LongitudinalResult, NightSummary } from "@/types/study";

const STAGE_COLORS: Record<string, string> = {
  Wake: "#fbbf24", REM: "#f472b6", N1: "#a5b4fc", N2: "#818cf8", N3: "#4338ca", Movement: "#94a3b8",
};
const STAGE_ORDER = ["Wake", "REM", "N1", "N2", "N3", "Movement"];

function MetricRow({ label, unit, values }: { label: string; unit: string; values: (number | null)[] }) {
  const numeric = values.filter((v): v is number => v != null);
  const max = numeric.length ? Math.max(...numeric) : 1;
  return (
    <tr>
      <td className="py-2 pr-4 text-xs font-medium text-slate-500">{label}</td>
      {values.map((v, i) => (
        <td key={i} className="py-2 pr-4">
          {v != null ? (
            <div className="flex items-center gap-2">
              <div className="h-1.5 w-16 rounded-full bg-slate-100">
                <div className="h-1.5 rounded-full bg-brand-500" style={{ width: `${(v / max) * 100}%` }} />
              </div>
              <span className="text-sm text-slate-700">
                {v}
                {unit}
              </span>
            </div>
          ) : (
            <span className="text-xs text-slate-300">n/a</span>
          )}
        </td>
      ))}
    </tr>
  );
}

function StageBar({ night }: { night: NightSummary }) {
  return (
    <div className="flex h-4 overflow-hidden rounded">
      {STAGE_ORDER.filter((s) => night.stage_pct[s]).map((stage) => (
        <div
          key={stage}
          style={{ width: `${night.stage_pct[stage]}%`, backgroundColor: STAGE_COLORS[stage] }}
          title={`${stage}: ${night.stage_pct[stage]}%`}
        />
      ))}
    </div>
  );
}

export default function LongitudinalPage() {
  const [result, setResult] = useState<LongitudinalResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getLongitudinal().then(setResult).catch(() => setError("Could not load longitudinal data."));
  }, []);

  if (error) return <p className="text-sm text-red-600">{error}</p>;

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-xl font-semibold text-slate-900">Longitudinal</h1>
      <p className="mt-1 text-sm text-slate-600">
        Multi-night burden tracking for the same person — same pipeline, same features, night
        over night.
      </p>

      {!result && <p className="mt-4 text-sm text-slate-400">Loading…</p>}

      {result && !result.available && (
        <Card className="mt-4">
          <p className="text-sm text-slate-600">{result.message}</p>
        </Card>
      )}

      {result?.available &&
        result.patients.map((p) => (
          <Card key={p.patient_key} className="mt-4">
            <div className="text-sm font-semibold text-slate-900">Patient {p.patient_key}</div>
            <p className="text-xs text-slate-500">{p.nights.length} nights ingested</p>

            <table className="mt-3 w-full">
              <thead>
                <tr>
                  <td />
                  {p.nights.map((n) => (
                    <td key={n.study_id} className="pb-1 pr-4 text-xs font-semibold text-slate-700">
                      {n.record_name}
                    </td>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                <MetricRow label="Duration (min)" unit="" values={p.nights.map((n) => Math.round(n.duration_sec / 60))} />
                <MetricRow label="Events / hour" unit="" values={p.nights.map((n) => n.events_per_hour)} />
                <MetricRow label="Mean SpO2" unit="%" values={p.nights.map((n) => n.mean_spo2)} />
                <MetricRow label="ODI" unit="/hr" values={p.nights.map((n) => n.odi)} />
              </tbody>
            </table>

            <div className="mt-3 space-y-1.5">
              <div className="text-xs font-medium text-slate-500">Sleep stage composition</div>
              {p.nights.map((n) => (
                <div key={n.study_id}>
                  <div className="mb-0.5 text-[10px] text-slate-400">{n.record_name}</div>
                  <StageBar night={n} />
                </div>
              ))}
            </div>
          </Card>
        ))}
    </div>
  );
}
