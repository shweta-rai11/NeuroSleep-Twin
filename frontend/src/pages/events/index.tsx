import { StudyPicker } from "@/components/layout/StudyPicker";

export default function EventsIndexPage() {
  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-xl font-semibold text-slate-900">Respiratory Events</h1>
      <p className="mt-1 text-sm text-slate-600">
        Pick a study to detect and inspect candidate respiratory events.
      </p>
      <StudyPicker basePath="/events" />
    </div>
  );
}
