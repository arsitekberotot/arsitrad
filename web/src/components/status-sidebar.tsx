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
          <div className="flex items-center gap-2 text-sky-600">
            <Sparkles className="size-4" />
            <Badge className="border-sky-200 bg-sky-100 text-sky-700">Tonight build</Badge>
          </div>
          <CardTitle>{bootstrap?.app_title ?? "Arsitrad Web"}</CardTitle>
          <CardDescription>
            Proper UI shell on top of the existing Python brain. Streamlit stays as fallback.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-slate-700">
          <p>{bootstrap?.disclaimer ?? "Loading disclaimer..."}</p>
          <div className="rounded-2xl border border-slate-200 bg-white/80 p-4">
            <div className="mb-2 flex items-center gap-2 text-slate-800">
              <Gauge className="size-4 text-emerald-600" /> Runtime endpoint
            </div>
            <p className="break-all font-mono text-xs text-slate-600">{apiBaseUrl}</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Runtime status</CardTitle>
          <CardDescription>
            Quick read on API connectivity, retrieval assets, and model availability.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-slate-700">
          <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white/80 px-4 py-3">
            <span className="text-slate-600">API health</span>
            <Badge className={health ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-amber-200 bg-amber-50 text-amber-700"}>
              {health ? "Connected" : "Waiting"}
            </Badge>
          </div>
          <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white/80 px-4 py-3">
            <span className="flex items-center gap-2 text-slate-600"><Database className="size-4" /> Sparse index</span>
            <Badge className={health?.sparse_index_exists ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-rose-200 bg-rose-50 text-rose-700"}>
              {health?.sparse_index_exists ? "Ready" : "Missing"}
            </Badge>
          </div>
          <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white/80 px-4 py-3">
            <span className="flex items-center gap-2 text-slate-600"><Layers3 className="size-4" /> GGUF model</span>
            <Badge className={health?.model_exists ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-amber-200 bg-amber-50 text-amber-700"}>
              {health?.model_exists ? "Found" : "Not found"}
            </Badge>
          </div>
          <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white/80 px-4 py-3">
            <span className="text-slate-600">Dense retrieval</span>
            <Badge className={health?.dense_enabled ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-slate-200 bg-white/80 text-slate-700"}>
              {health?.dense_enabled ? "Enabled" : "Sparse-first"}
            </Badge>
          </div>
          {!health && (
            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-amber-800">
              <div className="mb-2 flex items-center gap-2 font-medium">
                <AlertTriangle className="size-4" /> Backend belum nyambung
              </div>
              <p className="text-sm text-amber-800">
                Jalankan <span className="font-mono">uvicorn api.server:app --reload --port 8000</span> dari root repo.
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
