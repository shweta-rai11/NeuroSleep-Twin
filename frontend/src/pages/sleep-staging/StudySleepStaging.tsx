import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { api } from "@/api/client";
import { Card } from "@/components/layout/Card";
import type { RespiratoryEventsResult, SleepStagesResult, StudyDetail } from "@/types/study";

const STAGE_LEVELS: Record<string, number> = { Wake: 5, REM: 4, N1: 3, N2: 2, N3: 1, Movement: 0 };
const STAGE_COLORS: Record<string, string> = {
  Wake: "#fbbf24", REM: "#f472b6", N1: "#a5b4fc", N2: "#818cf8", N3: "#4338ca", Movement: "#94a3b8",
};
const STAGE_ORDER = ["Wake", "REM", "N1", "N2", "N3", "Movement"];

function formatMinutes(min: number): string {
  const h = Math.floor(min / 60);
  const m = Math.round(min % 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

function Hypnogram({ epochs, duration }: { epochs: SleepStagesResult["epochs"]; duration: number }) {
  const width = 1000;
  const height = 140;
  const levelHeight = height / 6;

  const points = epochs.flatMap((e) => {
    const x0 = (e.onset_sec / duration) * width;
    const x1 = ((e.onset_sec + e.duration_sec) / duration) * width;
    const y = height - (STAGE_LEVELS[e.stage] + 0.5) * levelHeight;
    return [`${x0},${y}`, `${x1},${y}`];
  });

  return (
    <svg viewBox={`0 0 ${width} ${height + 20}`} className="w-full" preserveAspectRatio="none">
      {STAGE_ORDER.map((stage) => (
        <text key={stage} x={2} y={height - (STAGE_LEVELS[stage] + 0.5) * levelHeight + 3} fontSize="9" fill="#94a3b8">
          {stage}
        </text>
      ))}
      <polyline points={points.join(" ")} fill="none" stroke="#2748d8" strokeWidth="1.5" />
      {epochs.map((e, i) => (
        <rect
          key={i}
          x={(e.onset_sec / duration) * width}
          y={height + 4}
          width={Math.max((e.duration_sec / duration) * width, 0.5)}
          height={10}
          fill={STAGE_COLORS[e.stage] ?? "#cbd5e1"}
        />
      ))}
    </svg>
  );
}

export default function StudySleepStaging() {
  const { studyId } = useParams<{ studyId: string }>();
  const id = Number(studyId);

  const [study, setStudy] = useState<StudyDetail | null>(null);
  const [result, setResult] = useState<SleepStagesResult | null>(null);
  const [events, setEvents] = useState<RespiratoryEventsResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getStudy(id).then(setStudy).catch(() => setError("Could not load this study."));
    api.getSleepStages(id).then(setResult).catch(() => setError("Could not load sleep stages."));
    api.getRespiratoryEvents(id).then(setEvents).catch(() => setEvents(null));
  }, [id]);

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!study || !result) return <p className="text-sm text-slate-400">Loading…</p>;

  const duration = study.duration_sec ?? 0;
  const totalMinutes = Object.values(result.stage_minutes).reduce((a, b) => a + b, 0);

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-xl font-semibold text-slate-900">Sleep Staging</h1>
      <p className="mt-1 text-sm text-slate-600">
        {study.display_name || study.record_name} — hypnogram from the dataset's own ground-truth
        stage annotations (an observed measurement, not a model output).
      </p>

      {!result.available && (
        <Card className="mt-4">
          <p className="text-sm text-slate-600">{result.message}</p>
        </Card>
      )}

      {result.available && (
        <>
          <Card className="mt-4">
            <Hypnogram epochs={result.epochs} duration={duration} />
            {events?.available && (
              <div className="relative mt-1 h-3">
                {events.events.map((e) => (
                  <div
                    key={e.id}
                    title={`${e.event_type} at ${Math.round(e.onset_sec)}s`}
                    className={`absolute top-0 h-3 w-0.5 ${e.event_type === "apnea" ? "bg-red-500" : "bg-amber-500"}`}
                    style={{ left: `${(e.onset_sec / duration) * 100}%` }}
                  />
                ))}
              </div>
            )}
            <div className="mt-1 flex justify-end gap-3 text-[10px] text-slate-400">
              <span className="flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-red-500" /> apnea
              </span>
              <span className="flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-amber-500" /> hypopnea
              </span>
            </div>
          </Card>

          <div className="mt-4 grid grid-cols-3 gap-3 sm:grid-cols-6">
            {STAGE_ORDER.filter((s) => result.stage_minutes[s] != null).map((stage) => (
              <Card key={stage} className="text-center">
                <div className="text-lg font-semibold" style={{ color: STAGE_COLORS[stage] }}>
                  {formatMinutes(result.stage_minutes[stage])}
                </div>
                <div className="mt-1 text-xs text-slate-500">{stage}</div>
                <div className="text-[10px] text-slate-400">
                  {Math.round((result.stage_minutes[stage] / totalMinutes) * 100)}%
                </div>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
