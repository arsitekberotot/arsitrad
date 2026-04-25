"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowRight,
  Building2,
  Image as ImageIcon,
  Flame,
  LoaderCircle,
  MapPinned,
  Menu,
  Paperclip,
  RefreshCcw,
  X,
  Wind,
} from "lucide-react";

import { AnswerView } from "@/components/answer-view";
import { ModuleResult } from "@/components/module-result";
import { StatusSidebar } from "@/components/status-sidebar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  API_BASE_URL,
  askQuestion,
  fetchBootstrap,
  fetchHealth,
  submitCooling,
  submitDisaster,
  submitPermit,
  submitSettlement,
} from "@/lib/api";
import type {
  AskResponse,
  BootstrapData,
  ChatMessageInput,
  CoolingFormData,
  DisasterFormData,
  HealthData,
  ImageAttachment,
  ModuleId,
  ModuleResponse,
  PermitFormData,
  SettlementFormData,
} from "@/lib/types";
import { formatLabel } from "@/lib/utils";

type ConversationEntry = {
  id: string;
  role: "user" | "assistant";
  content: string;
  images?: ImageAttachment[];
  response?: AskResponse;
};

const FALLBACK_BOOTSTRAP: BootstrapData = {
  app_title: "Arsitrad Web",
  disclaimer:
    "Arsitrad adalah alat bantu informasi regulasi, bukan pengganti konsultasi profesional.",
  default_question: "Apa syarat PBG untuk rumah tinggal 2 lantai di Semarang?",
  quick_prompts: [
    "Apa syarat PBG untuk rumah tinggal 2 lantai di Semarang?",
    "Apa aturan bangunan gedung negara terkait SBKBG?",
    "Apakah RDTR wajib dicek sebelum mengurus PBG?",
  ],
  modules: [
    { id: "regulation", title: "Regulation QA", description: "Tanya regulasi utama Arsitrad." },
    { id: "permit", title: "Permit Navigator", description: "Checklist dan estimasi alur izin." },
    { id: "cooling", title: "Passive Cooling", description: "Strategi pendinginan pasif." },
    { id: "disaster", title: "Disaster Reporter", description: "Klasifikasi kerusakan bangunan." },
    { id: "settlement", title: "Settlement Upgrading", description: "Prioritas intervensi permukiman." },
  ],
};

const PERMIT_DEFAULTS: PermitFormData = {
  building_type: "rumah_tinggal",
  location: "Semarang",
  floor_area_m2: 120,
  land_area_m2: 150,
  building_height_m: 8,
  building_function: "hunian",
};

const COOLING_DEFAULTS: CoolingFormData = {
  dimensions: { length_m: 8, width_m: 10, height_m: 3.5, floor_count: 1 },
  orientation: "barat",
  materials: { wall_material: "bata", roof_material: "metal" },
  climate_zone: "tropical_basah",
  budget_idr: 5000000,
};

const DISASTER_DEFAULTS: DisasterFormData = {
  location: "Semarang",
  disaster_type: "gempa",
  building_type: "rumah_tinggal",
  damage_description: "Dinding retak diagonal, atap bergeser, beberapa bagian lantai tidak rata.",
  floor_area_m2: 60,
  photo_urls: [],
};

const SETTLEMENT_DEFAULTS: SettlementFormData = {
  location: "Semarang",
  population_density: 500,
  current_infrastructure: "jalan sempit, drainase buruk, air sumur, listrik tersedia",
  budget_constraint_idr: 500000000,
  priority_goals: ["sanitasi", "air bersih", "drainase"],
};

