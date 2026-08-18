import { ChevronDown, Info, Send } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { api } from "@/api/client";
import { Card } from "@/components/layout/Card";
import type { StudyListItem } from "@/types/study";

interface ChatMessage {
  role: "user" | "assistant";
  text: string;
  evidence?: Record<string, unknown>;
}

const SUGGESTED_QUESTIONS = [
  "How many respiratory events were detected and how severe?",
  "What was the oxygen burden like?",
  "How does this compare against ground truth?",
  "Summarize the sleep stages.",
];

export default function ResearchAssistantPage() {
  const [studies, setStudies] = useState<StudyListItem[] | null>(null);
  const [studyId, setStudyId] = useState<number | null>(null);
  const [status, setStatus] = useState<{ configured: boolean; provider: string | null; model: string | null } | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [showEvidence, setShowEvidence] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.listStudies().then((all) => {
      const ingested = all.filter((s) => s.status === "ingested");
      setStudies(ingested);
      if (ingested.length > 0) setStudyId(ingested[0].id);
    });
    api.getAssistantStatus().then(setStatus);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send(question: string) {
    if (!studyId || !question.trim() || busy) return;
    setMessages((prev) => [...prev, { role: "user", text: question }]);
    setInput("");
    setBusy(true);
    try {
      const res = await api.askAssistant(studyId, question);
      setMessages((prev) => [...prev, { role: "assistant", text: res.answer, evidence: res.evidence }]);
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", text: "Could not reach the assistant." }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Research Assistant</h1>
          <p className="mt-1 text-sm text-slate-600">
            Narrates already-computed pipeline output only — it never reasons over raw signals.
          </p>
        </div>
        {studies && studies.length > 0 && (
          <div className="relative">
            <select
              value={studyId ?? ""}
              onChange={(e) => setStudyId(Number(e.target.value))}
              className="appearance-none rounded-md border border-slate-300 py-1.5 pl-3 pr-8 text-sm"
            >
              {studies.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.display_name || s.record_name}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
          </div>
        )}
      </div>

      {status && !status.configured && (
        <div className="mt-3 flex items-start gap-1.5 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-800">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          No local Ollama server or ANTHROPIC_API_KEY found — answering with deterministic template
          narration of the same structured data a real model would see.
        </div>
      )}
      {status?.configured && (
        <div className="mt-3 flex items-start gap-1.5 rounded-md bg-emerald-50 px-3 py-2 text-xs text-emerald-800">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          Answering with {status.provider === "ollama" ? "a local Ollama model" : "Anthropic"} (
          {status.model}).
        </div>
      )}

      {studies && studies.length === 0 && (
        <Card className="mt-4">
          <p className="text-sm text-slate-600">Ingest a study first to ask about it.</p>
        </Card>
      )}

      {studyId && (
        <>
          <div className="mt-4 flex-1 space-y-3 overflow-y-auto">
            {messages.length === 0 && (
              <div className="flex flex-wrap gap-1.5">
                {SUGGESTED_QUESTIONS.map((q) => (
                  <button
                    key={q}
                    onClick={() => send(q)}
                    className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-600 hover:bg-slate-50"
                  >
                    {q}
                  </button>
                ))}
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
                <div
                  className={
                    m.role === "user"
                      ? "max-w-lg rounded-lg bg-brand-600 px-3 py-2 text-sm text-white"
                      : "max-w-lg rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800"
                  }
                >
                  {m.text}
                  {m.evidence && (
                    <div className="mt-2 border-t border-slate-100 pt-1.5">
                      <button
                        onClick={() => setShowEvidence(showEvidence === i ? null : i)}
                        className="text-[10px] font-medium text-brand-600 hover:underline"
                      >
                        {showEvidence === i ? "Hide evidence" : "Show evidence"}
                      </button>
                      {showEvidence === i && (
                        <pre className="mt-1 max-h-48 overflow-auto rounded bg-slate-50 p-2 text-[10px] text-slate-600">
                          {JSON.stringify(m.evidence, null, 2)}
                        </pre>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {busy && <p className="text-xs text-slate-400">Thinking…</p>}
            <div ref={bottomRef} />
          </div>

          <div className="mt-3 flex items-center gap-2 border-t border-slate-200 pt-3">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send(input)}
              placeholder="Ask about this study's results…"
              className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
            <button
              onClick={() => send(input)}
              disabled={busy || !input.trim()}
              className="rounded-md bg-brand-600 p-2 text-white hover:bg-brand-700 disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </>
      )}
    </div>
  );
}
