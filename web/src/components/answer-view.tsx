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
      className: "border-emerald-400/20 bg-emerald-400/10 text-emerald-100",
    };
  }

  if (score >= 0.6) {
    return {
      label: "Sedang",
      className: "border-amber-400/20 bg-amber-400/10 text-amber-100",
    };
  }

  return {
    label: "Rendah",
    className: "border-rose-400/20 bg-rose-400/10 text-rose-100",
  };
}

function sectionIcon(heading: (typeof SECTION_ORDER)[number]) {
  switch (heading) {
    case "RINGKASAN":
      return <Sparkles className="size-4 text-sky-300" />;
    case "DETAIL REGULASI":
      return <FileText className="size-4 text-sky-300" />;
    case "SARAN TEKNIS":
      return <ShieldCheck className="size-4 text-sky-300" />;
    case "SUMBER":
      return <BookOpenText className="size-4 text-sky-300" />;
    default:
      return <ShieldCheck className="size-4 text-sky-300" />;
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
            <Badge className="bg-white/5 text-slate-300">
              Mode {response.used_model ? "GGUF" : "Fallback"}
            </Badge>
            <Badge className="bg-white/5 text-slate-300">
              Kandidat {response.retrieval.candidates.length}
            </Badge>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Standalone query</p>
            <p className="mt-3 text-sm leading-7 text-slate-200">{response.retrieval.standalone_query}</p>
          </div>
        </CardContent>
      </Card>

      {sectionEntries.length > 0 ? (
        <div className="grid gap-4">
          {sectionEntries.map((heading) => (
            <Card key={heading}>
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2 text-slate-100">
                  {sectionIcon(heading)}
                  <CardTitle className="text-base">{formatLabel(heading.toLowerCase())}</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <div className="whitespace-pre-wrap text-sm leading-7 text-slate-300">{sections[heading]}</div>
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
            <div className="whitespace-pre-wrap text-sm leading-7 text-slate-300">{cleaned}</div>
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
