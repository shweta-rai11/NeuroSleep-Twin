import { StudyPicker } from "@/components/layout/StudyPicker";

export default function QcIndexPage() {
  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-xl font-semibold text-slate-900">Signal QC</h1>
      <p className="mt-1 text-sm text-slate-600">
        Pick a study for a research signal-quality assessment and readiness score.
      </p>
      <StudyPicker basePath="/qc" />
    </div>
  );
}
