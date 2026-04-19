const SECTION_ORDER = [
  "RINGKASAN",
  "DETAIL REGULASI",
  "SARAN TEKNIS",
  "SUMBER",
] as const;

export interface ParsedAnswer {
  cleaned: string;
  sections: Partial<Record<(typeof SECTION_ORDER)[number], string>>;
}

export function cleanAnswerText(text: string) {
  let cleaned = (text ?? "").replace(/\r\n/g, "\n").trim();

  if (
    cleaned.length >= 2 &&
    ((cleaned.startsWith('"') && cleaned.endsWith('"')) ||
      (cleaned.startsWith("'") && cleaned.endsWith("'")))
  ) {
    cleaned = cleaned.slice(1, -1).trim();
  }

  cleaned = cleaned.replace(/\n{3,}/g, "\n\n");
  return cleaned;
}

function normalizeHeading(line: string) {
  const normalized = line.replace(/^\d+\.\s*/, "").trim().toUpperCase();
  return SECTION_ORDER.includes(normalized as (typeof SECTION_ORDER)[number])
    ? (normalized as (typeof SECTION_ORDER)[number])
    : null;
}

export function parseStructuredAnswer(text: string): ParsedAnswer {
  const cleaned = cleanAnswerText(text);
  const sections: Partial<Record<(typeof SECTION_ORDER)[number], string>> = {};
  let current: (typeof SECTION_ORDER)[number] | null = null;
  const buffers: Partial<Record<(typeof SECTION_ORDER)[number], string[]>> = {};

  for (const rawLine of cleaned.split("\n")) {
    const heading = normalizeHeading(rawLine);
    if (heading) {
      current = heading;
      buffers[current] = buffers[current] ?? [];
      continue;
    }

    if (!current) {
      continue;
    }

    buffers[current]?.push(rawLine);
  }

  for (const key of SECTION_ORDER) {
    const value = buffers[key]?.join("\n").trim();
    if (value) {
      sections[key] = value;
    }
  }

  return { cleaned, sections };
}

export { SECTION_ORDER };
