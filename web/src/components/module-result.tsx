import { Fragment } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatIDR, formatLabel } from "@/lib/utils";

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function renderPrimitive(value: unknown) {
  if (typeof value === "number") {
    if (Number.isFinite(value) && value >= 1000) {
      return formatIDR(value);
    }
    return value.toString();
  }

  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }

  return String(value);
}

function JsonNode({ label, value, depth = 0 }: { label?: string; value: unknown; depth?: number }) {
  if (value === null || value === undefined) {
    return null;
  }

  if (Array.isArray(value)) {
    return (
      <div className="space-y-3">
        {label ? <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">{formatLabel(label)}</p> : null}
        <div className="space-y-3">
          {value.map((item, index) => (
            <div
              key={`${label ?? "item"}-${index}`}
              className="rounded-2xl border border-white/8 bg-white/5 p-4"
            >
              {isPlainObject(item) || Array.isArray(item) ? (
                <JsonNode value={item} depth={depth + 1} />
              ) : (
                <p className="text-sm leading-6 text-slate-300">{renderPrimitive(item)}</p>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (isPlainObject(value)) {
    const entries = Object.entries(value);
    return (
      <div className="space-y-3">
        {label ? <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">{formatLabel(label)}</p> : null}
        <div className={depth === 0 ? "grid gap-3 xl:grid-cols-2" : "space-y-3"}>
          {entries.map(([key, nestedValue]) => (
            <div
              key={key}
              className="rounded-2xl border border-white/8 bg-white/5 p-4"
            >
              {isPlainObject(nestedValue) || Array.isArray(nestedValue) ? (
                <JsonNode label={key} value={nestedValue} depth={depth + 1} />
              ) : (
                <Fragment>
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">{formatLabel(key)}</p>
                  <p className="mt-2 text-sm leading-6 text-slate-300">{renderPrimitive(nestedValue)}</p>
                </Fragment>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {label ? <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">{formatLabel(label)}</p> : null}
      <p className="text-sm leading-6 text-slate-300">{renderPrimitive(value)}</p>
    </div>
  );
}

export function ModuleResult({ title, payload }: { title: string; payload: Record<string, unknown> | null }) {
  if (!payload) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <JsonNode value={payload} />
      </CardContent>
    </Card>
  );
}
