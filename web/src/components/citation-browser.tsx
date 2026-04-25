"use client";

import { useEffect, useMemo, useState } from "react";
import { ExternalLink, FileText, Search, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { Candidate } from "@/lib/types";
import { formatLabel } from "@/lib/utils";

function sourceName(candidate: Candidate, index: number) {
  const metadataName = candidate.metadata.source_name;
  if (typeof metadataName === "string" && metadataName.trim()) {
    return metadataName;
  }

  return candidate.chunk_key || `Source ${index + 1}`;
}

function sourceRegion(candidate: Candidate) {
  const value = candidate.metadata.region;
  return typeof value === "string" && value.trim() ? formatLabel(value) : null;
}

function sourcePage(candidate: Candidate) {
  const value = candidate.metadata.start_page ?? candidate.metadata.page;
  if (typeof value === "number" && Number.isFinite(value)) {
    return String(value);
  }
  if (typeof value === "string" && value.trim()) {
    return value;
  }
  return null;
}

function sourceChunkKind(candidate: Candidate) {
  const value = candidate.metadata.document_type ?? candidate.metadata.type ?? candidate.source;
  return typeof value === "string" && value.trim() ? formatLabel(value) : null;
}

function useBodyScrollLock(active: boolean) {
  useEffect(() => {
    if (!active) {
      return;
    }

    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [active]);
}

function SourcePreviewModal({
  candidate,
  index,
  onClose,
}: {
  candidate: Candidate;
  index: number;
  onClose: () => void;
}) {
  const name = sourceName(candidate, index);
  const region = sourceRegion(candidate);
  const page = sourcePage(candidate);
  const kind = sourceChunkKind(candidate);

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-white/75 p-4 backdrop-blur-sm">
      <div className="max-h-[88vh] w-full max-w-4xl overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-2xl shadow-slate-200/40">
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-6 py-5">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge className="border-sky-200 bg-sky-100 text-sky-800">[{index + 1}]</Badge>
              <h3 className="text-lg font-semibold text-slate-950">{name}</h3>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {kind ? <Badge className="bg-white/80 text-slate-700">{kind}</Badge> : null}
              {region ? <Badge className="bg-white/80 text-slate-700">{region}</Badge> : null}
              {page ? <Badge className="bg-white/80 text-slate-700">Hlm. {page}</Badge> : null}
              <Badge className="bg-white/80 text-slate-700">Score {candidate.score.toFixed(2)}</Badge>
            </div>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="Close source preview">
            <X className="size-4" />
          </Button>
        </div>
        <div className="max-h-[calc(88vh-112px)] overflow-y-auto px-6 py-5">
          <div className="rounded-3xl border border-slate-200 bg-white/80 p-5">
            <p className="whitespace-pre-wrap text-sm leading-7 text-slate-800">{candidate.content}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function InlineCitationPanel({
  candidates,
  standaloneQuery,
  onPreview,
}: {
  candidates: Candidate[];
  standaloneQuery: string;
  onPreview: (candidate: Candidate, index: number) => void;
}) {
  return (
    <Card className="border-sky-200 bg-sky-50/70">
      <CardContent className="space-y-4 p-5">
        <div className="rounded-2xl border border-slate-200 bg-white/80 p-4 text-sm text-slate-700">
          <div className="flex items-center gap-2 text-slate-900">
            <Search className="size-4 text-sky-600" />
            <span className="font-medium">Standalone query</span>
          </div>
          <p className="mt-3 leading-6">{standaloneQuery}</p>
        </div>

        <div className="grid gap-3">
          {candidates.map((candidate, index) => {
            const name = sourceName(candidate, index);
            const region = sourceRegion(candidate);
            const page = sourcePage(candidate);
            const kind = sourceChunkKind(candidate);

            return (
              <div key={`${candidate.chunk_key}-${index}`} className="rounded-2xl border border-slate-200 bg-white p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge className="border-sky-200 bg-sky-100 text-sky-800">[{index + 1}]</Badge>
                      <p className="break-words text-sm font-semibold text-slate-950">{name}</p>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {kind ? <Badge className="bg-white/80 text-slate-700">{kind}</Badge> : null}
                      {region ? <Badge className="bg-white/80 text-slate-700">{region}</Badge> : null}
                      {page ? <Badge className="bg-white/80 text-slate-700">Hlm. {page}</Badge> : null}
                      <Badge className="bg-white/80 text-slate-700">Score {candidate.score.toFixed(2)}</Badge>
                    </div>
                  </div>
                  <Button variant="outline" size="sm" onClick={() => onPreview(candidate, index)}>
                    <ExternalLink className="size-4" /> Preview
                  </Button>
                </div>
                <p className="mt-4 whitespace-pre-wrap text-sm leading-7 text-slate-700">{candidate.content.slice(0, 700)}{candidate.content.length > 700 ? "…" : ""}</p>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

export function CitationBrowser({
  candidates,
  standaloneQuery,
}: {
  candidates: Candidate[];
  standaloneQuery: string;
}) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [previewIndex, setPreviewIndex] = useState<number | null>(null);

  useBodyScrollLock(previewIndex !== null);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key !== "Escape") {
        return;
      }

      if (previewIndex !== null) {
        setPreviewIndex(null);
        return;
      }

      if (drawerOpen) {
        setDrawerOpen(false);
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [drawerOpen, previewIndex]);

  const previewCandidate = useMemo(() => {
    if (previewIndex === null) {
      return null;
    }
    return candidates[previewIndex] ?? null;
  }, [candidates, previewIndex]);

  const topNames = candidates.slice(0, 3).map((candidate, index) => sourceName(candidate, index));

  return (
    <>
      <Card>
        <CardContent className="flex flex-col gap-4 p-5 md:flex-row md:items-center md:justify-between">
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm font-medium text-slate-900">
              <FileText className="size-4 text-sky-600" />
              Citations ready
            </div>
            <div className="flex flex-wrap gap-2">
              {topNames.map((name, index) => (
                <Badge key={`${name}-${index}`} className="bg-white/80 text-slate-700">
                  [{index + 1}] {name}
                </Badge>
              ))}
              {candidates.length > 3 ? (
                <Badge className="bg-white/80 text-slate-700">+{candidates.length - 3} lainnya</Badge>
              ) : null}
            </div>
            <p className="text-sm leading-6 text-slate-600">
              Open the drawer to audit the retrieved chunks and preview full source text without crowding the main answer.
            </p>
          </div>
          <Button variant="outline" onClick={() => setDrawerOpen((value) => !value)}>
            <FileText className="size-4" /> {drawerOpen ? "Hide citations" : "Open citations"}
          </Button>
        </CardContent>
      </Card>

      {drawerOpen ? (
        <InlineCitationPanel
          candidates={candidates}
          standaloneQuery={standaloneQuery}
          onPreview={(_, index) => setPreviewIndex(index)}
        />
      ) : null}

      {previewCandidate && previewIndex !== null ? (
        <SourcePreviewModal
          candidate={previewCandidate}
          index={previewIndex}
          onClose={() => setPreviewIndex(null)}
        />
      ) : null}
    </>
  );
}
