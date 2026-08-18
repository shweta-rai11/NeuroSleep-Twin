import { useCallback, useEffect, useMemo, useState } from "react";
import Plot from "react-plotly.js";
import { useParams } from "react-router-dom";

import { api } from "@/api/client";
import { Card } from "@/components/layout/Card";
import type { AnnotationInfo, SignalWindow, StudyDetail } from "@/types/study";

const WINDOW_LENGTH_OPTIONS = [
  { label: "30s", seconds: 30 },
  { label: "1 min", seconds: 60 },
  { label: "2 min", seconds: 120 },
  { label: "5 min", seconds: 300 },
  { label: "10 min", seconds: 600 },
];

const CHANNEL_COLORS = ["#2748d8", "#c2410c", "#0f766e", "#7c3aed", "#be123c", "#4d7c0f"];

// First token of an MIT-BIH PSG '.st' aux_note is the epoch's sleep-stage
// code (0-4/R); anything after it is respiratory/arousal event tags for
// that 30s epoch. Real stage/event semantics land in Phases 7-8 — this is
// just enough to color the overview strip today.
const STAGE_COLORS: Record<string, string> = {
  W: "#fbbf24",
  R: "#f472b6",
  "0": "#fbbf24",
  "1": "#a5b4fc",
  "2": "#818cf8",
  "3": "#6366f1",
  "4": "#4338ca",
};

function formatTime(totalSeconds: number): string {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = Math.floor(totalSeconds % 60);
  return [h, m, s].map((n) => String(n).padStart(2, "0")).join(":");
}