function ModuleTabButton({
  active,
  title,
  description,
  onClick,
}: {
  active: boolean;
  title: string;
  description: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-2xl border p-4 text-left transition ${
        active
          ? "border-sky-300 bg-sky-100 shadow-lg shadow-sky-200/60"
          : "border-slate-200 bg-white/80 hover:border-sky-200 hover:bg-sky-50"
      }`}
    >
      <div className="mb-2 flex items-center gap-2">
        <span className="text-sm font-semibold text-slate-950">{title}</span>
        {active ? <Badge className="border-sky-200 bg-sky-100 text-sky-700">Active</Badge> : null}
      </div>
      <p className="text-sm text-slate-600">{description}</p>
    </button>
  );
}

function QuestionBubble({ content, images = [] }: { content: string; images?: ImageAttachment[] }) {
  return (
    <div className="ml-auto max-w-3xl rounded-3xl border border-sky-200 bg-sky-100 p-4 text-sm leading-7 text-sky-950">
      <p>{content}</p>
      {images.length > 0 ? (
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          {images.map((image) => (
            <div key={image.id} className="overflow-hidden rounded-2xl border border-sky-200 bg-white/80">
              {/* eslint-disable-next-line @next/next/no-img-element -- user-uploaded data URLs are local previews, not optimizable remote assets. */}
              <img src={image.data_url} alt={image.name} className="h-32 w-full object-cover" />
              <div className="p-2 text-xs leading-5 text-slate-700">
                <p className="truncate font-medium text-slate-900">{image.name}</p>
                <p>{image.content_type} · {Math.ceil(image.size_bytes / 1024)} KB</p>
              </div>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function ArsitradWorkbench() {
  const [bootstrap, setBootstrap] = useState<BootstrapData | null>(null);
  const [health, setHealth] = useState<HealthData | null>(null);
  const [bootstrapError, setBootstrapError] = useState<string | null>(null);
  const [statusOpen, setStatusOpen] = useState(false);
  const [question, setQuestion] = useState(FALLBACK_BOOTSTRAP.default_question);
  const [conversation, setConversation] = useState<ConversationEntry[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Tanyakan regulasi bangunan, SBKBG, PBG, RDTR, RTRW, atau buka module cards buat workflow yang lebih spesifik.",
    },
  ]);
  const [chatError, setChatError] = useState<string | null>(null);
  const [chatLoading, setChatLoading] = useState(false);
  const [attachedImages, setAttachedImages] = useState<ImageAttachment[]>([]);
  const [activeModule, setActiveModule] = useState<ModuleId>("regulation");
  const [permitForm, setPermitForm] = useState<PermitFormData>(PERMIT_DEFAULTS);
  const [coolingForm, setCoolingForm] = useState<CoolingFormData>(COOLING_DEFAULTS);
  const [disasterForm, setDisasterForm] = useState<DisasterFormData>(DISASTER_DEFAULTS);
  const [settlementForm, setSettlementForm] = useState<SettlementFormData>(SETTLEMENT_DEFAULTS);
  const [moduleLoading, setModuleLoading] = useState<ModuleId | null>(null);
  const [moduleError, setModuleError] = useState<string | null>(null);
  const [moduleResults, setModuleResults] = useState<Partial<Record<ModuleId, ModuleResponse["payload"]>>>({});
  const idCounter = useRef(1);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const moduleList = bootstrap?.modules ?? FALLBACK_BOOTSTRAP.modules;

  useEffect(() => {
    let cancelled = false;

    async function boot() {
      try {
        const [bootstrapData, healthData] = await Promise.all([
          fetchBootstrap(),
          fetchHealth(),
        ]);

        if (cancelled) return;

        setBootstrap(bootstrapData);
        setHealth(healthData);
        setQuestion(bootstrapData.default_question);
      } catch (error) {
        if (cancelled) return;

        setBootstrapError(error instanceof Error ? error.message : "Failed to load backend bootstrap.");
      }
    }

    void boot();

    return () => {
      cancelled = true;
    };
  }, []);

  const historyForApi = useMemo<ChatMessageInput[]>(() => {
    return conversation
      .filter((entry) => entry.id !== "welcome")
      .map((entry) => ({ role: entry.role, content: entry.content }));
  }, [conversation]);

  async function refreshHealth() {
    try {
      setHealth(await fetchHealth());
    } catch {
      // ignore noisy refresh failures
    }
  }

  function removeAttachedImage(id: string) {
    setAttachedImages((prev) => prev.filter((image) => image.id !== id));
  }

  async function handleImageFiles(files: FileList | null) {
    if (!files || files.length === 0) {
      return;
    }

    const selectedFiles = Array.from(files).filter((file) => file.type.startsWith("image/"));
    if (selectedFiles.length === 0) {
      setChatError("Upload gambar saja: denah, foto tapak, atau referensi visual bangunan.");
      return;
    }

    const remainingSlots = Math.max(0, 4 - attachedImages.length);
    const filesToRead = selectedFiles.slice(0, remainingSlots);
    if (filesToRead.length === 0) {
      setChatError("Maksimal 4 gambar per pesan.");
      return;
    }

    const loadedImages = await Promise.all(
      filesToRead.map(
        (file) =>
          new Promise<ImageAttachment>((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => {
              resolve({
                id: `${file.name}-${file.size}-${idCounter.current++}`,
                name: file.name,
                content_type: file.type || "image/unknown",
                size_bytes: file.size,
                data_url: String(reader.result),
              });
            };
            reader.onerror = () => reject(reader.error ?? new Error("Failed to read image."));
            reader.readAsDataURL(file);
          }),
      ),
    );

    setAttachedImages((prev) => [...prev, ...loadedImages]);
    setChatError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  async function handleAsk(prefilled?: string) {
    const currentQuestion = (prefilled ?? question).trim() || (attachedImages.length > 0 ? "Analisis gambar terlampir untuk konteks regulasi dan arsitektur." : "");
    if (!currentQuestion) {
      return;
    }

    setChatLoading(true);
    setChatError(null);

    const nextId = () => {
      const value = idCounter.current;
      idCounter.current += 1;
      return value;
    };

    const imagesToSend = prefilled ? [] : attachedImages;
    const userEntry: ConversationEntry = {
      id: `user-${nextId()}`,
      role: "user",
      content: currentQuestion,
      images: imagesToSend,
    };

    setConversation((prev) => [...prev, userEntry]);
    setQuestion("");
    setAttachedImages([]);

    try {
      const response = await askQuestion(currentQuestion, historyForApi, imagesToSend);
      setConversation((prev) => [
        ...prev,
        {
          id: `assistant-${nextId()}`,
          role: "assistant",
          content: response.answer,
          response,
        },
      ]);
      await refreshHealth();
    } catch (error) {
      setChatError(error instanceof Error ? error.message : "Request failed.");
      setQuestion(currentQuestion);
      setAttachedImages(imagesToSend);
    } finally {
      setChatLoading(false);
    }
  }

  async function handleModuleSubmit(module: ModuleId) {
    setModuleLoading(module);
    setModuleError(null);

    try {
      let response: ModuleResponse;

      switch (module) {
        case "permit":
          response = await submitPermit(permitForm);
          break;
        case "cooling":
          response = await submitCooling(coolingForm);
          break;
        case "disaster":
          response = await submitDisaster(disasterForm);
          break;
        case "settlement":
          response = await submitSettlement(settlementForm);
          break;
        default:
          return;
      }

      setModuleResults((prev) => ({ ...prev, [module]: response.payload }));
    } catch (error) {
      setModuleError(error instanceof Error ? error.message : "Module request failed.");
    } finally {
      setModuleLoading(null);
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col gap-4 overflow-hidden">
      <Card className="shrink-0 border-sky-200 bg-white/95 shadow-lg shadow-slate-200/60">
        <CardContent className="flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex size-11 shrink-0 items-center justify-center rounded-2xl border border-sky-200 bg-sky-100 text-lg font-black tracking-tight text-sky-700">
              A
            </div>
            <div className="min-w-0">
              <h1 className="truncate text-xl font-semibold tracking-tight text-slate-950">Arsitrad</h1>
              <p className="truncate text-sm text-slate-600">Regulation QA + architecture helper workflows</p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge className={health ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-amber-200 bg-amber-50 text-amber-700"}>
              {health ? "API connected" : "API waiting"}
            </Badge>
            <Badge className={health?.model_exists ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-amber-200 bg-amber-50 text-amber-700"}>
              {health?.model_exists ? "GGUF found" : "GGUF pending"}
            </Badge>
            <Button variant="outline" size="sm" onClick={() => setStatusOpen((value) => !value)} aria-expanded={statusOpen}>
              <Menu className="size-4" /> {statusOpen ? "Hide status" : "Runtime"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {statusOpen ? (
        <div className="max-h-[42vh] shrink-0 overflow-y-auto pr-1">
          <StatusSidebar bootstrap={bootstrap} health={health} apiBaseUrl={API_BASE_URL} />
        </div>
      ) : null}

        <Card className="flex min-h-0 flex-1 flex-col overflow-hidden">
          <CardHeader className="shrink-0">
            <div className="flex items-center justify-between gap-3">
              <div>
                <CardTitle>Workspace</CardTitle>
                <CardDescription>
                  Choose a workflow. Regulation QA stays primary; helper modules handle focused architectural tasks.
                </CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={() => void refreshHealth()}>
                <RefreshCcw className="size-4" /> Refresh status
              </Button>
            </div>
          </CardHeader>
          <CardContent className="flex min-h-0 flex-1 flex-col gap-6 overflow-hidden">
            <div className="grid shrink-0 gap-3 lg:grid-cols-5">
              {moduleList.map((module) => (
                <ModuleTabButton
                  key={module.id}
                  active={activeModule === module.id}
                  title={module.title}
                  description={module.description}
                  onClick={() => setActiveModule(module.id)}
                />
              ))}
            </div>

            {bootstrapError ? (
              <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
                Backend bootstrap failed: {bootstrapError}
              </div>
            ) : null}

            {activeModule === "regulation" ? (
              <div className="flex h-full min-h-0 flex-col gap-4 overflow-hidden">
                <div className="shrink-0 flex flex-wrap gap-2">
                  {(bootstrap?.quick_prompts ?? FALLBACK_BOOTSTRAP.quick_prompts).map((prompt) => (
                    <Button
                      key={prompt}
                      variant="outline"
                      size="sm"
                      onClick={() => void handleAsk(prompt)}
                      disabled={chatLoading}
                    >
                      {prompt}
                    </Button>
                  ))}
                </div>

                <div data-testid="chat-scroll-container" className="min-h-0 flex-1 space-y-4 overflow-y-auto rounded-3xl border border-slate-200 bg-slate-100/70 p-4">
                  {conversation.map((entry) => (
                    <div key={entry.id} className="space-y-4">
                      {entry.role === "user" ? (
                        <QuestionBubble content={entry.content} images={entry.images} />
                      ) : entry.response ? (
                        <AnswerView response={entry.response} />
                      ) : (
                        <Card className="border-slate-200 bg-white/80">
                          <CardContent className="p-4 text-sm leading-7 text-slate-700">
                            {entry.content}
                          </CardContent>
                        </Card>
                      )}
                    </div>
                  ))}

                  {chatLoading ? (
                    <Card className="border-slate-200 bg-white/80">
                      <CardContent className="flex items-center gap-3 p-4 text-sm text-slate-700">
                        <LoaderCircle className="size-4 animate-spin text-sky-600" />
                        Arsitrad is retrieving sources and drafting the answer.
                      </CardContent>
                    </Card>
                  ) : null}
                </div>

                <div data-testid="chat-input-area" className="shrink-0 space-y-3 rounded-3xl border border-slate-200 bg-white/80 p-4">
                  <Label htmlFor="reg-question">Pertanyaan</Label>
                  <Textarea
                    id="reg-question"
                    value={question}
                    onChange={(event) => setQuestion(event.target.value)}
                    placeholder={bootstrap?.default_question ?? FALLBACK_BOOTSTRAP.default_question}
                    className="min-h-[130px]"
                  />
                  {attachedImages.length > 0 ? (
                    <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                      {attachedImages.map((image) => (
                        <div key={image.id} className="relative overflow-hidden rounded-2xl border border-slate-200 bg-slate-50">
                          {/* eslint-disable-next-line @next/next/no-img-element -- user-uploaded data URLs are local previews, not optimizable remote assets. */}
                          <img src={image.data_url} alt={image.name} className="h-24 w-full object-cover" />
                          <button
                            type="button"
                            aria-label={`Remove ${image.name}`}
                            className="absolute right-2 top-2 rounded-full bg-white/90 p-1 text-slate-700 shadow"
                            onClick={() => removeAttachedImage(image.id)}
                          >
                            <X className="size-3" />
                          </button>
                          <div className="p-2 text-xs leading-5 text-slate-600">
                            <p className="truncate font-medium text-slate-900">{image.name}</p>
                            <p>{Math.ceil(image.size_bytes / 1024)} KB</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : null}

                  <div className="flex flex-wrap items-center justify-between gap-3">
                    {chatError ? <p className="text-sm text-rose-600">{chatError}</p> : <span className="text-sm text-slate-500">Ask a specific regulation question. Attach floor plans or site photos when visual context matters.</span>}
                    <div className="flex flex-wrap items-center gap-2">
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept="image/*"
                        multiple
                        className="hidden"
                        onChange={(event) => void handleImageFiles(event.target.files)}
                      />
                      <Button type="button" variant="outline" onClick={() => fileInputRef.current?.click()} disabled={chatLoading || attachedImages.length >= 4}>
                        <Paperclip className="size-4" /> Attach images
                      </Button>
                      <Button onClick={() => void handleAsk()} disabled={chatLoading}>
                        {chatLoading ? <LoaderCircle className="size-4 animate-spin" /> : attachedImages.length > 0 ? <ImageIcon className="size-4" /> : <ArrowRight className="size-4" />}
                        Tanya Arsitrad
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            ) : null}

            {activeModule === "permit" ? (
              <div className="min-h-0 flex-1 overflow-y-auto pr-1">
              <div className="grid gap-6 2xl:grid-cols-[0.72fr_1.28fr]">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-lg"><Building2 className="size-5 text-sky-600" /> Permit Navigator</CardTitle>
                    <CardDescription>Generate checklist dan estimasi alur pengurusan izin bangunan.</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <Label htmlFor="permit-type">Tipe bangunan</Label>
                      <Select id="permit-type" value={permitForm.building_type} onChange={(event) => setPermitForm({ ...permitForm, building_type: event.target.value })}>
                        {[
                          "rumah_tinggal",
                          "apartemen",
                          "gedung_komersial",
                          "gedung_industri",
                          "fasilitas_umum",
                        ].map((value) => <option key={value} value={value}>{formatLabel(value)}</option>)}
                      </Select>
                    </div>
                    <div>
                      <Label htmlFor="permit-location">Lokasi</Label>
                      <Input id="permit-location" value={permitForm.location} onChange={(event) => setPermitForm({ ...permitForm, location: event.target.value })} />
                    </div>
                    <div className="grid gap-4 md:grid-cols-3">
                      <div>
                        <Label htmlFor="permit-floor">Luas lantai</Label>
                        <Input id="permit-floor" type="number" value={permitForm.floor_area_m2} onChange={(event) => setPermitForm({ ...permitForm, floor_area_m2: Number(event.target.value) })} />
                      </div>
                      <div>
                        <Label htmlFor="permit-land">Luas tanah</Label>
                        <Input id="permit-land" type="number" value={permitForm.land_area_m2} onChange={(event) => setPermitForm({ ...permitForm, land_area_m2: Number(event.target.value) })} />
                      </div>
                      <div>
                        <Label htmlFor="permit-height">Tinggi</Label>
                        <Input id="permit-height" type="number" value={permitForm.building_height_m} onChange={(event) => setPermitForm({ ...permitForm, building_height_m: Number(event.target.value) })} />
                      </div>
                    </div>
                    <div>
                      <Label htmlFor="permit-function">Fungsi bangunan</Label>
                      <Select id="permit-function" value={permitForm.building_function} onChange={(event) => setPermitForm({ ...permitForm, building_function: event.target.value })}>
                        {["hunian", "usaha", "campuran"].map((value) => <option key={value} value={value}>{formatLabel(value)}</option>)}
                      </Select>
                    </div>
                    <Button onClick={() => void handleModuleSubmit("permit")} disabled={moduleLoading === "permit"} className="w-full">
                      {moduleLoading === "permit" ? <LoaderCircle className="size-4 animate-spin" /> : <ArrowRight className="size-4" />} Generate guidance
                    </Button>
                  </CardContent>
                </Card>
                <ModuleResult module="permit" title="Permit guidance" payload={moduleResults.permit ?? null} />
              </div>
              </div>
            ) : null}

            {activeModule === "cooling" ? (
              <div className="min-h-0 flex-1 overflow-y-auto pr-1">
              <div className="grid gap-6 2xl:grid-cols-[0.72fr_1.28fr]">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-lg"><Wind className="size-5 text-sky-600" /> Passive Cooling</CardTitle>
                    <CardDescription>Quick passive-cooling recommendations for tropical building setups.</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid gap-4 md:grid-cols-2">
                      <div>
                        <Label>Panjang</Label>
                        <Input type="number" value={coolingForm.dimensions.length_m} onChange={(event) => setCoolingForm({ ...coolingForm, dimensions: { ...coolingForm.dimensions, length_m: Number(event.target.value) } })} />
                      </div>
                      <div>
                        <Label>Lebar</Label>
                        <Input type="number" value={coolingForm.dimensions.width_m} onChange={(event) => setCoolingForm({ ...coolingForm, dimensions: { ...coolingForm.dimensions, width_m: Number(event.target.value) } })} />
                      </div>
                      <div>
                        <Label>Tinggi</Label>
                        <Input type="number" value={coolingForm.dimensions.height_m} onChange={(event) => setCoolingForm({ ...coolingForm, dimensions: { ...coolingForm.dimensions, height_m: Number(event.target.value) } })} />
                      </div>
                      <div>
                        <Label>Jumlah lantai</Label>
                        <Input type="number" value={coolingForm.dimensions.floor_count} onChange={(event) => setCoolingForm({ ...coolingForm, dimensions: { ...coolingForm.dimensions, floor_count: Number(event.target.value) } })} />
                      </div>
                    </div>
                    <div className="grid gap-4 md:grid-cols-2">
                      <div>
                        <Label>Orientasi</Label>
                        <Select value={coolingForm.orientation} onChange={(event) => setCoolingForm({ ...coolingForm, orientation: event.target.value })}>
                          {["utara", "selatan", "timur", "barat"].map((value) => <option key={value} value={value}>{formatLabel(value)}</option>)}
                        </Select>
                      </div>
                      <div>
                        <Label>Zona iklim</Label>
                        <Select value={coolingForm.climate_zone} onChange={(event) => setCoolingForm({ ...coolingForm, climate_zone: event.target.value })}>
                          {["dataran_rendah_pesisir", "dataran_tinggi", "tropical_basah", "tropical_kering"].map((value) => <option key={value} value={value}>{formatLabel(value)}</option>)}
                        </Select>
                      </div>
                      <div>
                        <Label>Material dinding</Label>
                        <Select value={coolingForm.materials.wall_material} onChange={(event) => setCoolingForm({ ...coolingForm, materials: { ...coolingForm.materials, wall_material: event.target.value } })}>
                          {["bata", "beton", "kayu", "batako", "hebel"].map((value) => <option key={value} value={value}>{formatLabel(value)}</option>)}
                        </Select>
                      </div>
                      <div>
                        <Label>Material atap</Label>
                        <Select value={coolingForm.materials.roof_material} onChange={(event) => setCoolingForm({ ...coolingForm, materials: { ...coolingForm.materials, roof_material: event.target.value } })}>
                          {["genteng", "metal", "beton"].map((value) => <option key={value} value={value}>{formatLabel(value)}</option>)}
                        </Select>
                      </div>
                    </div>
                    <div>
                      <Label>Budget (IDR)</Label>
                      <Input type="number" value={coolingForm.budget_idr ?? 0} onChange={(event) => setCoolingForm({ ...coolingForm, budget_idr: Number(event.target.value) })} />
                    </div>
                    <Button onClick={() => void handleModuleSubmit("cooling")} disabled={moduleLoading === "cooling"} className="w-full">
                      {moduleLoading === "cooling" ? <LoaderCircle className="size-4 animate-spin" /> : <ArrowRight className="size-4" />} Generate cooling plan
                    </Button>
                  </CardContent>
                </Card>
                <ModuleResult module="cooling" title="Cooling recommendations" payload={moduleResults.cooling ?? null} />
              </div>
              </div>
            ) : null}

            {activeModule === "disaster" ? (
              <div className="min-h-0 flex-1 overflow-y-auto pr-1">
              <div className="grid gap-6 2xl:grid-cols-[0.72fr_1.28fr]">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-lg"><Flame className="size-5 text-sky-600" /> Disaster Reporter</CardTitle>
                    <CardDescription>Classify damage and get a structured repair recommendation payload.</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid gap-4 md:grid-cols-2">
                      <div>
                        <Label>Lokasi</Label>
                        <Input value={disasterForm.location} onChange={(event) => setDisasterForm({ ...disasterForm, location: event.target.value })} />
                      </div>
                      <div>
                        <Label>Tipe bencana</Label>
                        <Select value={disasterForm.disaster_type} onChange={(event) => setDisasterForm({ ...disasterForm, disaster_type: event.target.value })}>
                          {["gempa", "banjir", "tsunami", "longsor", "puting_beliung", "kebakaran"].map((value) => <option key={value} value={value}>{formatLabel(value)}</option>)}
                        </Select>
                      </div>
                      <div>
                        <Label>Tipe bangunan</Label>
                        <Select value={disasterForm.building_type} onChange={(event) => setDisasterForm({ ...disasterForm, building_type: event.target.value })}>
                          {["rumah_tinggal", "gedung_perkantoran", "sekolah", "pasar", "lainnya"].map((value) => <option key={value} value={value}>{formatLabel(value)}</option>)}
                        </Select>
                      </div>
                      <div>
                        <Label>Luas lantai</Label>
                        <Input type="number" value={disasterForm.floor_area_m2 ?? 0} onChange={(event) => setDisasterForm({ ...disasterForm, floor_area_m2: Number(event.target.value) })} />
                      </div>
                    </div>
                    <div>
                      <Label>Deskripsi kerusakan</Label>
                      <Textarea value={disasterForm.damage_description} onChange={(event) => setDisasterForm({ ...disasterForm, damage_description: event.target.value })} className="min-h-[160px]" />
                    </div>
                    <div>
                      <Label>Photo URLs (comma-separated, optional)</Label>
                      <Input value={disasterForm.photo_urls.join(", ")} onChange={(event) => setDisasterForm({ ...disasterForm, photo_urls: event.target.value.split(",").map((item) => item.trim()).filter(Boolean) })} />
                    </div>
                    <Button onClick={() => void handleModuleSubmit("disaster")} disabled={moduleLoading === "disaster"} className="w-full">
                      {moduleLoading === "disaster" ? <LoaderCircle className="size-4 animate-spin" /> : <ArrowRight className="size-4" />} Generate report
                    </Button>
                  </CardContent>
                </Card>
                <ModuleResult module="disaster" title="Disaster report" payload={moduleResults.disaster ?? null} />
              </div>
              </div>
            ) : null}

            {activeModule === "settlement" ? (
              <div className="min-h-0 flex-1 overflow-y-auto pr-1">
              <div className="grid gap-6 2xl:grid-cols-[0.72fr_1.28fr]">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-lg"><MapPinned className="size-5 text-sky-600" /> Settlement Upgrading</CardTitle>
                    <CardDescription>Budget-aware prioritization for settlement improvement actions.</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid gap-4 md:grid-cols-2">
                      <div>
                        <Label>Lokasi</Label>
                        <Input value={settlementForm.location} onChange={(event) => setSettlementForm({ ...settlementForm, location: event.target.value })} />
                      </div>
                      <div>
                        <Label>Kepadatan (orang/ha)</Label>
                        <Input type="number" value={settlementForm.population_density} onChange={(event) => setSettlementForm({ ...settlementForm, population_density: Number(event.target.value) })} />
                      </div>
                    </div>
                    <div>
                      <Label>Infrastruktur saat ini</Label>
                      <Textarea value={settlementForm.current_infrastructure} onChange={(event) => setSettlementForm({ ...settlementForm, current_infrastructure: event.target.value })} className="min-h-[160px]" />
                    </div>
                    <div>
                      <Label>Budget (IDR)</Label>
                      <Input type="number" value={settlementForm.budget_constraint_idr} onChange={(event) => setSettlementForm({ ...settlementForm, budget_constraint_idr: Number(event.target.value) })} />
                    </div>
                    <div>
                      <Label>Priority goals (comma-separated)</Label>
                      <Input value={settlementForm.priority_goals.join(", ")} onChange={(event) => setSettlementForm({ ...settlementForm, priority_goals: event.target.value.split(",").map((item) => item.trim()).filter(Boolean) })} />
                    </div>
                    <Button onClick={() => void handleModuleSubmit("settlement")} disabled={moduleLoading === "settlement"} className="w-full">
                      {moduleLoading === "settlement" ? <LoaderCircle className="size-4 animate-spin" /> : <ArrowRight className="size-4" />} Generate upgrading plan
                    </Button>
                  </CardContent>
                </Card>
                <ModuleResult module="settlement" title="Settlement upgrading plan" payload={moduleResults.settlement ?? null} />
              </div>
              </div>
            ) : null}

            {moduleError ? (
              <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
                {moduleError}
              </div>
            ) : null}
          </CardContent>
        </Card>
    </div>
  );
}
