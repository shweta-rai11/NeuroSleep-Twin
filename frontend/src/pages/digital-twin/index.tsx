import { ChevronDown } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { api } from "@/api/client";
import { CascadeScene } from "@/components/digital-twin/CascadeScene";
import { Card } from "@/components/layout/Card";
import type { RespiratoryEvent, StudyListItem } from "@/types/study";

function formatTime(totalSeconds: number): string {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = Math.floor(totalSeconds % 60);
  return [h, m, s].map((n) => String(n).padStart(2, "0")).join(":");
}

export default function DigitalTwinPage() {
  const [studies, setStudies] = useState<StudyListItem[] | null>(null);
  const [studyId, setStudyId] = useState<number | null>(null);
  const [events, setEvents] = useState<RespiratoryEvent[]>([]);
  const [eventId, setEventId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listStudies().then((all) => {
      const ingested = all.filter((s) => s.status === "ingested");
      setStudies(ingested);
      if (ingested.length > 0) setStudyId(ingested[0].id);
    });
  }, []);

  useEffect(() => {
    if (!studyId) return;
    api
      .getRespiratoryEvents(studyId)
      .then((r) => {
        setEvents(r.events);
        setEventId(r.events[0]?.id ?? null);
        if (!r.available) setError(r.message);
        else setError(null);
      })
      .catch(() => setError("Could not load events for this study."));
  }, [studyId]);

  const selectedEvent = events.find((e) => e.id === eventId) ?? null;

  const magnitudes = useMemo(() => {
    if (!selectedEvent) return { respiratory: 0, oxygen: 0, cortical: 0, autonomic: 0 };
    const clip01 = (v: number) => Math.max(0, Math.min(1, v));
    return {
      respiratory: clip01(1 - selectedEvent.depth_ratio),
      oxygen: selectedEvent.desaturation_depth != null ? clip01(selectedEvent.desaturation_depth / 30) : 0,
      cortical: selectedEvent.arousal_probability ?? 0,
      autonomic: selectedEvent.hr_response_bpm != null ? clip01(selectedEvent.hr_response_bpm / 40) : 0,
    };
  }, [selectedEvent]);

  return (
    <div className="mx-auto max-w-4xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Digital Twin</h1>
          <p className="mt-1 text-sm text-slate-600">
            A conceptual model — not a visualization of real-time neuronal activity. Node size and
            glow reflect one selected event's actual computed features.
          </p>
        </div>
        <div className="flex gap-2">
          {studies && studies.length > 0 && (
            <div className="relative">
              <select
                value={studyId ?? ""}
                onChange={(e) => setStudyId(Number(e.target.value))}
                className="appearance-none rounded-md border border-slate-300 py-1.5 pl-3 pr-8 text-sm"
              >
                {studies.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.display_name || s.record_name}
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
            </div>
          )}
          {events.length > 0 && (
            <div className="relative">
              <select
                value={eventId ?? ""}
                onChange={(e) => setEventId(Number(e.target.value))}
                className="appearance-none rounded-md border border-slate-300 py-1.5 pl-3 pr-8 text-sm"
              >
                {events.map((e) => (
                  <option key={e.id} value={e.id}>
                    {formatTime(e.onset_sec)} · {e.event_type}
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
            </div>
          )}
        </div>
      </div>

      {error && (
        <Card className="mt-4">
          <p className="text-sm text-slate-600">{error}</p>
        </Card>
      )}

      {selectedEvent && (
        <Card className="mt-4 !p-0 overflow-hidden">
          <div style={{ height: 480 }}>
            <CascadeScene magnitudes={magnitudes} />
          </div>
          <div className="border-t border-slate-100 px-4 py-2 text-xs text-slate-500">
            Drag to orbit. Showing the {selectedEvent.event_type} event at{" "}
            {formatTime(selectedEvent.onset_sec)} — respiratory severity{" "}
            {Math.round(magnitudes.respiratory * 100)}%, oxygen desaturation{" "}
            {Math.round(magnitudes.oxygen * 100)}%, cortical arousal proxy{" "}
            {Math.round(magnitudes.cortical * 100)}%, autonomic HR response{" "}
            {Math.round(magnitudes.autonomic * 100)}%.
          </div>
        </Card>
      )}
    </div>
  );
}
