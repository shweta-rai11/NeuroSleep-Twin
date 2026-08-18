import { Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/layout/AppShell";
import AutonomicPage from "@/pages/autonomic";
import StudyAutonomic from "@/pages/autonomic/StudyAutonomic";
import BenchmarkLabPage from "@/pages/benchmark-lab";
import StudyBenchmark from "@/pages/benchmark-lab/StudyBenchmark";
import BeyondAhiPage from "@/pages/beyond-ahi";
import StudyBeyondAhi from "@/pages/beyond-ahi/StudyBeyondAhi";
import BrainResponsePage from "@/pages/brain-response";
import StudyBrainResponse from "@/pages/brain-response/StudyBrainResponse";
import ChannelMappingPage from "@/pages/channel-mapping";
import StudyChannelMapping from "@/pages/channel-mapping/StudyChannelMapping";
import DashboardPage from "@/pages/dashboard";
import DatasetsPage from "@/pages/datasets";
import DigitalTwinPage from "@/pages/digital-twin";
import EventsPage from "@/pages/events";
import StudyEvents from "@/pages/events/StudyEvents";
import LongitudinalPage from "@/pages/longitudinal";
import OxygenBurdenPage from "@/pages/oxygen-burden";
import StudyOxygenBurden from "@/pages/oxygen-burden/StudyOxygenBurden";
import PhenotypingPage from "@/pages/phenotyping";
import QcPage from "@/pages/qc";
import StudyQcPage from "@/pages/qc/StudyQc";
import ReportsPage from "@/pages/reports";
import StudyReport from "@/pages/reports/StudyReport";
import ResearchAssistantPage from "@/pages/research-assistant";
import SettingsPage from "@/pages/settings";
import SleepStagingPage from "@/pages/sleep-staging";
import StudySleepStaging from "@/pages/sleep-staging/StudySleepStaging";
import UploadPage from "@/pages/upload";
import ViewerPage from "@/pages/viewer";
import StudyViewer from "@/pages/viewer/StudyViewer";

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/datasets" element={<DatasetsPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/channel-mapping" element={<ChannelMappingPage />} />
        <Route path="/channel-mapping/:studyId" element={<StudyChannelMapping />} />
        <Route path="/qc" element={<QcPage />} />
        <Route path="/qc/:studyId" element={<StudyQcPage />} />
        <Route path="/viewer" element={<ViewerPage />} />
        <Route path="/viewer/:studyId" element={<StudyViewer />} />
        <Route path="/sleep-staging" element={<SleepStagingPage />} />
        <Route path="/sleep-staging/:studyId" element={<StudySleepStaging />} />
        <Route path="/events" element={<EventsPage />} />
        <Route path="/events/:studyId" element={<StudyEvents />} />
        <Route path="/oxygen-burden" element={<OxygenBurdenPage />} />
        <Route path="/oxygen-burden/:studyId" element={<StudyOxygenBurden />} />
        <Route path="/brain-response" element={<BrainResponsePage />} />
        <Route path="/brain-response/:studyId" element={<StudyBrainResponse />} />
        <Route path="/autonomic" element={<AutonomicPage />} />
        <Route path="/autonomic/:studyId" element={<StudyAutonomic />} />
        <Route path="/beyond-ahi" element={<BeyondAhiPage />} />
        <Route path="/beyond-ahi/:studyId" element={<StudyBeyondAhi />} />
        <Route path="/phenotyping" element={<PhenotypingPage />} />
        <Route path="/benchmark-lab" element={<BenchmarkLabPage />} />
        <Route path="/benchmark-lab/:studyId" element={<StudyBenchmark />} />
        <Route path="/longitudinal" element={<LongitudinalPage />} />
        <Route path="/research-assistant" element={<ResearchAssistantPage />} />
        <Route path="/digital-twin" element={<DigitalTwinPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/reports/:studyId" element={<StudyReport />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </AppShell>
  );
}
