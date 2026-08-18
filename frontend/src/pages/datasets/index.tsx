import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "@/api/client";
import { Card } from "@/components/layout/Card";
import type { DatasetEntry } from "@/types/dataset";
import type { StudyListItem } from "@/types/study";

const POLL_INTERVAL_MS = 2000;

export default function DatasetsPage() {
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState<DatasetEntry[] | null>(null);
  const [studies, setStudies] = useState<StudyListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ingestingRecord, setIngestingRecord] = useState<string | null>(null);
  const [ingestError, setIngestError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listDatasets()
      .then(setDatasets)
      .catch(() => setError("Could not load the dataset catalog. Is the backend running on :8000?"));
    api.listStudies().then(setStudies).catch(() => setStudies([]));
  }, []);

  async function exploreRecord(datasetId: string, recordName: string) {
    setIngestError(null);

    const alreadyIngested = studies?.find(
      (s) => s.dataset_id === datasetId && s.record_name === recordName && s.status === "ingested",
    );
    if (alreadyIngested) {
      navigate(`/viewer/${alreadyIngested.id}`);
      return;
    }

    setIngestingRecord(recordName);
    try {
      const job = await api.ingestRecord(datasetId, recordName);
      let taskId = job.task_id;
      // eslint-disable-next-line no-constant-condition
      while (true) {
        await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
        const status = await api.getIngestJob(taskId);
        if (status.status === "ready" && status.study_id) {
          navigate(`/viewer/${status.study_id}`);
          return;
        }
        if (status.status === "error" || status.status === "failure") {
          setIngestError(status.error ?? "Ingestion failed.");
          setIngestingRecord(null);
          return;
        }
      }
    } catch {
      setIngestError("Could not reach the backend to start ingestion.");
      setIngestingRecord(null);
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-xl font-semibold text-slate-900">Public Datasets</h1>
      <p className="mt-1 text-sm text-slate-600">
        Datasets are only ever pulled from official, institutionally maintained sources with
        clear licenses. Every entry below shows its real provenance.
      </p>

      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
      {!error && !datasets && <p className="mt-4 text-sm text-slate-400">Loading…</p>}

      <div className="mt-4 space-y-4">
        {datasets?.map((d) => (
          <Card key={d.id}>
            <div>
              <div className="text-sm font-semibold text-slate-900">{d.name}</div>
              <p className="mt-1 text-sm text-slate-600">{d.short_description}</p>
            </div>
            <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs sm:grid-cols-3">
              <div>
                <dt className="text-slate-400">Source</dt>
                <dd className="text-slate-700">{d.source}</dd>
              </div>
              <div>
                <dt className="text-slate-400">Version</dt>
                <dd className="text-slate-700">{d.version}</dd>
              </div>
              <div>
                <dt className="text-slate-400">Records</dt>
                <dd className="text-slate-700">{d.num_records}</dd>
              </div>
              <div className="col-span-2 sm:col-span-3">
                <dt className="text-slate-400">License</dt>
                <dd className="text-slate-700">{d.license}</dd>
              </div>
              <div className="col-span-2 sm:col-span-3">
                <dt className="text-slate-400">Citation</dt>
                <dd className="text-slate-700">{d.citation}</dd>
              </div>
              <div className="col-span-2 sm:col-span-3">
                <dt className="text-slate-400">Source URL</dt>
                <dd>
                  <a
                    className="text-brand-600 hover:underline"
                    href={d.source_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {d.source_url}
                  </a>
                </dd>
              </div>
            </dl>

            <div className="mt-4 border-t border-slate-100 pt-4">
              <div className="text-xs font-medium text-slate-500">
                Explore a record — downloads directly from {d.source} on first use.
              </div>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {d.record_names.map((recordName) => {
                  const ingested = studies?.some(
                    (s) => s.dataset_id === d.id && s.record_name === recordName && s.status === "ingested",
                  );
                  const isBusy = ingestingRecord === recordName;
                  return (
                    <button
                      key={recordName}
                      onClick={() => exploreRecord(d.id, recordName)}
                      disabled={isBusy}
                      className={
                        ingested
                          ? "rounded-md bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700 hover:bg-emerald-100"
                          : "rounded-md bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-200 disabled:cursor-wait disabled:opacity-60"
                      }
                    >
                      {isBusy ? `${recordName} — downloading…` : recordName}
                    </button>
                  );
                })}
              </div>
              {ingestError && <p className="mt-2 text-xs text-red-600">{ingestError}</p>}
              <p className="mt-2 text-xs text-slate-400">
                Green = already ingested and ready to view. First download of a record can take
                a minute or two (real PhysioNet data, ~2 hours of multi-channel signal).
              </p>
            </div>
          </Card>
        ))}
      </div>

      <p className="mt-4 text-xs text-slate-400">Additional datasets — coming soon.</p>
    </div>
  );
}
