import { StudyPicker } from "@/components/layout/StudyPicker";

export default function ReportsIndexPage() {
  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-xl font-semibold text-slate-900">Research Report</h1>
      <p className="mt-1 text-sm text-slate-600">
        Pick a study to generate a full-provenance report across every analysis stage.
      </p>
      <StudyPicker basePath="/reports" />
    </div>
  );
}
