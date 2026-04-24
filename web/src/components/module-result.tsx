import type { ReactNode } from "react";

import {
  ArrowRight,
  Building2,
  CheckCircle2,
  CircleGauge,
  ClipboardList,
  Clock3,
  Flame,
  House,
  Ruler,
  ShieldAlert,
  ThermometerSun,
  Wallet,
  Waves,
  Wind,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { ModuleId } from "@/lib/types";
import { formatIDR, formatLabel } from "@/lib/utils";

type StructuredModuleId = Exclude<ModuleId, "regulation">;

type Metric = {
  label: string;
  value: string;
  caption?: string;
};

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function toStringValue(value: unknown): string | null {
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed ? trimmed : null;
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  return null;
}

function toNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  return null;
}

function toStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item) => toStringValue(item))
    .filter((item): item is string => Boolean(item));
}

function toObjectArray(value: unknown): Record<string, unknown>[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter(isPlainObject);
}

function formatCount(value: number | null, suffix?: string) {
  if (value === null) {
    return "-";
  }

  const formatted = new Intl.NumberFormat("id-ID", { maximumFractionDigits: 1 }).format(value);
  return suffix ? `${formatted} ${suffix}` : formatted;
}

function formatPriority(priority: string | null) {
  if (!priority) return "Unknown";
  return priority.replace(/_/g, " ").toUpperCase();
}

function priorityClass(priority: string | null) {
  switch ((priority ?? "").toUpperCase()) {
    case "HIGH":
      return "border-rose-200 bg-rose-50 text-rose-800";
    case "MEDIUM":
      return "border-amber-200 bg-amber-50 text-amber-800";
    case "LOW":
      return "border-emerald-200 bg-emerald-50 text-emerald-800";
    default:
      return "bg-white/80 text-slate-800";
  }
}

function repairPriorityLabel(priority: number | null) {
  if (priority === 1) {
    return "Darurat";
  }
  if (priority === 2) {
    return "Tinggi";
  }
  if (priority === 3) {
    return "Sedang";
  }
  return "-";
}

function repairPriorityClass(priority: number | null) {
  if (priority === 1) {
    return "border-rose-200 bg-rose-50 text-rose-800";
  }
  if (priority === 2) {
    return "border-amber-200 bg-amber-50 text-amber-800";
  }
  if (priority === 3) {
    return "border-sky-200 bg-sky-100 text-sky-800";
  }
  return "bg-white/80 text-slate-800";
}

function replaceTokens(text: string, tokens: Record<string, string>) {
  return text.replace(/\{(\w+)\}/g, (_, token: string) => tokens[token] ?? `{${token}}`);
}

function MetricCard({ label, value, caption }: Metric) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white/80 p-4">
      <p className="text-xs uppercase tracking-[0.24em] text-slate-500">{label}</p>
      <p className="mt-2 text-lg font-semibold text-slate-950">{value}</p>
      {caption ? <p className="mt-2 text-sm leading-6 text-slate-600">{caption}</p> : null}
    </div>
  );
}

