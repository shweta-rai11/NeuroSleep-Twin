import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { api } from "@/api/client";
import { CurveChart } from "@/components/charts/CurveChart";
import { Card } from "@/components/layout/Card";
import type { BenchmarkResult, StudyDetail } from "@/types/study";

function Metric({ label, value }: { label: string; value: number | null }) {
  return (
    <Card className="text-center">
      <div className="text-2xl font-semibold text-slate-900">
        {value != null ? value.toFixed(3) : "—"}
      </div>
      <div className="mt-1 text-xs text-slate-500">{label}</div>
    </Card>
  );
}

export default function StudyBenchmark() {
  const { studyId } = useParams<{ studyId: string }>();
  const id = Number(studyId);

  const [study, setStudy] = useState<StudyDetail | null>(null);
  const [result, setResult] = useState<BenchmarkResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getStudy(id).then(setStudy).catch(() => setError("Could not load this study."));
    api.getBenchmark(id).then(setResult).catch(() => setError("Could not compute benchmark."));
  }, [id]);

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!study || !result) return <p className="text-sm text-slate-400">Scoring against ground truth…</p>;

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-xl font-semibold text-slate-900">Benchmark Lab</h1>
      <p className="mt-1 text-sm text-slate-600">
        {study.display_name || study.record_name} — candidate respiratory events vs. this
        recording's own ground-truth epoch annotations (H/HA/OA/X/CA/CAA, sourced from PhysioNet's
        slpdb documentation). Evaluated at 30s-epoch resolution — the dataset's ground truth
        doesn't carry precise onset/offset times.
      </p>

      {!result.available && (
        <Card className="mt-4">
          <p className="text-sm text-slate-600">{result.message}</p>
        </Card>
      )}

      {result.available && result.confusion && (
        <>
          {result.message && (
            <Card className="mt-4 border-amber-200 bg-amber-50">
              <p className="text-xs text-amber-800">{result.message}</p>
            </Card>
          )}

          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-5">
            <Metric label="Sensitivity" value={result.sensitivity} />
            <Metric label="Specificity" value={result.specificity} />
            <Metric label="Precision" value={result.precision} />
            <Metric label="AUROC" value={result.auroc} />
            <Metric label="AUPRC" value={result.auprc} />
          </div>

          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <Card>
              <div className="mb-2 text-xs font-medium text-slate-500">
                Confusion matrix — {result.n_epochs} epochs ({result.n_positive_epochs} ground-truth
                positive)
              </div>
              <table className="w-full text-center text-sm">
                <tbody>
                  <tr>
                    <td />
                    <td className="pb-1 text-xs text-slate-400">GT positive</td>
                    <td className="pb-1 text-xs text-slate-400">GT negative</td>
                  </tr>
                  <tr>
                    <td className="pr-1 text-xs text-slate-400">Pred +</td>
                    <td className="rounded bg-emerald-50 py-3 font-semibold text-emerald-700">
                      {result.confusion.tp}
                    </td>
                    <td className="rounded bg-red-50 py-3 font-semibold text-red-700">
                      {result.confusion.fp}
                    </td>
                  </tr>
                  <tr>
                    <td className="pr-1 text-xs text-slate-400">Pred −</td>
                    <td className="rounded bg-red-50 py-3 font-semibold text-red-700">
                      {result.confusion.fn}
                    </td>
                    <td className="rounded bg-emerald-50 py-3 font-semibold text-emerald-700">
                      {result.confusion.tn}
                    </td>
                  </tr>
                </tbody>
              </table>
            </Card>

            {result.roc_curve && (
              <Card>
                <div className="mb-2 text-xs font-medium text-slate-500">ROC curve</div>
                <div className="flex justify-center">
                  <CurveChart x={result.roc_curve.x} y={result.roc_curve.y} xLabel="FPR" yLabel="TPR" diagonal />
                </div>
              </Card>
            )}

            {result.pr_curve && (
              <Card>
                <div className="mb-2 text-xs font-medium text-slate-500">Precision-Recall curve</div>
                <div className="flex justify-center">
                  <CurveChart x={result.pr_curve.x} y={result.pr_curve.y} xLabel="Recall" yLabel="Precision" />
                </div>
              </Card>
            )}

            {result.calibration_predicted.length > 1 && (
              <Card>
                <div className="mb-2 text-xs font-medium text-slate-500">Calibration</div>
                <div className="flex justify-center">
                  <CurveChart
                    x={result.calibration_predicted}
                    y={result.calibration_observed}
                    xLabel="Predicted"
                    yLabel="Observed"
                    diagonal
                  />
                </div>
              </Card>
            )}
          </div>
        </>
      )}
    </div>
  );
}
