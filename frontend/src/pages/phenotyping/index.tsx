import { Pencil } from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "@/api/client";
import { RadarChart } from "@/components/fingerprint/RadarChart";
import { Card } from "@/components/layout/Card";
import type { PhenotypesResult } from "@/types/study";

const CLUSTER_COLORS = ["#2748d8", "#dc2626", "#059669", "#d97706", "#7c3aed", "#0891b2", "#db2777", "#65a30d"];

const AXIS_LABELS: Record<string, string> = {
  severity: "Severity", duration: "Duration", desaturation: "Desaturation",
  hr_response: "HR response", arousal: "Arousal",
};

export default function PhenotypingPage() {
  const [k, setK] = useState(3);
  const [result, setResult] = useState<PhenotypesResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editingCluster, setEditingCluster] = useState<number | null>(null);
  const [draftLabel, setDraftLabel] = useState("");

  useEffect(() => {
    setResult(null);
    api.getPhenotypes(k).then(setResult).catch(() => setError("Could not run phenotype clustering."));
  }, [k]);

  async function saveLabel(clusterIndex: number) {
    if (!draftLabel.trim()) {
      setEditingCluster(null);
      return;
    }
    await api.renameCluster(k, clusterIndex, draftLabel.trim());
    setResult((prev) =>
      prev
        ? { ...prev, clusters: prev.clusters.map((c) => (c.cluster_index === clusterIndex ? { ...c, label: draftLabel.trim() } : c)) }
        : prev,
    );
    setEditingCluster(null);
  }

  if (error) return <p className="text-sm text-red-600">{error}</p>;

  return (
    <div className="mx-auto max-w-4xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Phenotyping</h1>
          <p className="mt-1 text-sm text-slate-600">
            Unsupervised clustering of every detected event's fingerprint into descriptive,
            renamable neuro-respiratory phenotypes — across all ingested studies. Not diagnostic
            subtypes.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-slate-500">Clusters (k)</label>
          <select
            value={k}
            onChange={(e) => setK(Number(e.target.value))}
            className="rounded-md border border-slate-300 px-2 py-1 text-xs"
          >
            {[2, 3, 4, 5, 6].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </div>
      </div>

      {!result && <p className="mt-4 text-sm text-slate-400">Clustering…</p>}

      {result && !result.available && (
        <Card className="mt-4">
          <p className="text-sm text-slate-600">{result.message}</p>
        </Card>
      )}

      {result?.available && (
        <>
          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {result.clusters.map((c) => (
              <Card key={c.cluster_index}>
                <div className="flex items-center justify-between gap-2">
                  {editingCluster === c.cluster_index ? (
                    <input
                      autoFocus
                      value={draftLabel}
                      onChange={(e) => setDraftLabel(e.target.value)}
                      onBlur={() => saveLabel(c.cluster_index)}
                      onKeyDown={(e) => e.key === "Enter" && saveLabel(c.cluster_index)}
                      className="w-full rounded border border-slate-300 px-1.5 py-0.5 text-sm"
                    />
                  ) : (
                    <div className="flex items-center gap-1.5">
                      <span
                        className="h-2.5 w-2.5 shrink-0 rounded-full"
                        style={{ backgroundColor: CLUSTER_COLORS[c.cluster_index % CLUSTER_COLORS.length] }}
                      />
                      <span className="text-sm font-semibold text-slate-900">{c.label}</span>
                      <button
                        onClick={() => {
                          setEditingCluster(c.cluster_index);
                          setDraftLabel(c.label);
                        }}
                        className="text-slate-300 hover:text-slate-500"
                      >
                        <Pencil className="h-3 w-3" />
                      </button>
                    </div>
                  )}
                  <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
                    {c.size} events
                  </span>
                </div>
                <div className="flex justify-center">
                  <RadarChart
                    size={180}
                    axes={result.axes.map((a, i) => ({ label: AXIS_LABELS[a] ?? a, value: c.centroid[i] }))}
                  />
                </div>
              </Card>
            ))}
          </div>

          <Card className="mt-4 overflow-hidden !p-0">
            <div className="border-b border-slate-100 px-4 py-2 text-xs font-medium text-slate-500">
              All {result.events.length} events by phenotype
            </div>
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-2">Study</th>
                  <th className="px-4 py-2">Onset</th>
                  <th className="px-4 py-2">Type</th>
                  <th className="px-4 py-2">Phenotype</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {result.events.map((e) => {
                  const cluster = result.clusters.find((c) => c.cluster_index === e.cluster_index);
                  return (
                    <tr key={e.event_id}>
                      <td className="px-4 py-2 text-slate-700">{e.study_label}</td>
                      <td className="px-4 py-2 font-mono text-xs text-slate-600">{Math.round(e.onset_sec)}s</td>
                      <td className="px-4 py-2 text-slate-600">{e.event_type}</td>
                      <td className="px-4 py-2">
                        <span className="inline-flex items-center gap-1.5">
                          <span
                            className="h-2 w-2 rounded-full"
                            style={{ backgroundColor: CLUSTER_COLORS[e.cluster_index % CLUSTER_COLORS.length] }}
                          />
                          {cluster?.label}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Card>
        </>
      )}
    </div>
  );
}
