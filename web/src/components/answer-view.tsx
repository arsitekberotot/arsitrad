import { FileText, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { parseStructuredAnswer, SECTION_ORDER } from "@/lib/answer";
import type { AskResponse, Candidate } from "@/lib/types";
import { formatLabel } from "@/lib/utils";

function confidenceTone(score: number) {
  if (score >= 0.75) return "Tinggi";
  if (score >= 0.6) return "Sedang";
  return "Rendah";
}

function SourceCard({ candidate, index }: { candidate: Candidate; index: number }) {
  const sourceName = String(candidate.metadata.source_name ?? candidate.chunk_key ?? `Source ${index}`);
  const region = candidate.metadata.region ? String(candidate.metadata.region) : null;
  const page = candidate.metadata.start_page ?? candidate.metadata.page ?? null;

  return (
    <Card className="border-white/8 bg-slate-950/50">
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge>[{index}]</Badge>
          <CardTitle className="text-sm">{sourceName}</CardTitle>
          {region ? <Badge className="bg-white/5 text-slate-300">{formatLabel(region)}</Badge> : null}
          {page ? <Badge className="bg-white/5 text-slate-300">Hlm. {String(page)}</Badge> : null}
        </div>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-slate-300">
        <p className="line-clamp-5 whitespace-pre-wrap leading-6">{candidate.content}</p>
        <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Score {candidate.score.toFixed(2)}</p>
      </CardContent>
    </Card>
  );
}

export function AnswerView({ response }: { response: AskResponse }) {
  const { cleaned, sections } = parseStructuredAnswer(response.answer);
  const sectionEntries = SECTION_ORDER.filter((heading) => sections[heading]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge className="border-sky-400/20 bg-sky-400/10 text-sky-100">
          Confidence {response.retrieval.confidence.toFixed(2)} · {confidenceTone(response.retrieval.confidence)}
        </Badge>
        <Badge className="bg-white/5 text-slate-300">
          Mode {response.used_model ? "GGUF" : "Fallback"}
        </Badge>
        <Badge className="bg-white/5 text-slate-300">
          Query {response.retrieval.standalone_query}
        </Badge>
      </div>

      {sectionEntries.length > 0 ? (
        <div className="grid gap-4">
          {sectionEntries.map((heading) => (
            <Card key={heading}>
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2 text-slate-100">
                  <ShieldCheck className="size-4 text-sky-300" />
                  <CardTitle className="text-base">{formatLabel(heading.toLowerCase())}</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <div className="whitespace-pre-wrap text-sm leading-7 text-slate-300">
                  {sections[heading]}
                </div>
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

      {response.retrieval.candidates.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-sm font-medium text-slate-200">
            <FileText className="size-4 text-sky-300" />
            Sumber teratas
          </div>
          <div className="grid gap-3 xl:grid-cols-2">
            {response.retrieval.candidates.slice(0, 4).map((candidate, index) => (
              <SourceCard key={`${candidate.chunk_key}-${index}`} candidate={candidate} index={index + 1} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
