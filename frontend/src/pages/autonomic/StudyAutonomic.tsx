import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { api } from "@/api/client";
import { Card } from "@/components/layout/Card";
import type { EventFeatureResult, StudyDetail } from "@/types/study";

function formatTime(totalSeconds: number): string {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = Math.floor(totalSeconds % 60);
  return [h, m, s].map((n) => String(n).padStart(2, "0")).join(":");
}

function HrBar({ baseline, peak, min, max }: { baseline: number; peak: number; min: number; max: number }) {
  const pct = (v: number) => ((v - min) / (max - min)) * 100;
  return (
    <div className="relative h-2 rounded-full bg-slate-100">
      <div
        className="absolute top-0 h-2 rounded-full bg-brand-200"
        style={{ left: `${pct(baseline)}%`, width: `${pct(peak) - pct(baseline)}%` }}
      />
      <div className="absolute top-1/2 h-2.5 w-2.5 -translate-y-1/2 rounded-full bg-slate-400" style={{ left: `${pct(baseline)}%` }} />
      <div className="absolute top-1/2 h-2.5 w-2.5 -translate-y-1/2 rounded-full bg-red-500" style={{ left: `${pct(peak)}%` }} />
    </div>
  );
}

export default function StudyAutonomic() {
  const { studyId } = useParams<{ studyId: string }>();
  const id = Number(studyId);

  const [study, setStudy] = useState<StudyDetail | null>(null);
  const [result, setResult] = useState<EventFeatureResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getStudy(id).then(setStudy).catch(() => setError("Could not load this study."));
    api
      .getAutonomicResponse(id)
      .then(setResult)
      .catch(() => setError("Could not compute autonomic response."));
  }, [id]);

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!study || !result) return <p className="text-sm text-slate-400">Detecting R-peaks and computing HR response…</p>;

  const withHr = result.events.filter((e) => e.hr_baseline_bpm != null && e.hr_peak_bpm != null);
  const allBpm = withHr.flatMap((e) => [e.hr_baseline_bpm as number, e.hr_peak_bpm as number]);
  const min = allBpm.length ? Math.min(...allBpm) - 5 : 40;
  const max = allBpm.length ? Math.max(...allBpm) + 5 : 120;

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-xl font-semibold text-slate-900">Autonomic Response</h1>
      <p className="mt-1 text-sm text-slate-600">
        {study.display_name || study.record_name} — heart-rate response from{" "}
        {result.channel_used?.name ?? "the ECG channel"} (R-peak detection), 30s before each event
        to 20s after. A cardiovascular signal change, not a direct measurement of autonomic
        nervous system nuclei.
      </p>

      {!result.available && (
        <Card className="mt-4">
          <p className="text-sm text-slate-600">{result.message}</p>
        </Card>
      )}

      {result.available && (
        <div className="mt-4 space-y-2">
          <div className="flex justify-end gap-3 text-[10px] text-slate-400">
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-slate-400" /> baseline
            </span>
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-red-500" /> peak
            </span>
          </div>
          {withHr.map((e) => (
            <Card key={e.id}>
              <div className="flex items-center justify-between text-sm">
                <div className="font-medium text-slate-900">
                  {formatTime(e.onset_sec)} · {e.event_type}
                </div>
                <div className="text-xs text-slate-500">
                  {e.hr_baseline_bpm?.toFixed(0)} → {e.hr_peak_bpm?.toFixed(0)} bpm{" "}
                  <span className="font-medium text-red-600">(+{e.hr_response_bpm?.toFixed(1)})</span>
                </div>
              </div>
              <div className="mt-2">
                <HrBar baseline={e.hr_baseline_bpm as number} peak={e.hr_peak_bpm as number} min={min} max={max} />
              </div>
            </Card>
          ))}
          {withHr.length === 0 && (
            <Card>
              <p className="text-sm text-slate-500">No events had enough clean R-peaks nearby to compute HR response.</p>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
