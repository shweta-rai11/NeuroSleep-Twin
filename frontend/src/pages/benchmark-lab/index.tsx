import { StudyPicker } from "@/components/layout/StudyPicker";

export default function BenchmarkLabIndexPage() {
  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-xl font-semibold text-slate-900">Benchmark Lab</h1>
      <p className="mt-1 text-sm text-slate-600">
        Pick a study to benchmark candidate event detection against its ground-truth annotations.
      </p>
      <StudyPicker basePath="/benchmark-lab" />
    </div>
  );
}
