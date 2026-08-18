import { StudyPicker } from "@/components/layout/StudyPicker";

export default function BrainResponseIndexPage() {
  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-xl font-semibold text-slate-900">Brain Response</h1>
      <p className="mt-1 text-sm text-slate-600">
        Pick a study to see event-centered cortical/EEG spectral response.
      </p>
      <StudyPicker basePath="/brain-response" />
    </div>
  );
}
