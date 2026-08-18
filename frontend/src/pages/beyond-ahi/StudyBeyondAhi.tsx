import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { api } from "@/api/client";
import { Card } from "@/components/layout/Card";
import type { BeyondAhiResult, BurdenMetric, StudyDetail } from "@/types/study";

function MetricCard({
  label,
  unit,
  metric,
  accent = "text-slate-900",
}: {
  label: string;
  unit: string;
  metric: BurdenMetric | null;
  accent?: string;
}) {
  return (
    <Card className="text-center">
      {metric?.available && metric.value != null ? (
        <>
          <div className={`text-2xl font-semibold ${accent}`}>
            {metric.value}
            <span className="ml-1 text-sm font-normal text-slate-400">{unit}</span>
          </div>
          <div className="mt-1 text-xs text-slate-500">{label}</div>
        </>
      ) : (
        <>
          <div className="text-2xl font-semibold text-slate-300">—</div>
          <div className="mt-1 text-xs text-slate-500">{label}</div>
          <div className="mt-1 text-[11px] text-slate-400">{metric?.message ?? "Not available"}</div>
        </>
      )}
    </Card>
  );
}

export default function StudyBeyondAhi() {
  const { studyId } = useParams<{ studyId: string }>();
  const id = Number(studyId);

  const [study, setStudy] = useState<StudyDetail | null>(null);
  const [result, setResult] = useState<BeyondAhiResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getStudy(id).then(setStudy).catch(() => setError("Could not load this study."));
    api.getBeyondAhi(id).then(setResult).catch(() => setError("Could not compute Beyond AHI."));
  }, [id]);

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!study || !result) return <p className="text-sm text-slate-400">Comparing burden dimensions…</p>;

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-xl font-semibold text-slate-900">Beyond AHI</h1>
      <p className="mt-1 text-sm text-slate-600">
        {study.display_name || study.record_name} — AHI next to oxygen, arousal, autonomic, and recovery
        burden. This is <span className="font-medium text-slate-700">exploring physiology alongside AHI</span>,
        not replacing it: two nights with the same AHI can carry very different burden below.
      </p>

      {!result.available && (
        <Card className="mt-4">
          <p className="text-sm text-slate-600">{result.message}</p>
        </Card>
      )}

      {result.available && (
        <>
          <Card className="mt-4 text-center">
            <div className="text-3xl font-semibold text-slate-900">
              {result.ahi?.value}
              <span className="ml-1 text-base font-normal text-slate-400">events/hr</span>
            </div>
            <div className="mt-1 text-xs font-medium uppercase tracking-wide text-slate-500">
              AHI-equivalent (candidate events/hour)
            </div>
          </Card>

          <div className="mt-3 text-xs font-medium uppercase tracking-wide text-slate-400">
            Burden alongside it
          </div>
          <div className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-3">
            <MetricCard label="ODI (dips/hr)" unit="" metric={result.odi} />
            <MetricCard label="Time below 90% SpO2" unit="%" metric={result.oxygen_time_below_90} accent="text-red-600" />
            <MetricCard label="Mean desaturation depth" unit="%" metric={result.oxygen_mean_desaturation} />
            <MetricCard label="Arousal burden (mean probability)" unit="" metric={result.arousal_burden} />
            <MetricCard label="Autonomic burden (mean HR response)" unit="bpm" metric={result.autonomic_burden} />
            <MetricCard label="Recovery burden (mean time to recover)" unit="s" metric={result.recovery_burden} />
          </div>

          <p className="mt-4 text-xs text-slate-400">
            Each dimension only appears when its channel is mapped for this study — a dash means "not
            measured here," never a computed zero.
          </p>
        </>
      )}
    </div>
  );
}
