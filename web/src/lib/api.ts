import type {
  AskResponse,
  BootstrapData,
  ChatMessageInput,
  CoolingFormData,
  DisasterFormData,
  HealthData,
  ModuleResponse,
  PermitFormData,
  SettlementFormData,
} from "@/lib/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    let detail = `Request failed with ${response.status}`;

    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        detail = payload.detail;
      }
    } catch {
      // ignore
    }

    throw new Error(detail);
  }

  return (await response.json()) as T;
}

export function fetchBootstrap() {
  return request<BootstrapData>("/api/bootstrap");
}

export function fetchHealth() {
  return request<HealthData>("/health");
}

export function askQuestion(question: string, history: ChatMessageInput[]) {
  return request<AskResponse>("/api/ask", {
    method: "POST",
    body: JSON.stringify({ question, history }),
  });
}

export function submitPermit(payload: PermitFormData) {
  return request<ModuleResponse>("/api/permit", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function submitCooling(payload: CoolingFormData) {
  return request<ModuleResponse>("/api/cooling", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function submitDisaster(payload: DisasterFormData) {
  return request<ModuleResponse>("/api/disaster", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function submitSettlement(payload: SettlementFormData) {
  return request<ModuleResponse>("/api/settlement", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export { API_BASE_URL };
