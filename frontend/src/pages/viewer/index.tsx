import { Trash2 } from "lucide-react";
import { type MouseEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import { Card } from "@/components/layout/Card";
import type { StudyListItem } from "@/types/study";

export default function ViewerIndexPage() {
  const [studies, setStudies] = useState<StudyListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  useEffect(() => {
    api
      .listStudies()
      .then(setStudies)
      .catch(() => setError("Could not reach the API. Is the backend running on :8000?"));
  }, []);

  const ingested = studies?.filter((s) => s.status === "ingested") ?? [];

  async function handleDelete(e: MouseEvent, id: number) {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm("Delete this study and its data? This cannot be undone.")) return;
    setDeletingId(id);
    try {
      await api.deleteStudy(id);
      setStudies((prev) => prev?.filter((s) => s.id !== id) ?? null);
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-xl font-semibold text-slate-900">Signal Viewer & Night Map</h1>
      <p className="mt-1 text-sm text-slate-600">
        A synchronized, zoomable multi-channel viewer over real ingested recordings.
      </p>

      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

      {studies && ingested.length === 0 && (
        <Card className="mt-4">
          <p className="text-sm text-slate-600">
            No studies ingested yet. Go to{" "}
            <Link to="/datasets" className="text-brand-600 hover:underline">
              Public Datasets
            </Link>{" "}
            and pick a record to explore — it downloads once, then opens straight into this
            viewer.
          </p>
        </Card>
      )}

      <div className="mt-4 space-y-2">
        {ingested.map((s) => (
          <Link key={s.id} to={`/viewer/${s.id}`}>
            <Card className="transition-colors hover:border-brand-300">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-semibold text-slate-900">
                    {s.display_name || s.record_name}
                  </div>
                  <div className="text-xs text-slate-500">
                    {s.dataset_id} {s.source === "upload" && "· uploaded"}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-xs text-slate-500">
                    {s.duration_sec ? `${Math.round(s.duration_sec / 60)} min` : ""}
                  </div>
                  <button
                    onClick={(e) => handleDelete(e, s.id)}
                    disabled={deletingId === s.id}
                    title="Delete this study and its data"
                    className="text-slate-300 hover:text-red-500 disabled:opacity-40"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
