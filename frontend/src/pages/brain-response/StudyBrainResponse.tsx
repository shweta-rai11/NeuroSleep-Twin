import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { api } from "@/api/client";
import { Card } from "@/components/layout/Card";
import type { EventFeatureResult, StudyDetail } from "@/types/study";

const BAND_COLORS: Record<string, string> = {
  delta: "#4338ca", theta: "#6366f1", alpha: "#a5b4fc", beta: "#fbbf24",
};

function formatTime(totalSeconds: number): string {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = Math.floor(totalSeconds % 60);
  return [h, m, s].map((n) => String(n).padStart(2, "0")).join(":");
}

export default function StudyBrainResponse() {
  const { studyId } = useParams<{ studyId: string }>();
  const id = Number(studyId);

  const [study, setStudy] = useState<StudyDetail | null>(null);
  const [result, setResult] = useState<EventFeatureResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getStudy(id).then(setStudy).catch(() => setError("Could not load this study."));
    api.getBrainResponse(id).then(setResult).catch(() => setError("Could not compute brain response."));
  }, [id]);

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!study || !result) return <p className="text-sm text-slate-400">Computing EEG spectral response…</p>;

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-xl font-semibold text-slate-900">Brain Response</h1>
      <p className="mt-1 text-sm text-slate-600">
        {study.display_name || study.record_name} — relative EEG band power in the 15s following
        each event, from {result.channel_used?.name ?? "the EEG channel"}. Arousal probability is
        a heuristic power-shift proxy, not AASM arousal scoring.
      </p>

      {!result.available && (
        <Card className="mt-4">
          <p className="text-sm text-slate-600">{result.message}</p>
        </Card>
      )}

      {result.available && (
        <div className="mt-4 space-y-2">
          <div className="flex justify-end gap-3 text-[10px] text-slate-400">
            {Object.entries(BAND_COLORS).map(([band, color]) => (
              <span key={band} className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-sm" style={{ backgroundColor: color }} /> {band}
              </span>
            ))}
          </div>
          {result.events.map((e) => {
            const bands = [
              ["delta", e.eeg_delta_rel],
              ["theta", e.eeg_theta_rel],
              ["alpha", e.eeg_alpha_rel],
              ["beta", e.eeg_beta_rel],
            ] as const;
            const hasData = bands.every(([, v]) => v != null);
            return (
              <Card key={e.id}>
                <div className="flex items-center justify-between">
                  <div className="text-sm font-medium text-slate-900">
                    {formatTime(e.onset_sec)} · {e.event_type}
                  </div>
                  {e.arousal_probability != null && (
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                      arousal p={e.arousal_probability.toFixed(2)}
                    </span>
                  )}
                </div>
                {hasData ? (
                  <div className="mt-2 flex h-4 overflow-hidden rounded">
                    {bands.map(([band, value]) => (
                      <div
                        key={band}
                        style={{ width: `${(value ?? 0) * 100}%`, backgroundColor: BAND_COLORS[band] }}
                        title={`${band}: ${((value ?? 0) * 100).toFixed(1)}%`}
                      />
                    ))}
                  </div>
                ) : (
                  <p className="mt-2 text-xs text-slate-400">Not enough EEG signal around this event.</p>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