export default function StudyViewer() {
  const { studyId } = useParams<{ studyId: string }>();
  const id = Number(studyId);

  const [study, setStudy] = useState<StudyDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [windowStart, setWindowStart] = useState(0);
  const [windowLength, setWindowLength] = useState(60);
  const [windows, setWindows] = useState<Record<number, SignalWindow>>({});
  const [loadingWindow, setLoadingWindow] = useState(false);

  useEffect(() => {
    api
      .getStudy(id)
      .then(setStudy)
      .catch(() => setError("Could not load this study. Is the backend running on :8000?"));
  }, [id]);

  const duration = study?.duration_sec ?? 0;

  const loadWindow = useCallback(
    async (start: number, length: number) => {
      if (!study) return;
      setLoadingWindow(true);
      try {
        const results = await Promise.all(
          study.channels.map((ch) => api.getSignalWindow(study.id, ch.id, start, Math.min(start + length, duration))),
        );
        const byChannel: Record<number, SignalWindow> = {};
        study.channels.forEach((ch, i) => {
          byChannel[ch.id] = results[i];
        });
        setWindows(byChannel);
      } finally {
        setLoadingWindow(false);
      }
    },
    [study, duration],
  );

  useEffect(() => {
    loadWindow(windowStart, windowLength);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [study, windowStart, windowLength]);

  function jumpTo(startSec: number) {
    const clamped = Math.max(0, Math.min(startSec, Math.max(0, duration - windowLength)));
    setWindowStart(clamped);
  }

  const annotationsInWindow: AnnotationInfo[] = useMemo(() => {
    if (!study) return [];
    const end = windowStart + windowLength;
    return study.annotations.filter((a) => a.onset_sec < end && a.onset_sec + a.duration_sec > windowStart);
  }, [study, windowStart, windowLength]);

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!study) return <p className="text-sm text-slate-400">Loading…</p>;

  const rowCount = study.channels.length;
  const gap = 0.03;
  const rowHeight = (1 - gap * (rowCount - 1)) / rowCount;

  const traces = study.channels.map((ch, i) => {
    const w = windows[ch.id];
    const yaxis = i === 0 ? "y" : `y${i + 1}`;
    return {
      x: w?.t ?? [],
      y: w?.v ?? [],
      type: "scattergl" as const,
      mode: "lines" as const,
      name: `${ch.name}${ch.unit ? ` (${ch.unit})` : ""}`,
      line: { color: CHANNEL_COLORS[i % CHANNEL_COLORS.length], width: 1 },
      xaxis: "x",
      yaxis,
    };
  });

  const layout: Record<string, unknown> = {
    height: Math.max(120 * rowCount, 320),
    margin: { l: 60, r: 20, t: 10, b: 40 },
    showlegend: false,
    xaxis: {
      title: "Time (s)",
      range: [windowStart, windowStart + windowLength],
    },
    shapes: annotationsInWindow.map((a) => ({
      type: "line",
      xref: "x",
      yref: "paper",
      x0: a.onset_sec,
      x1: a.onset_sec,
      y0: 0,
      y1: 1,
      line: { color: "#94a3b8", width: 1, dash: "dot" },
    })),
    annotations: annotationsInWindow.map((a) => ({
      x: a.onset_sec,
      y: 1,
      yref: "paper",
      text: a.label,
      showarrow: false,
      textangle: -90,
      font: { size: 9, color: "#64748b" },
      xanchor: "left",
      yanchor: "top",
    })),
  };

  study.channels.forEach((ch, i) => {
    const key = i === 0 ? "yaxis" : `yaxis${i + 1}`;
    const top = 1 - i * (rowHeight + gap);
    layout[key] = {
      title: ch.name,
      domain: [Math.max(0, top - rowHeight), top],
      titlefont: { size: 10 },
      tickfont: { size: 9 },
    };
  });

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">
            {study.display_name || study.record_name}
          </h1>
          <p className="text-xs text-slate-500">
            {study.dataset_id} · {study.channels.length} channels · {formatTime(duration)} total
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-slate-500">Window</label>
          <select
            value={windowLength}
            onChange={(e) => setWindowLength(Number(e.target.value))}
            className="rounded-md border border-slate-300 px-2 py-1 text-xs"
          >
            {WINDOW_LENGTH_OPTIONS.map((opt) => (
              <option key={opt.seconds} value={opt.seconds}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <Card className="mb-4">
        <div className="mb-1 flex items-center justify-between text-xs text-slate-500">
          <span>Night Map (click to jump)</span>
          <span>
            {formatTime(windowStart)} – {formatTime(windowStart + windowLength)}
          </span>
        </div>
        <div
          className="relative h-6 cursor-pointer overflow-hidden rounded bg-slate-100"
          onClick={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const fraction = (e.clientX - rect.left) / rect.width;
            jumpTo(fraction * duration);
          }}
        >
          {study.annotations.map((a) => {
            const stageCode = a.label.trim().split(" ")[0];
            const color = STAGE_COLORS[stageCode] ?? "#cbd5e1";
            return (
              <div
                key={a.id}
                className="absolute top-0 h-full"
                style={{
                  left: `${(a.onset_sec / duration) * 100}%`,
                  width: `${Math.max((a.duration_sec / duration) * 100, 0.15)}%`,
                  backgroundColor: color,
                }}
                title={`${formatTime(a.onset_sec)} — ${a.label}`}
              />
            );
          })}
          <div
            className="absolute top-0 h-full border-x-2 border-slate-900/70 bg-slate-900/10"
            style={{
              left: `${(windowStart / duration) * 100}%`,
              width: `${(windowLength / duration) * 100}%`,
            }}
          />
        </div>
      </Card>

      <Card>
        <div className="mb-2 flex items-center justify-between">
          <button
            onClick={() => jumpTo(windowStart - windowLength)}
            disabled={windowStart <= 0}
            className="rounded-md border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-40"
          >
            ← Prev
          </button>
          {loadingWindow && <span className="text-xs text-slate-400">Loading window…</span>}
          <button
            onClick={() => jumpTo(windowStart + windowLength)}
            disabled={windowStart + windowLength >= duration}
            className="rounded-md border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-40"
          >
            Next →
          </button>
        </div>
        {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
        <Plot data={traces as any} layout={layout} config={{ displaylogo: false }} style={{ width: "100%" }} />
      </Card>
    </div>
  );
}
