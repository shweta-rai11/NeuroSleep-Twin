import { StudyPicker } from "@/components/layout/StudyPicker";

export default function OxygenBurdenIndexPage() {
  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-xl font-semibold text-slate-900">Oxygen Burden</h1>
      <p className="mt-1 text-sm text-slate-600">
        Pick a study for desaturation depth, slope, recovery, and area-under-threshold burden.
      </p>
      <StudyPicker basePath="/oxygen-burden" />
    </div>
  );
}
