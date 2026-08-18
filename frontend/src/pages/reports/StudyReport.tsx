import { Printer } from "lucide-react";
import { type ReactNode, useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { api } from "@/api/client";
import type { DatasetEntry } from "@/types/dataset";
import type {
  BenchmarkResult,
  OxygenBurdenResult,
  RespiratoryEventsResult,
  SleepStagesResult,
  StudyDetail,
  StudyQc,
} from "@/types/study";

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mt-6 break-inside-avoid">
      <h2 className="border-b border-slate-200 pb-1 text-sm font-semibold uppercase tracking-wide text-slate-500">
        {title}
      </h2>
      <div className="mt-2">{children}</div>
    </section>
  );
}

export default function StudyReport() {
  const { studyId } = useParams<{ studyId: string }>();
  const id = Number(studyId);

  const [study, setStudy] = useState<StudyDetail | null>(null);
  const [dataset, setDataset] = useState<DatasetEntry | null>(null);
  const [qc, setQc] = useState<StudyQc | null>(null);
  const [events, setEvents] = useState<RespiratoryEventsResult | null>(null);
  const [oxygen, setOxygen] = useState<OxygenBurdenResult | null>(null);
  const [stages, setStages] = useState<SleepStagesResult | null>(null);
  const [benchmark, setBenchmark] = useState<BenchmarkResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getStudy(id).then((s) => {
      setStudy(s);
      if (s.source === "public") api.getDataset(s.dataset_id).then(setDataset).catch(() => setDataset(null));
    }).catch(() => setError("Could not load this study."));
    api.getStudyQc(id).then(setQc).catch(() => setQc(null));
    api.getRespiratoryEvents(id).then(setEvents).catch(() => setEvents(null));
    api.getOxygenBurden(id).then(setOxygen).catch(() => setOxygen(null));
    api.getSleepStages(id).then(setStages).catch(() => setStages(null));
    api.getBenchmark(id).then(setBenchmark).catch(() => setBenchmark(null));
  }, [id]);

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!study) return <p className="text-sm text-slate-400">Assembling report…</p>;

  return (
    <div className="mx-auto max-w-3xl bg-white p-6 print:p-0">
      <div className="no-print mb-4 flex justify-end">
        <button
          onClick={() => window.print()}
          className="inline-flex items-center gap-1.5 rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          <Printer className="h-4 w-4" /> Print / Save as PDF
        </button>
      </div>

      <header className="border-b-2 border-slate-900 pb-3">
        <div className="text-xs font-medium uppercase tracking-wide text-slate-400">
          NeuroSleep Twin — Research Report
        </div>
        <h1 className="mt-1 text-2xl font-semibold text-slate-900">
          {study.display_name || study.record_name}
        </h1>
        <p className="mt-1 text-xs text-slate-500">
          Generated {new Date().toLocaleString()} · Research prototype output — not a clinical
          report. Does not diagnose sleep apnea or any neurological disease.
        </p>
      </header>

      <Section title="Provenance">
        <table className="w-full text-xs">
          <tbody className="divide-y divide-slate-100">
            <tr>
              <td className="w-40 py-1 text-slate-400">Source</td>
              <td className="py-1 text-slate-700">{study.source === "public" ? dataset?.source ?? study.dataset_id : "User upload"}</td>
            </tr>
            {dataset && (
              <>
                <tr>
                  <td className="py-1 text-slate-400">Dataset</td>
                  <td className="py-1 text-slate-700">
                    {dataset.name} v{dataset.version}
                  </td>
                </tr>
                <tr>
                  <td className="py-1 text-slate-400">License</td>
                  <td className="py-1 text-slate-700">{dataset.license}</td>
                </tr>
                <tr>
                  <td className="py-1 text-slate-400">Citation</td>
                  <td className="py-1 text-slate-700">{dataset.citation}</td>
                </tr>
              </>
            )}
            <tr>
              <td className="py-1 text-slate-400">Record / upload id</td>
              <td className="py-1 font-mono text-slate-700">{study.record_name}</td>
            </tr>
            <tr>
              <td className="py-1 text-slate-400">Duration</td>
              <td className="py-1 text-slate-700">{study.duration_sec ? `${Math.round(study.duration_sec / 60)} min` : "—"}</td>
            </tr>
            <tr>
              <td className="py-1 text-slate-400">Event-detection algorithm</td>
              <td className="py-1 font-mono text-slate-700">{events?.algorithm_version ?? "n/a"}</td>
            </tr>
          </tbody>
        </table>
      </Section>

      <Section title="Channels & Signal QC">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-slate-400">
              <th className="py-1 font-normal">Channel</th>
              <th className="py-1 font-normal">Type</th>
              <th className="py-1 font-normal">Rate</th>
              <th className="py-1 font-normal">QC score</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {study.channels.map((c) => {
              const q = qc?.channels.find((x) => x.channel_id === c.id);
              return (
                <tr key={c.id}>
                  <td className="py-1 text-slate-700">{c.name}</td>
                  <td className="py-1 text-slate-600">{c.signal_type ?? "unmapped"}</td>
                  <td className="py-1 text-slate-600">{c.sampling_rate} Hz</td>
                  <td className="py-1 text-slate-600">{q ? `${q.score} (${q.label})` : "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {qc && <p className="mt-1 text-xs text-slate-500">Overall readiness: {qc.overall_score} ({qc.overall_label})</p>}
      </Section>

      <Section title="Respiratory Events">
        {events?.available && events.summary ? (
          <p className="text-xs text-slate-700">
            {events.summary.count} candidate events ({events.summary.apnea_count} apnea-like,{" "}
            {events.summary.hypopnea_count} hypopnea-like) — {events.summary.events_per_hour}{" "}
            events/hour. Machine-learning estimate, not a clinical scoring.
          </p>
        ) : (
          <p className="text-xs text-slate-500">{events?.message ?? "Not available."}</p>
        )}
      </Section>

      <Section title="Oxygen Burden">
        {oxygen?.available && oxygen.summary ? (
          <p className="text-xs text-slate-700">
            Mean SpO2 {oxygen.summary.mean_spo2}%, minimum {oxygen.summary.min_spo2}%,{" "}
            {oxygen.summary.pct_time_below_90}% of the recording below 90%. ODI{" "}
            {oxygen.summary.odi} dips/hour ({oxygen.summary.artifact_pct}% sensor dropout cleaned).
          </p>
        ) : (
          <p className="text-xs text-slate-500">{oxygen?.message ?? "Not available."}</p>
        )}
      </Section>

      <Section title="Sleep Staging">
        {stages?.available ? (
          <p className="text-xs text-slate-700">
            {Object.entries(stages.stage_minutes)
              .map(([k, v]) => `${k} ${v}min`)
              .join(", ")}
            . From the dataset's own ground-truth annotations.
          </p>
        ) : (
          <p className="text-xs text-slate-500">{stages?.message ?? "Not available."}</p>
        )}
      </Section>

      <Section title="Benchmark vs. Ground Truth">
        {benchmark?.available && benchmark.confusion ? (
          <p className="text-xs text-slate-700">
            Sensitivity {benchmark.sensitivity}, specificity {benchmark.specificity}, precision{" "}
            {benchmark.precision}, AUROC {benchmark.auroc ?? "n/a"}, AUPRC {benchmark.auprc ?? "n/a"} across{" "}
            {benchmark.n_epochs} epochs ({benchmark.n_positive_epochs} ground-truth positive).
          </p>
        ) : (
          <p className="text-xs text-slate-500">{benchmark?.message ?? "Not available."}</p>
        )}
      </Section>

      <footer className="mt-8 border-t border-slate-200 pt-2 text-[10px] text-slate-400">
        NeuroSleep Twin is a research prototype. It does not independently diagnose obstructive
        sleep apnea or neurological disease, and does not replace professional interpretation of
        polysomnography or other medical assessments.
      </footer>
    </div>
  );
}
