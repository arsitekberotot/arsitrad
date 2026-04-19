import { AlertTriangle, Database, Gauge, Layers3, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { BootstrapData, HealthData } from "@/lib/types";

interface StatusSidebarProps {
  bootstrap: BootstrapData | null;
  health: HealthData | null;
  apiBaseUrl: string;
}

export function StatusSidebar({ bootstrap, health, apiBaseUrl }: StatusSidebarProps) {
  return (
    <div className="space-y-5">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2 text-sky-300">
            <Sparkles className="size-4" />
            <Badge className="border-sky-400/20 bg-sky-400/10 text-sky-200">Tonight build</Badge>
          </div>
          <CardTitle>{bootstrap?.app_title ?? "Arsitrad Web"}</CardTitle>
          <CardDescription>
            Proper UI shell on top of the existing Python brain. Streamlit stays as fallback.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-slate-300">
          <p>{bootstrap?.disclaimer ?? "Loading disclaimer..."}</p>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="mb-2 flex items-center gap-2 text-slate-200">
              <Gauge className="size-4 text-emerald-300" /> Runtime endpoint
            </div>
            <p className="break-all font-mono text-xs text-slate-400">{apiBaseUrl}</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Runtime status</CardTitle>
          <CardDescription>
            Quick read on whether the backend is actually alive or just pretending.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-slate-300">
          <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
            <span className="text-slate-400">API health</span>
            <Badge className={health ? "border-emerald-400/20 bg-emerald-400/10 text-emerald-200" : "border-amber-400/20 bg-amber-400/10 text-amber-200"}>
              {health ? "Connected" : "Waiting"}
            </Badge>
          </div>
          <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
            <span className="flex items-center gap-2 text-slate-400"><Database className="size-4" /> Sparse index</span>
            <Badge className={health?.sparse_index_exists ? "border-emerald-400/20 bg-emerald-400/10 text-emerald-200" : "border-rose-400/20 bg-rose-400/10 text-rose-200"}>
              {health?.sparse_index_exists ? "Ready" : "Missing"}
            </Badge>
          </div>
          <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
            <span className="flex items-center gap-2 text-slate-400"><Layers3 className="size-4" /> GGUF model</span>
            <Badge className={health?.model_exists ? "border-emerald-400/20 bg-emerald-400/10 text-emerald-200" : "border-amber-400/20 bg-amber-400/10 text-amber-200"}>
              {health?.model_exists ? "Found" : "Not found"}
            </Badge>
          </div>
          <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
            <span className="text-slate-400">Dense retrieval</span>
            <Badge className={health?.dense_enabled ? "border-emerald-400/20 bg-emerald-400/10 text-emerald-200" : "border-white/10 bg-white/5 text-slate-300"}>
              {health?.dense_enabled ? "Enabled" : "Sparse-first"}
            </Badge>
          </div>
          {!health && (
            <div className="rounded-2xl border border-amber-400/20 bg-amber-400/10 p-4 text-amber-100">
              <div className="mb-2 flex items-center gap-2 font-medium">
                <AlertTriangle className="size-4" /> Backend belum nyambung
              </div>
              <p className="text-sm text-amber-50/80">
                Jalankan <span className="font-mono">uvicorn api.server:app --reload --port 8000</span> dari root repo.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">What changed</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-slate-300">
          <p>• Next.js App Router shell with client-side workbench</p>
          <p>• shadcn-style card/button/input primitives</p>
          <p>• dedicated Python API instead of Streamlit-only rendering</p>
          <p>• same ArsitradAnswerEngine underneath, less toy-store UI on top</p>
        </CardContent>
      </Card>
    </div>
  );
}
