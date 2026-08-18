import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import { Card } from "@/components/layout/Card";
import type { StudyListItem } from "@/types/study";

export function StudyPicker({ basePath }: { basePath: string }) {
  const [studies, setStudies] = useState<StudyListItem[] | null>(null);

  useEffect(() => {
    api.listStudies().then(setStudies).catch(() => setStudies([]));
  }, []);

  const ingested = studies?.filter((s) => s.status === "ingested") ?? [];

  if (studies && ingested.length === 0) {
    return (
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
    );
  }

  return (
    <div className="mt-4 space-y-2">
      {ingested.map((s) => (
        <Link key={s.id} to={`${basePath}/${s.id}`}>
          <Card className="flex items-center justify-between transition-colors hover:border-brand-300">
            <div>
              <div className="text-sm font-semibold text-slate-900">
                {s.display_name || s.record_name}
              </div>
              <div className="text-xs text-slate-500">{s.dataset_id}</div>
            </div>
          </Card>
        </Link>
      ))}
    </div>
  );
}
