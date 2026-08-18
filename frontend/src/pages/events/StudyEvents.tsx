import { AlertTriangle } from "lucide-react";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { api } from "@/api/client";
import { Card } from "@/components/layout/Card";
import { computeFingerprint } from "@/components/fingerprint/computeFingerprint";
import { RadarChart } from "@/components/fingerprint/RadarChart";
import type { AcousticAnalysisResult, RespiratoryEvent, RespiratoryEventsResult, StudyDetail } from "@/types/study";

function formatTime(totalSeconds: number): string {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = Math.floor(totalSeconds % 60);
  return [h, m, s].map((n) => String(n).padStart(2, "0")).join(":");
}

export default function StudyEvents() {
  const { studyId } = useParams<{ studyId: string }>();
  const id = Number(studyId);

  const [study, setStudy] = useState<StudyDetail | null>(null);
  const [result, setResult] = useState<RespiratoryEventsResult | null>(null);
  const [acoustic, setAcoustic] = useState<AcousticAnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<RespiratoryEvent | null>(null);

  useEffect(() => {
    api.getStudy(id).then(setStudy).catch(() => setError("Could not load this study."));
    api
      .getRespiratoryEvents(id)
      .then((r) => {
        setResult(r);
        if (r.events.length > 0) setSelected(r.events[0]);
        // No physiological resp/airflow channel — this may be an audio-only
        // upload instead, which gets a different (much rougher) analysis.
        if (!r.available) {
          api.getAcousticAnalysis(id).then(setAcoustic).catch(() => setAcoustic(null));
        }
      })
      .catch(() => setError("Could not run respiratory event detection."));
  }, [id]);

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!study || !result) return <p className="text-sm text-slate-400">Detecting candidate events…</p>;

  const duration = study.duration_sec ?? 0;

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-xl font-semibold text-slate-900">Respiratory Events</h1>
      <p className="mt-1 text-sm text-slate-600">
        {study.display_name || study.record_name} —{" "}
        {result.available
          ? `candidate events from an amplitude-envelope detector (${result.algorithm_version}). A machine-learning estimate, not a clinical scoring.`
          : acoustic?.available
            ? "no physiological respiratory channel here, so showing acoustic breathing-pause analysis from the uploaded audio instead."
            : "candidate respiratory events."}
      </p>

      {!result.available && !acoustic?.available && (
        <Card className="mt-4">
          <p className="text-sm text-slate-600">{result.message}</p>
        </Card>
      )}

      {!result.available && acoustic?.available && acoustic.summary && (
        <>
          <Card className="mt-4 border-amber-200 bg-amber-50">
            <div className="flex items-start gap-1.5 text-xs text-amber-800">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              {acoustic.message}
            </div>
          </Card>

          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Card className="text-center">
              <div className="text-2xl font-semibold text-slate-900">{acoustic.summary.pause_count}</div>
              <div className="mt-1 text-xs text-slate-500">Candidate pauses</div>
            </Card>
            <Card className="text-center">
              <div className="text-2xl font-semibold text-slate-900">{acoustic.summary.pauses_per_hour}</div>
              <div className="mt-1 text-xs text-slate-500">Pauses / hour</div>
            </Card>
            <Card className="text-center">
              <div className="text-2xl font-semibold text-slate-900">
                {acoustic.summary.mean_pause_duration_sec}s
              </div>
              <div className="mt-1 text-xs text-slate-500">Mean pause length</div>
            </Card>
            <Card className="text-center">
              <div className="text-2xl font-semibold text-slate-900">{acoustic.summary.pct_time_in_pause}%</div>
              <div className="mt-1 text-xs text-slate-500">Time in pause</div>
            </Card>
          </div>

          <Card className="mt-4">
            <div className="mb-1 text-xs text-slate-500">
              Timeline — channel: {acoustic.channel_used?.name}
            </div>
            <div className="relative h-6 overflow-hidden rounded bg-slate-100">
              {acoustic.pauses.map((p, i) => (
                <div
                  key={i}
                  title={`${formatTime(p.onset_sec)} — quiet for ${p.duration_sec.toFixed(1)}s`}
                  className="absolute top-0 h-full bg-slate-500"
                  style={{
                    left: `${(p.onset_sec / duration) * 100}%`,
                    width: `${Math.max((p.duration_sec / duration) * 100, 0.3)}%`,
                  }}
                />
              ))}
            </div>
          </Card>

          <Card className="mt-4 overflow-hidden !p-0">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-2">Onset</th>
                  <th className="px-4 py-2">Duration</th>
                  <th className="px-4 py-2">Depth ratio</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {acoustic.pauses.map((p, i) => (
                  <tr key={i}>
                    <td className="px-4 py-2 font-mono text-xs text-slate-700">{formatTime(p.onset_sec)}</td>
                    <td className="px-4 py-2 text-slate-600">{p.duration_sec.toFixed(1)}s</td>
                    <td className="px-4 py-2 text-slate-600">{p.depth_ratio.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </>
      )}

      {result.available && result.summary && (
        <>
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Card className="text-center">
              <div className="text-2xl font-semibold text-slate-900">{result.summary.count}</div>
              <div className="mt-1 text-xs text-slate-500">Total candidate events</div>
            </Card>
            <Card className="text-center">
              <div className="text-2xl font-semibold text-red-600">{result.summary.apnea_count}</div>
              <div className="mt-1 text-xs text-slate-500">Apnea-like</div>
            </Card>
            <Card className="text-center">
              <div className="text-2xl font-semibold text-amber-600">{result.summary.hypopnea_count}</div>
              <div className="mt-1 text-xs text-slate-500">Hypopnea-like</div>
            </Card>
            <Card className="text-center">
              <div className="text-2xl font-semibold text-slate-900">{result.summary.events_per_hour}</div>
              <div className="mt-1 text-xs text-slate-500">Events / hour</div>
            </Card>
          </div>

          <Card className="mt-4">
            <div className="mb-1 text-xs text-slate-500">
              Timeline — channel: {result.channel_used?.name}
            </div>
            <div className="relative h-6 overflow-hidden rounded bg-slate-100">
              {result.events.map((e) => (
                <div
                  key={e.id}
                  title={`${formatTime(e.onset_sec)} — ${e.event_type} (${e.duration_sec.toFixed(1)}s)`}
                  className={`absolute top-0 h-full ${e.event_type === "apnea" ? "bg-red-500" : "bg-amber-400"}`}
                  style={{
                    left: `${(e.onset_sec / duration) * 100}%`,
                    width: `${Math.max((e.duration_sec / duration) * 100, 0.3)}%`,
                  }}
                />
              ))}
            </div>
          </Card>

          <div className="mt-4 grid gap-4 sm:grid-cols-[1fr_260px]">
            <Card className="overflow-hidden !p-0">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-4 py-2">Onset</th>
                    <th className="px-4 py-2">Duration</th>
                    <th className="px-4 py-2">Type</th>
                    <th className="px-4 py-2">Depth ratio</th>
                    <th className="px-4 py-2">Desat depth</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {result.events.map((e) => (
                    <tr
                      key={e.id}
                      onClick={() => setSelected(e)}
                      className={`cursor-pointer ${selected?.id === e.id ? "bg-brand-50" : "hover:bg-slate-50"}`}
                    >
                      <td className="px-4 py-2 font-mono text-xs text-slate-700">{formatTime(e.onset_sec)}</td>
                      <td className="px-4 py-2 text-slate-600">{e.duration_sec.toFixed(1)}s</td>
                      <td className="px-4 py-2">
                        <span
                          className={
                            e.event_type === "apnea"
                              ? "rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700"
                              : "rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700"
                          }
                        >
                          {e.event_type}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-slate-600">{e.depth_ratio.toFixed(3)}</td>
                      <td className="px-4 py-2 text-slate-600">
                        {e.desaturation_depth != null ? `${e.desaturation_depth.toFixed(1)}%` : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>

            {selected && (
              <Card>
                <div className="text-xs font-medium text-slate-500">
                  Event fingerprint — {formatTime(selected.onset_sec)}
                </div>
                <div className="flex justify-center">
                  <RadarChart axes={computeFingerprint(selected)} size={220} />
                </div>
                <p className="text-center text-[10px] text-slate-400">
                  Normalized 0-1 per axis, fixed scales — not a clinical score.
                </p>
              </Card>
            )}
          </div>
        </>
      )}
    </div>
  );
}
