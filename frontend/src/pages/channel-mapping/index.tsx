import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import { Card } from "@/components/layout/Card";
import type { StudyListItem } from "@/types/study";

export default function ChannelMappingIndexPage() {
  const [studies, setStudies] = useState<StudyListItem[] | null>(null);

  useEffect(() => {
    api.listStudies().then(setStudies).catch(() => setStudies([]));
  }, []);

  const ingested = studies?.filter((s) => s.status === "ingested") ?? [];

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-xl font-semibold text-slate-900">Channel Mapping</h1>
      <p className="mt-1 text-sm text-slate-600">
        Pick a study to review its confidence-scored channel mapping.
      </p>

      {studies && ingested.length === 0 && (
        <Card className="mt-4">
          <p className="text-sm text-slate-600">
            No studies yet — ingest a{" "}
            <Link to="/datasets" className="text-brand-600 hover:underline">
              public record
            </Link>{" "}
            or{" "}
            <Link to="/upload" className="text-brand-600 hover:underline">
              upload your own
            </Link>
            .
          </p>
        </Card>
      )}

      <div className="mt-4 space-y-2">
        {ingested.map((s) => (
          <Link key={s.id} to={`/channel-mapping/${s.id}`}>
            <Card className="flex items-center justify-between transition-colors hover:border-brand-300">
              <div>
                <div className="text-sm font-semibold text-slate-900">
                  {s.display_name || s.record_name}
                </div>
                <div className="text-xs text-slate-500">{s.dataset_id}</div>
              </div>
              <span
                className={
                  s.channel_mapping_confirmed
                    ? "rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700"
                    : "rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700"
                }
              >
                {s.channel_mapping_confirmed ? "Confirmed" : "Needs review"}
              </span>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