function SectionShell({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="pb-4">
        <CardTitle className="text-base">{title}</CardTitle>
        {description ? <CardDescription className="leading-6">{description}</CardDescription> : null}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

function PermitResult({ title, payload }: { title: string; payload: Record<string, unknown> }) {
  const buildingType = formatLabel(toStringValue(payload.building_type) ?? "-");
  const location = toStringValue(payload.location) ?? "-";
  const totalSteps = toNumber(payload.total_steps);
  const estimatedDays = toNumber(payload.estimated_total_days);
  const estimatedCost = toNumber(payload.estimated_total_cost_idr);
  const floorArea = toNumber(payload.floor_area_m2);
  const landArea = toNumber(payload.land_area_m2);
  const buildingHeight = toNumber(payload.building_height_m);
  const buildingFunction = formatLabel(toStringValue(payload.building_function) ?? "-");
  const retribution = isPlainObject(payload.retribution) ? payload.retribution : null;
  const steps = toObjectArray(payload.imb_steps);
  const additionalRequirements = toStringArray(payload.additional_requirements);
  const references = toStringArray(payload.sni_references);

  const metrics: Metric[] = [
    {
      label: "Lokasi + fungsi",
      value: location,
      caption: `${buildingType} · ${buildingFunction}`,
    },
    {
      label: "Estimasi biaya total",
      value: formatIDR(estimatedCost ?? undefined),
      caption: "Biaya administrasi + retribusi kasar.",
    },
    {
      label: "Estimasi durasi",
      value: estimatedDays !== null ? `${formatCount(estimatedDays)} hari` : "-",
      caption: "Akumulasi estimasi maksimum dari tiap tahap.",
    },
    {
      label: "Tahapan inti",
      value: totalSteps !== null ? formatCount(totalSteps) : "-",
      caption: `${formatCount(floorArea, "m²")} lantai · ${formatCount(landArea, "m²")} tanah`,
    },
  ];

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="rounded-2xl border border-sky-200 bg-sky-100 p-3 text-sky-700">
              <Building2 className="size-5" />
            </div>
            <div>
              <CardTitle>{title}</CardTitle>
              <CardDescription className="leading-6">
                Human-readable permit checklist with cost, timeline, and document breakdown.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {metrics.map((metric) => (
              <MetricCard key={metric.label} {...metric} />
            ))}
          </div>

          <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
            <div className="rounded-2xl border border-slate-200 bg-white/80 p-4">
              <div className="flex items-center gap-2 text-sm font-medium text-slate-900">
                <ClipboardList className="size-4 text-sky-600" /> Ringkasan proyek
              </div>
              <dl className="mt-4 grid gap-3 sm:grid-cols-2">
                <div>
                  <dt className="text-xs uppercase tracking-[0.24em] text-slate-500">Tipe bangunan</dt>
                  <dd className="mt-2 text-sm text-slate-800">{buildingType}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-[0.24em] text-slate-500">Tinggi bangunan</dt>
                  <dd className="mt-2 text-sm text-slate-800">{buildingHeight !== null ? `${formatCount(buildingHeight)} m` : "-"}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-[0.24em] text-slate-500">Luas lantai</dt>
                  <dd className="mt-2 text-sm text-slate-800">{floorArea !== null ? `${formatCount(floorArea)} m²` : "-"}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-[0.24em] text-slate-500">Luas tanah</dt>
                  <dd className="mt-2 text-sm text-slate-800">{landArea !== null ? `${formatCount(landArea)} m²` : "-"}</dd>
                </div>
              </dl>
            </div>

            <div className="rounded-2xl border border-sky-400/10 bg-sky-400/5 p-4">
              <div className="flex items-center gap-2 text-sm font-medium text-slate-900">
                <Wallet className="size-4 text-sky-600" /> Snapshot retribusi
              </div>
              <div className="mt-4 space-y-3 text-sm text-slate-700">
                <p>{toStringValue(retribution?.breakdown) ?? "Breakdown belum tersedia."}</p>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                    <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Tarif / m²</p>
                    <p className="mt-2 text-sm font-semibold text-slate-950">{formatIDR(toNumber(retribution?.rate_per_m2_idr) ?? undefined)}</p>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                    <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Total retribusi</p>
                    <p className="mt-2 text-sm font-semibold text-slate-950">{formatIDR(toNumber(retribution?.total_retribution_idr) ?? undefined)}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <SectionShell
        title="Alur pengurusan"
        description="Urutannya sudah dibikin seperti playbook yang bisa langsung dipakai cek berkas dan ekspektasi waktu."
      >
        <div className="space-y-3">
          {steps.map((step, index) => {
            const stepNumber = toNumber(step.step) ?? index + 1;
            const stepName = toStringValue(step.name) ?? `Tahap ${index + 1}`;
            const docs = toStringArray(step.required_docs);
            const estimatedStepCost = toNumber(step.estimated_cost_idr);
            return (
              <div key={`${stepName}-${stepNumber}`} className="rounded-2xl border border-slate-200 bg-white/80 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge className="border-sky-200 bg-sky-100 text-sky-800">Tahap {stepNumber}</Badge>
                      <p className="text-sm font-semibold text-slate-950">{stepName}</p>
                    </div>
                    <p className="mt-3 text-sm leading-6 text-slate-700">{toStringValue(step.description) ?? "-"}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Badge className="bg-white/80 text-slate-700">
                      <Clock3 className="mr-1 size-3.5" /> {toStringValue(step.estimated_days) ?? "-"}
                    </Badge>
                    <Badge className="bg-white/80 text-slate-700">
                      <Wallet className="mr-1 size-3.5" /> {formatIDR(estimatedStepCost ?? undefined)}
                    </Badge>
                  </div>
                </div>

                {docs.length > 0 ? (
                  <div className="mt-4 grid gap-2 md:grid-cols-2">
                    {docs.map((doc) => (
                      <div key={`${stepName}-${doc}`} className="rounded-2xl border border-slate-200 bg-slate-50 p-3 text-sm leading-6 text-slate-700">
                        <div className="flex items-start gap-2">
                          <CheckCircle2 className="mt-1 size-4 text-emerald-600" />
                          <span>{doc}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : null}

                {toStringValue(step.note) ? (
                  <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                    {toStringValue(step.note)}
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      </SectionShell>

      {additionalRequirements.length > 0 ? (
        <SectionShell title="Persyaratan tambahan" description="Item ekstra yang biasanya muncul kalau fungsi, luas, atau tinggi bangunannya bikin birokrasi tambah rewel.">
          <div className="grid gap-2">
            {additionalRequirements.map((item) => (
              <div key={item} className="rounded-2xl border border-slate-200 bg-white/80 p-3 text-sm leading-6 text-slate-700">
                <div className="flex items-start gap-2">
                  <ArrowRight className="mt-1 size-4 text-sky-600" />
                  <span>{item}</span>
                </div>
              </div>
            ))}
          </div>
        </SectionShell>
      ) : null}

      {references.length > 0 ? (
        <SectionShell title="Referensi standar" description="Pegangan normatif yang dipakai modul untuk ngarahin checklist ini.">
          <div className="flex flex-wrap gap-2">
            {references.map((reference) => (
              <Badge key={reference} className="bg-white/80 text-slate-700">
                {reference}
              </Badge>
            ))}
          </div>
        </SectionShell>
      ) : null}
    </div>
  );
}

function CoolingResult({ title, payload }: { title: string; payload: Record<string, unknown> }) {
  const orientation = toStringValue(payload.orientation) ?? "-";
  const climateZone = formatLabel(toStringValue(payload.climate_zone) ?? "-");
  const climateDescription = toStringValue(payload.climate_description) ?? "-";
  const tempReduction = toNumber(payload.estimated_temp_reduction_c);
  const totalCost = toNumber(payload.estimated_cooling_cost_idr);
  const totalRecommendations = toNumber(payload.total_recommendations);
  const dimensions = isPlainObject(payload.building_dimensions) ? payload.building_dimensions : null;
  const thermalPerformance = isPlainObject(payload.thermal_performance) ? payload.thermal_performance : null;
  const wallMaterial = isPlainObject(thermalPerformance?.wall_material) ? thermalPerformance?.wall_material : null;
  const roofMaterial = isPlainObject(thermalPerformance?.roof_material) ? thermalPerformance?.roof_material : null;
  const recommendations = toObjectArray(payload.recommendations);
  const references = toStringArray(payload.sni_references);

  const metrics: Metric[] = [
    {
      label: "Orientasi + iklim",
      value: `${formatLabel(orientation)} · ${climateZone}`,
      caption: climateDescription,
    },
    {
      label: "Penurunan suhu",
      value: tempReduction !== null ? `${formatCount(tempReduction)}°C` : "-",
      caption: "Estimasi gabungan dari semua rekomendasi yang lolos filter budget.",
    },
    {
      label: "Biaya implementasi",
      value: formatIDR(totalCost ?? undefined),
      caption: `${formatCount(totalRecommendations)} intervensi aktif`,
    },
    {
      label: "Dimensi bangunan",
      value:
        dimensions !== null
          ? `${formatCount(toNumber(dimensions.length_m))} × ${formatCount(toNumber(dimensions.width_m))} × ${formatCount(toNumber(dimensions.height_m))} m`
          : "-",
      caption: `Lantai ${formatCount(toNumber(dimensions?.floor_count))}`,
    },
  ];

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="rounded-2xl border border-sky-200 bg-sky-100 p-3 text-sky-700">
              <Wind className="size-5" />
            </div>
            <div>
              <CardTitle>{title}</CardTitle>
              <CardDescription className="leading-6">
                Output pendinginan pasif yang kebaca seperti review desain, bukan lemparan JSON telanjang.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {metrics.map((metric) => (
              <MetricCard key={metric.label} {...metric} />
            ))}
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-white/80 p-4">
              <div className="flex items-center gap-2 text-sm font-medium text-slate-900">
                <ThermometerSun className="size-4 text-sky-600" /> Thermal snapshot
              </div>
              <div className="mt-4 grid gap-3 text-sm text-slate-700 sm:grid-cols-2">
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                  <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Volume</p>
                  <p className="mt-2 text-sm font-semibold text-slate-950">{formatCount(toNumber(thermalPerformance?.volume_m3), "m³")}</p>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                  <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Luas dinding</p>
                  <p className="mt-2 text-sm font-semibold text-slate-950">{formatCount(toNumber(thermalPerformance?.wall_area_m2), "m²")}</p>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                  <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Material dinding</p>
                  <p className="mt-2 text-sm font-semibold text-slate-950">{toStringValue(wallMaterial?.description) ?? formatLabel(toStringValue(payload.materials) ?? "-")}</p>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                  <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Material atap</p>
                  <p className="mt-2 text-sm font-semibold text-slate-950">{toStringValue(roofMaterial?.description) ?? "-"}</p>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white/80 p-4">
              <div className="flex items-center gap-2 text-sm font-medium text-slate-900">
                <Ruler className="size-4 text-sky-600" /> Catatan performa
              </div>
              <div className="mt-4 space-y-3 text-sm leading-6 text-slate-700">
                <p>{toStringValue(thermalPerformance?.climate_description) ?? climateDescription}</p>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                    <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Thermal mass dinding</p>
                    <p className="mt-2 text-sm font-semibold text-slate-950">{formatLabel(toStringValue(wallMaterial?.thermal_mass) ?? "-")}</p>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                    <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Thermal mass atap</p>
                    <p className="mt-2 text-sm font-semibold text-slate-950">{formatLabel(toStringValue(roofMaterial?.thermal_mass) ?? "-")}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <SectionShell
        title="Prioritas intervensi"
        description="Setiap kartu di bawah ini sudah dibikin seperti checklist implementasi: prioritas, efek termal, dan langkah kerja langsung kebaca."
      >
        <div className="space-y-3">
          {recommendations.map((recommendation, index) => {
            const priority = toStringValue(recommendation.priority);
            const implementation = toStringArray(recommendation.implementation).map((item) =>
              replaceTokens(item, { orientation }),
            );
            const recommendationTitle = toStringValue(recommendation.title) ?? `Rekomendasi ${index + 1}`;
            return (
              <div key={`${recommendationTitle}-${index}`} className="rounded-2xl border border-slate-200 bg-white/80 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-semibold text-slate-950">{recommendationTitle}</p>
                      <Badge className={priorityClass(priority)}>{formatPriority(priority)}</Badge>
                    </div>
                    <p className="mt-3 text-sm leading-6 text-slate-700">{toStringValue(recommendation.description) ?? "-"}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Badge className="bg-white/80 text-slate-700">
                      <ThermometerSun className="mr-1 size-3.5" /> {toStringValue(recommendation.thermal_impact) ?? "-"}
                    </Badge>
                    <Badge className="bg-white/80 text-slate-700">
                      <Wallet className="mr-1 size-3.5" /> {formatIDR(toNumber(recommendation.estimated_cost_idr) ?? undefined)}
                    </Badge>
                  </div>
                </div>

                {implementation.length > 0 ? (
                  <div className="mt-4 grid gap-2">
                    {implementation.map((item) => (
                      <div key={`${recommendationTitle}-${item}`} className="rounded-2xl border border-slate-200 bg-slate-50 p-3 text-sm leading-6 text-slate-700">
                        <div className="flex items-start gap-2">
                          <ArrowRight className="mt-1 size-4 text-sky-600" />
                          <span>{item}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      </SectionShell>

      {references.length > 0 ? (
        <SectionShell title="Referensi standar" description="Rujukan teknis yang dipakai modul saat nyusun strategi pendinginan pasif.">
          <div className="flex flex-wrap gap-2">
            {references.map((reference) => (
              <Badge key={reference} className="bg-white/80 text-slate-700">
                {reference}
              </Badge>
            ))}
          </div>
        </SectionShell>
      ) : null}
    </div>
  );
}

function DisasterResult({ title, payload }: { title: string; payload: Record<string, unknown> }) {
  const damageClassification = formatLabel(toStringValue(payload.damage_classification) ?? "-");
  const description = toStringValue(payload.description) ?? "-";
  const repairPriority = toNumber(payload.repair_priority);
  const location = toStringValue(payload.location) ?? "-";
  const disasterType = formatLabel(toStringValue(payload.disaster_type) ?? "-");
  const buildingType = formatLabel(toStringValue(payload.building_type) ?? "-");
  const floorArea = toNumber(payload.floor_area_m2);
  const perM2Cost = toNumber(payload.per_m2_cost_idr);
  const totalCost = toNumber(payload.total_estimated_cost_idr);
  const recommendations = toObjectArray(payload.recommendations);
  const references = toStringArray(payload.sni_references);
  const photoUrls = toStringArray(payload.photo_urls);

  const metrics: Metric[] = [
    {
      label: "Klasifikasi",
      value: damageClassification,
      caption: description,
    },
    {
      label: "Prioritas perbaikan",
      value: repairPriorityLabel(repairPriority),
      caption: `${buildingType} · ${location}`,
    },
    {
      label: "Estimasi biaya total",
      value: formatIDR(totalCost ?? undefined),
      caption: `Biaya kasar ${formatIDR(perM2Cost ?? undefined)}/m²`,
    },
    {
      label: "Konteks kejadian",
      value: disasterType,
      caption: floorArea !== null ? `${formatCount(floorArea)} m² terdampak` : "Luas belum diisi",
    },
  ];

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="rounded-2xl border border-rose-200 bg-rose-50 p-3 text-rose-800">
              <Flame className="size-5" />
            </div>
            <div>
              <CardTitle>{title}</CardTitle>
              <CardDescription className="leading-6">
                Structured damage summary with repair priority, estimated cost, and recommended actions.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {metrics.map((metric) => (
              <MetricCard key={metric.label} {...metric} />
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge className={repairPriorityClass(repairPriority)}>
              <ShieldAlert className="mr-1 size-3.5" /> Prioritas {repairPriorityLabel(repairPriority)}
            </Badge>
            {photoUrls.length > 0 ? (
              <Badge className="bg-white/80 text-slate-700">{formatCount(photoUrls.length)} foto terlampir</Badge>
            ) : (
              <Badge className="bg-white/80 text-slate-700">Tanpa foto lampiran</Badge>
            )}
          </div>
        </CardContent>
      </Card>

      <SectionShell
        title="Urutan tindakan"
        description="Dibikin seperti runbook perbaikan: langkah dulu, biaya kasar, lalu catatan wajib kalau ada."
      >
        <div className="space-y-3">
          {recommendations.map((recommendation, index) => {
            const action = toStringValue(recommendation.action) ?? `Tindakan ${index + 1}`;
            return (
              <div key={`${action}-${index}`} className="rounded-2xl border border-slate-200 bg-white/80 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge className="border-rose-200 bg-rose-50 text-rose-800">
                        Step {formatCount(toNumber(recommendation.step) ?? index + 1)}
                      </Badge>
                      <p className="text-sm font-semibold text-slate-950">{action}</p>
                    </div>
                    {toStringValue(recommendation.note) ? (
                      <p className="mt-3 text-sm leading-6 text-slate-700">{toStringValue(recommendation.note)}</p>
                    ) : null}
                  </div>
                  <Badge className="bg-white/80 text-slate-700">
                    <Wallet className="mr-1 size-3.5" /> {formatIDR(toNumber(recommendation.estimated_cost_idr) ?? undefined)}
                  </Badge>
                </div>
              </div>
            );
          })}
        </div>
      </SectionShell>

      {references.length > 0 ? (
        <SectionShell title="Referensi standar" description="Standar dan regulasi yang sebaiknya dicek saat validasi atau audit perbaikan.">
          <div className="flex flex-wrap gap-2">
            {references.map((reference) => (
              <Badge key={reference} className="bg-white/80 text-slate-700">
                {reference}
              </Badge>
            ))}
          </div>
        </SectionShell>
      ) : null}
    </div>
  );
}

function SettlementResult({ title, payload }: { title: string; payload: Record<string, unknown> }) {
  const location = toStringValue(payload.location) ?? "-";
  const populationDensity = toNumber(payload.population_density);
  const budgetUsed = toNumber(payload.budget_used_idr);
  const budgetRemaining = toNumber(payload.budget_remaining_idr);
  const totalInvestmentNeeded = toNumber(payload.total_investment_needed_idr);
  const assessment = isPlainObject(payload.current_assessment) ? payload.current_assessment : null;
  const componentScores = isPlainObject(assessment?.component_scores) ? assessment?.component_scores : null;
  const gaps = toStringArray(assessment?.gaps);
  const plan = toObjectArray(payload.recommended_plan);

  const metrics: Metric[] = [
    {
      label: "Lokasi + kepadatan",
      value: location,
      caption: populationDensity !== null ? `${formatCount(populationDensity)} orang/ha` : "Kepadatan belum tersedia",
    },
    {
      label: "Skor infrastruktur",
      value: assessment ? `${formatCount(toNumber(assessment.current_score))}/100` : "-",
      caption: `Level ${formatLabel(toStringValue(assessment?.infrastructure_level) ?? "-")}`,
    },
    {
      label: "Budget terpakai",
      value: formatIDR(budgetUsed ?? undefined),
      caption: `Sisa ${formatIDR(budgetRemaining ?? undefined)}`,
    },
    {
      label: "Kebutuhan penuh",
      value: formatIDR(totalInvestmentNeeded ?? undefined),
      caption: `${formatCount(plan.length)} intervensi direkomendasikan`,
    },
  ];

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-3 text-emerald-800">
              <House className="size-5" />
            </div>
            <div>
              <CardTitle>{title}</CardTitle>
              <CardDescription className="leading-6">
                Area-priority dashboard for budget, service gaps, and recommended settlement interventions.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {metrics.map((metric) => (
              <MetricCard key={metric.label} {...metric} />
            ))}
          </div>

          <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
            <div className="rounded-2xl border border-slate-200 bg-white/80 p-4">
              <div className="flex items-center gap-2 text-sm font-medium text-slate-900">
                <CircleGauge className="size-4 text-sky-600" /> Status layanan dasar
              </div>
              <div className="mt-4 grid gap-2 sm:grid-cols-2">
                {Object.entries(componentScores ?? {}).map(([key, value]) => {
                  const available = Boolean(toNumber(value));
                  return (
                    <div key={key} className="rounded-2xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
                      <div className="flex items-center justify-between gap-3">
                        <span>{formatLabel(key)}</span>
                        <Badge className={available ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-rose-200 bg-rose-50 text-rose-800"}>
                          {available ? "Ada" : "Gap"}
                        </Badge>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white/80 p-4">
              <div className="flex items-center gap-2 text-sm font-medium text-slate-900">
                <Waves className="size-4 text-sky-600" /> Gap prioritas
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {gaps.length > 0 ? (
                  gaps.map((gap) => (
                    <Badge key={gap} className="border-amber-200 bg-amber-50 text-amber-800">
                      {formatLabel(gap)}
                    </Badge>
                  ))
                ) : (
                  <Badge className="border-emerald-200 bg-emerald-50 text-emerald-800">Tidak ada gap besar</Badge>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <SectionShell
        title="Rencana intervensi"
        description="Urutan prioritas dibuat berdasarkan impact, biaya, dan batas budget yang kamu kasih."
      >
        <div className="space-y-3">
          {plan.length > 0 ? (
            plan.map((intervention, index) => {
              const description = toStringValue(intervention.description) ?? `Intervensi ${index + 1}`;
              return (
                <div key={`${description}-${index}`} className="rounded-2xl border border-slate-200 bg-white/80 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge className="border-sky-200 bg-sky-100 text-sky-800">
                          Prioritas {formatCount(toNumber(intervention.priority_rank) ?? index + 1)}
                        </Badge>
                        <p className="text-sm font-semibold text-slate-950">{description}</p>
                      </div>
                      <p className="mt-3 text-sm leading-6 text-slate-700">
                        {formatLabel(toStringValue(intervention.category) ?? "-")} · dampak {formatCount(toNumber(intervention.impact_score))}/10
                      </p>
                    </div>
                    <Badge className="bg-white/80 text-slate-700">
                      <Wallet className="mr-1 size-3.5" /> {formatIDR(toNumber(intervention.recommended_cost) ?? undefined)}
                    </Badge>
                  </div>

                  <div className="mt-4 grid gap-3 sm:grid-cols-3">
                    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                      <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Unit disarankan</p>
                      <p className="mt-2 text-sm font-semibold text-slate-950">
                        {formatCount(toNumber(intervention.recommended_units))} {toStringValue(intervention.unit) ?? "unit"}
                      </p>
                    </div>
                    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                      <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Biaya per unit</p>
                      <p className="mt-2 text-sm font-semibold text-slate-950">{formatIDR(toNumber(intervention.cost_per_unit_idr) ?? undefined)}</p>
                    </div>
                    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                      <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Maks unit terjangkau</p>
                      <p className="mt-2 text-sm font-semibold text-slate-950">{formatCount(toNumber(intervention.max_affordable_units))}</p>
                    </div>
                  </div>
                </div>
              );
            })
          ) : (
            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-800">
              Tidak ada intervensi yang lolos dalam budget saat ini. Naikkan budget atau perbaiki target prioritas.
            </div>
          )}
        </div>
      </SectionShell>
    </div>
  );
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
            <div key={`${label ?? "item"}-${index}`} className="rounded-2xl border border-slate-200 bg-white/80 p-4">
              {isPlainObject(item) || Array.isArray(item) ? (
                <JsonNode value={item} depth={depth + 1} />
              ) : (
                <p className="text-sm leading-6 text-slate-700">{renderPrimitive(item)}</p>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (isPlainObject(value)) {
    return (
      <div className="space-y-3">
        {label ? <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">{formatLabel(label)}</p> : null}
        <div className={depth === 0 ? "grid gap-3 xl:grid-cols-2" : "space-y-3"}>
          {Object.entries(value).map(([key, nestedValue]) => (
            <div key={key} className="rounded-2xl border border-slate-200 bg-white/80 p-4">
              {isPlainObject(nestedValue) || Array.isArray(nestedValue) ? (
                <JsonNode label={key} value={nestedValue} depth={depth + 1} />
              ) : (
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">{formatLabel(key)}</p>
                  <p className="mt-2 text-sm leading-6 text-slate-700">{renderPrimitive(nestedValue)}</p>
                </div>
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
      <p className="text-sm leading-6 text-slate-700">{renderPrimitive(value)}</p>
    </div>
  );
}


function EmptyModuleState({ title, module }: { title: string; module: StructuredModuleId }) {
  const hints: Record<StructuredModuleId, string> = {
    permit: "Isi data bangunan untuk melihat checklist dokumen, estimasi biaya, dan urutan pengurusan.",
    cooling: "Isi dimensi, orientasi, material, dan iklim untuk mendapatkan strategi pendinginan pasif.",
    disaster: "Isi konteks bencana dan deskripsi kerusakan untuk mendapatkan prioritas perbaikan.",
    settlement: "Isi kondisi infrastruktur dan budget untuk mendapatkan urutan intervensi kawasan.",
  };

  return (
    <Card className="border-dashed border-slate-300 bg-white/70">
      <CardContent className="flex min-h-[260px] flex-col items-center justify-center gap-4 p-8 text-center">
        <div className="rounded-3xl border border-sky-200 bg-sky-50 p-4 text-sky-700">
          <ClipboardList className="size-7" />
        </div>
        <div>
          <CardTitle className="text-base">{title}</CardTitle>
          <CardDescription className="mt-2 max-w-md leading-6">{hints[module]}</CardDescription>
        </div>
        <Badge className="border-slate-200 bg-white text-slate-600">Result will appear here</Badge>
      </CardContent>
    </Card>
  );
}

function GenericResult({ title, payload }: { title: string; payload: Record<string, unknown> }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>Fallback renderer for unexpected module payloads.</CardDescription>
      </CardHeader>
      <CardContent>
        <JsonNode value={payload} />
      </CardContent>
    </Card>
  );
}

export function ModuleResult({
  module,
  title,
  payload,
}: {
  module: StructuredModuleId;
  title: string;
  payload: Record<string, unknown> | null;
}) {
  if (!payload) {
    return <EmptyModuleState title={title} module={module} />;
  }

  switch (module) {
    case "permit":
      return <PermitResult title={title} payload={payload} />;
    case "cooling":
      return <CoolingResult title={title} payload={payload} />;
    case "disaster":
      return <DisasterResult title={title} payload={payload} />;
    case "settlement":
      return <SettlementResult title={title} payload={payload} />;
    default:
      return <GenericResult title={title} payload={payload} />;
  }
}
