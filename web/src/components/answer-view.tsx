"use client";

import { BookOpenText, FileText, ShieldCheck, Sparkles } from "lucide-react";

import { CitationBrowser } from "@/components/citation-browser";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { parseStructuredAnswer, SECTION_ORDER } from "@/lib/answer";
import type { AskResponse } from "@/lib/types";
import { formatLabel } from "@/lib/utils";

function confidenceTone(score: number) {
  if (score >= 0.75) {
    return {
      label: "Tinggi",
      className: "border-emerald-200 bg-emerald-50 text-emerald-800",
    };
  }

  if (score >= 0.6) {
    return {
      label: "Sedang",
      className: "border-amber-200 bg-amber-50 text-amber-800",
    };
  }

  return {
    label: "Rendah",
    className: "border-rose-200 bg-rose-50 text-rose-800",
  };
}

function sectionIcon(heading: (typeof SECTION_ORDER)[number]) {
  switch (heading) {
    case "RINGKASAN":
      return <Sparkles className="size-4 text-sky-600" />;
    case "DETAIL REGULASI":
      return <FileText className="size-4 text-sky-600" />;
    case "SARAN TEKNIS":
      return <ShieldCheck className="size-4 text-sky-600" />;
    case "SUMBER":
      return <BookOpenText className="size-4 text-sky-600" />;
    default:
      return <ShieldCheck className="size-4 text-sky-600" />;
  }
}

export function AnswerView({ response }: { response: AskResponse }) {
  const { cleaned, sections } = parseStructuredAnswer(response.answer);
  const sectionEntries = SECTION_ORDER.filter((heading) => sections[heading]);
  const confidence = confidenceTone(response.retrieval.confidence);

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="space-y-4 p-5">
          <div className="flex flex-wrap items-center gap-2">
            <Badge className={confidence.className}>
              Confidence {response.retrieval.confidence.toFixed(2)} · {confidence.label}
            </Badge>
            <Badge className="bg-white/80 text-slate-700">
              Mode {response.used_model ? "GGUF" : "Fallback"}
            </Badge>
            <Badge className="bg-white/80 text-slate-700">
              Kandidat {response.retrieval.candidates.length}
            </Badge>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white/80 p-4">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Standalone query</p>
            <p className="mt-3 text-sm leading-7 text-slate-800">{response.retrieval.standalone_query}</p>
          </div>
        </CardContent>
      </Card>

      {sectionEntries.length > 0 ? (
        <div className="grid gap-4">
          {sectionEntries.map((heading) => (
            <Card key={heading}>
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2 text-slate-900">
                  {sectionIcon(heading)}
                  <CardTitle className="text-base">{formatLabel(heading.toLowerCase())}</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <div className="whitespace-pre-wrap text-sm leading-7 text-slate-700">{sections[heading]}</div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Jawaban</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="whitespace-pre-wrap text-sm leading-7 text-slate-700">{cleaned}</div>
          </CardContent>
        </Card>
      )}

      {response.retrieval.candidates.length > 0 ? (
        <CitationBrowser
          candidates={response.retrieval.candidates}
          standaloneQuery={response.retrieval.standalone_query}
        />
      ) : null}
    </div>
  );
}
