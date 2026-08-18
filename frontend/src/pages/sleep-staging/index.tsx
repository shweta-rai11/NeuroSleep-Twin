import { StudyPicker } from "@/components/layout/StudyPicker";

export default function SleepStagingIndexPage() {
  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-xl font-semibold text-slate-900">Sleep Staging</h1>
      <p className="mt-1 text-sm text-slate-600">
        Pick a study to view its hypnogram with respiratory events overlaid.
      </p>
      <StudyPicker basePath="/sleep-staging" />
    </div>
  );
}
