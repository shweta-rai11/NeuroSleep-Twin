import { AlertTriangle, ArrowRight } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "@/api/client";
import { Card } from "@/components/layout/Card";
import type { ChannelQc, StudyDetail, StudyQc as StudyQcType } from "@/types/study";

function scoreColor(score: number): string {
  if (score >= 85) return "text-emerald-600";
  if (score >= 70) return "text-lime-600";
  if (score >= 50) return "text-amber-600";
  return "text-red-600";
}

function scoreRingColor(score: number): string {
  if (score >= 85) return "#059669";
  if (score >= 70) return "#65a30d";
  if (score >= 50) return "#d97706";
  return "#dc2626";
}

function ScoreRing({ score }: { score: number }) {
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - score / 100);
  return (
    <svg width="100" height="100" viewBox="0 0 100 100">
      <circle cx="50" cy="50" r={radius} fill="none" stroke="#e2e8f0" strokeWidth="10" />
      <circle
        cx="50"
        cy="50"
        r={radius}
        fill="none"
        stroke={scoreRingColor(score)}
        strokeWidth="10"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        transform="rotate(-90 50 50)"
      />
      <text x="50" y="55" textAnchor="middle" fontSize="22" fontWeight="600" fill="#0f172a">
        {Math.round(score)}
      </text>
    </svg>
  );
}

function MetricBar({ label, value, unit = "%" }: { label: string; value: number; unit?: string }) {
  const pct = Math.min(100, value);
  return (
    <div>
      <div className="flex justify-between text-[11px] text-slate-500">
        <span>{label}</span>
        <span>
          {value.toFixed(unit === "%" ? 2 : 3)}
          {unit}
        </span>
      </div>
      <div className="mt-0.5 h-1.5 rounded-full bg-slate-100">
        <div
          className="h-1.5 rounded-full bg-slate-400"
          style={{ width: `${unit === "%" ? pct : Math.min(100, value * 20)}%` }}
        />
      </div>
    </div>
  );
}

function ChannelQcCard({ channel }: { channel: ChannelQc }) {
  return (
    <Card>
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm font-semibold text-slate-900">{channel.name}</div>
          <div className="text-xs text-slate-400">{channel.signal_type ?? "unmapped"}</div>
        </div>
        <div className={`text-lg font-semibold ${scoreColor(channel.score)}`}>
          {channel.score.toFixed(0)}
          <span className="ml-1 text-xs font-normal text-slate-400">{channel.label}</span>
        </div>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2">
        <MetricBar label="Missing" value={channel.missing_pct} />
        <MetricBar label="Flatline" value={channel.flatline_pct} />
        <MetricBar label="Clipping" value={channel.clipping_pct} />
        <MetricBar label="Artifacts" value={channel.artifact_pct} />
        <MetricBar label="Baseline drift" value={channel.drift_score} unit="" />
      </div>
      {channel.issues.length > 0 && (
        <ul className="mt-3 space-y-1 border-t border-slate-100 pt-2">
          {channel.issues.map((issue) => (
            <li key={issue} className="flex items-start gap-1.5 text-xs text-amber-700">
              <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" />
              {issue}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export default function StudyQcPage() {
  const { studyId } = useParams<{ studyId: string }>();
  const id = Number(studyId);

  const [study, setStudy] = useState<StudyDetail | null>(null);
  const [qc, setQc] = useState<StudyQcType | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getStudy(id).then(setStudy).catch(() => setError("Could not load this study."));
    api.getStudyQc(id).then(setQc).catch(() => setError("Could not compute QC for this study."));
  }, [id]);

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!study || !qc) return <p className="text-sm text-slate-400">Computing signal quality…</p>;

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-xl font-semibold text-slate-900">Signal QC</h1>
      <p className="mt-1 text-sm text-slate-600">
        {study.display_name || study.record_name} — research signal-quality assessment, not a
        clinical-quality certification.
      </p>

      <Card className="mt-4 flex items-center gap-6">
        <ScoreRing score={qc.overall_score} />
        <div>
          <div className={`text-sm font-semibold ${scoreColor(qc.overall_score)}`}>
            {qc.overall_label} readiness
          </div>
          <p className="mt-1 max-w-md text-xs text-slate-500">
            Averaged across all {qc.channels.length} channels — missingness, flatline runs,
            clipping/saturation, baseline drift, and extreme-outlier artifacts, computed directly
            from the stored waveform.
          </p>
        </div>
      </Card>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {qc.channels.map((c) => (
          <ChannelQcCard key={c.channel_id} channel={c} />
        ))}
      </div>

      <div className="mt-4 flex justify-end">
        <Link
          to={`/viewer/${id}`}
          className="inline-flex items-center gap-1.5 rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          Continue to Viewer <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </div>
  );
}
