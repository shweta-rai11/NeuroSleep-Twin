import { StudyPicker } from "@/components/layout/StudyPicker";

export default function BeyondAhiPage() {
  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-xl font-semibold text-slate-900">Beyond AHI</h1>
      <p className="mt-1 text-sm text-slate-600">
        Pick a study to compare AHI against oxygen, arousal, autonomic, and recovery burden side by
        side — exploring physiology alongside AHI, never replacing it.
      </p>
      <StudyPicker basePath="/beyond-ahi" />
    </div>
  );
}
