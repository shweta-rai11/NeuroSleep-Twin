import {
  Activity,
  ArrowRight,
  Database,
  FileText,
  Fingerprint,
  Layers,
  Sparkles,
  UploadCloud,
  Waves,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api, type HealthStatus } from "@/api/client";
import { Card } from "@/components/layout/Card";
import type { DatasetEntry } from "@/types/dataset";
import type { StudyListItem } from "@/types/study";

const PIPELINE_STEPS = [
  { icon: Database, label: "Ingest", detail: "Public dataset or your upload" },
  { icon: Layers, label: "Map & QC", detail: "Channels identified, signal validated" },
  { icon: Waves, label: "Stage & Detect", detail: "Hypnogram + candidate events" },
  { icon: Fingerprint, label: "Fingerprint", detail: "Per-event neuro-respiratory vector" },
  { icon: Sparkles, label: "Phenotype", detail: "Cluster into descriptive profiles" },
  { icon: FileText, label: "Report", detail: "Exportable, fully versioned" },
];

function formatDuration(sec: number | null): string {
  if (!sec) return "";
  const h = Math.floor(sec / 3600);
  const m = Math.round((sec % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [healthError, setHealthError] = useState(false);
  const [datasets, setDatasets] = useState<DatasetEntry[] | null>(null);
  const [studies, setStudies] = useState<StudyListItem[] | null>(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealthError(true));
    api.listDatasets().then(setDatasets).catch(() => setDatasets([]));
    api.listStudies().then(setStudies).catch(() => setStudies([]));
  }, []);

  const ingestedStudies = (studies ?? []).filter((s) => s.status === "ingested");

  return (
    <div className="mx-auto max-w-5xl space-y-10 pb-10">
      {/* Hero */}
      <section className="overflow-hidden rounded-2xl bg-gradient-to-br from-brand-900 via-brand-800 to-brand-950 px-8 py-12 text-white shadow-sm">
        <div className="flex items-center gap-2 text-xs font-medium text-brand-200">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
          {healthError ? "Backend unreachable" : health ? `${health.service} — live` : "Connecting…"}
        </div>
        <h1 className="mt-3 max-w-2xl text-3xl font-semibold tracking-tight sm:text-4xl">
          Mapping how the sleeping brain responds to disrupted breathing.
        </h1>
        <p className="mt-4 max-w-2xl text-sm leading-6 text-brand-100">
          A computational neuroscience platform for investigating how respiratory disturbances
          during sleep interact with cortical, autonomic, oxygenation, and recovery dynamics —
          event-level neuro-respiratory phenotyping, not event counting alone.
        </p>
        <div className="mt-7 flex flex-wrap gap-3">
          <Link
            to="/datasets"
            className="inline-flex items-center gap-1.5 rounded-md bg-white px-4 py-2 text-sm font-medium text-brand-900 hover:bg-brand-50"
          >
            <Database className="h-4 w-4" />
            Explore Public Dataset
          </Link>
          <Link
            to="/upload"
            className="inline-flex items-center gap-1.5 rounded-md border border-white/30 px-4 py-2 text-sm font-medium text-white hover:bg-white/10"
          >
            <UploadCloud className="h-4 w-4" />
            Upload Your Sleep Study
          </Link>
        </div>
      </section>

      {/* Stats */}
      <section className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card className="text-center">
          <div className="text-2xl font-semibold text-slate-900">{datasets?.length ?? "—"}</div>
          <div className="mt-1 text-xs text-slate-500">Public datasets</div>
        </Card>
        <Card className="text-center">
          <div className="text-2xl font-semibold text-slate-900">
            {datasets?.reduce((n, d) => n + d.num_records, 0) ?? "—"}
          </div>
          <div className="mt-1 text-xs text-slate-500">Records available</div>
        </Card>
        <Card className="text-center">
          <div className="text-2xl font-semibold text-slate-900">{ingestedStudies.length}</div>
          <div className="mt-1 text-xs text-slate-500">Studies ingested</div>
        </Card>
        <Card className="text-center">
          <div className="text-2xl font-semibold text-slate-900">
            {health ? "Online" : healthError ? "Offline" : "…"}
          </div>
          <div className="mt-1 text-xs text-slate-500">API status</div>
        </Card>
      </section>

      {/* Pipeline */}
      <section>
        <h2 className="text-sm font-semibold text-slate-900">One shared analysis pipeline</h2>
        <p className="mt-1 text-sm text-slate-500">
          Public data and your own uploads run through the exact same stages, so results are
          always comparable.
        </p>
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {PIPELINE_STEPS.map((step, i) => (
            <div key={step.label} className="rounded-lg border border-slate-200 bg-white p-3">
              <div className="flex items-center gap-2">
                <div className="flex h-7 w-7 items-center justify-center rounded-md bg-brand-50 text-brand-700">
                  <step.icon className="h-4 w-4" />
                </div>
                <span className="text-[11px] font-medium text-slate-400">
                  {String(i + 1).padStart(2, "0")}
                </span>
              </div>
              <div className="mt-2 text-xs font-semibold text-slate-900">{step.label}</div>
              <div className="mt-0.5 text-[11px] leading-4 text-slate-500">{step.detail}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Recent studies */}
      {ingestedStudies.length > 0 && (
        <section>
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">Recent studies</h2>
            <Link to="/viewer" className="text-xs font-medium text-brand-600 hover:underline">
              View all
            </Link>
          </div>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            {ingestedStudies.slice(0, 4).map((s) => (
              <Link key={s.id} to={`/viewer/${s.id}`}>
                <Card className="flex items-center justify-between transition-colors hover:border-brand-300">
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-md bg-slate-100 text-slate-500">
                      <Activity className="h-4 w-4" />
                    </div>
                    <div>
                      <div className="text-sm font-medium text-slate-900">{s.record_name}</div>
                      <div className="text-xs text-slate-500">
                        {s.dataset_id} · {formatDuration(s.duration_sec)}
                      </div>
                    </div>
                  </div>
                  <ArrowRight className="h-4 w-4 text-slate-300" />
                </Card>
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
