import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { api } from "@/api/client";
import { Card } from "@/components/layout/Card";
import type { OxygenBurdenResult, StudyDetail } from "@/types/study";

export default function StudyOxygenBurden() {
  const { studyId } = useParams<{ studyId: string }>();
  const id = Number(studyId);

  const [study, setStudy] = useState<StudyDetail | null>(null);
  const [result, setResult] = useState<OxygenBurdenResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getStudy(id).then(setStudy).catch(() => setError("Could not load this study."));
    api.getOxygenBurden(id).then(setResult).catch(() => setError("Could not compute oxygen burden."));
  }, [id]);

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!study || !result) return <p className="text-sm text-slate-400">Computing oxygen burden…</p>;

  const desatEvents = result.events.filter((e) => e.desaturation_depth != null);

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-xl font-semibold text-slate-900">Oxygen Burden</h1>
      <p className="mt-1 text-sm text-slate-600">
        {study.display_name || study.record_name} — derived physiological metrics from{" "}
        {result.channel_used?.name ?? "the SpO2 channel"}, using a fixed, disclosed formula.
      </p>

      {!result.available && (
        <Card className="mt-4">
          <p className="text-sm text-slate-600">{result.message}</p>
        </Card>
      )}

      {result.available && result.summary && (
        <>
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-5">
            <Card className="text-center">
              <div className="text-2xl font-semibold text-slate-900">{result.summary.mean_spo2}%</div>
              <div className="mt-1 text-xs text-slate-500">Mean SpO2</div>
            </Card>
            <Card className="text-center">
              <div className="text-2xl font-semibold text-red-600">{result.summary.min_spo2}%</div>
              <div className="mt-1 text-xs text-slate-500">Min SpO2</div>
            </Card>
            <Card className="text-center">
              <div className="text-2xl font-semibold text-slate-900">{result.summary.pct_time_below_90}%</div>
              <div className="mt-1 text-xs text-slate-500">Time below 90%</div>
            </Card>
            <Card className="text-center">
              <div className="text-2xl font-semibold text-slate-900">{result.summary.odi}</div>
              <div className="mt-1 text-xs text-slate-500">ODI (dips/hr)</div>
            </Card>
            <Card className="text-center">
              <div className="text-2xl font-semibold text-slate-400">{result.summary.artifact_pct}%</div>
              <div className="mt-1 text-xs text-slate-500">Sensor dropout, cleaned</div>
            </Card>
          </div>

          <Card className="mt-4 overflow-hidden !p-0">
            <div className="border-b border-slate-100 px-4 py-2 text-xs font-medium text-slate-500">
              Per-event desaturation ({desatEvents.length} of {result.events.length} candidate events)
            </div>
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-2">Baseline</th>
                  <th className="px-4 py-2">Nadir</th>
                  <th className="px-4 py-2">Depth</th>
                  <th className="px-4 py-2">Slope</th>
                  <th className="px-4 py-2">Recovery</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {desatEvents.map((e) => (
                  <tr key={e.id}>
                    <td className="px-4 py-2 text-slate-600">{e.spo2_baseline?.toFixed(1)}%</td>
                    <td className="px-4 py-2 text-slate-600">{e.spo2_nadir?.toFixed(1)}%</td>
                    <td className="px-4 py-2 font-medium text-slate-900">
                      {e.desaturation_depth?.toFixed(1)}%
                    </td>
                    <td className="px-4 py-2 text-slate-600">{e.desaturation_slope?.toFixed(3)} %/s</td>
                    <td className="px-4 py-2 text-slate-600">
                      {e.recovery_sec != null ? `${e.recovery_sec.toFixed(1)}s` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </>
      )}
    </div>
  );
}
