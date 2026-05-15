import type { ApiErrorBody, RecommendationRequest, RecommendationResponse } from "@/lib/types";

function apiBase(): string {
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (raw) return raw.replace(/\/$/, "");
  return "/api/backend";
}

export class RecommendationApiError extends Error {
  status: number;
  body: unknown;

  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.name = "RecommendationApiError";
    this.status = status;
    this.body = body;
  }
}

function summarizeBody(status: number, body: unknown): string {
  if (body && typeof body === "object") {
    const b = body as ApiErrorBody;
    if (typeof b.message === "string" && b.message.trim()) return b.message.trim();
    if (typeof b.error === "string" && b.error.trim()) return `${b.error} (${status})`;
    if (Array.isArray(b.detail)) {
      const parts = b.detail
        .map((item) => {
          if (item && typeof item === "object" && "msg" in item) {
            const loc = "loc" in item && Array.isArray(item.loc) ? `${item.loc.join(".")}: ` : "";
            return `${loc}${String((item as { msg?: string }).msg ?? item)}`;
          }
          return JSON.stringify(item);
        })
        .filter(Boolean);
      if (parts.length) return parts.join("; ");
    }
    if (typeof b.detail === "string" && b.detail.trim()) return b.detail.trim();
  }
  return `Request failed (${status})`;
}

export async function postRecommendations(
  body: RecommendationRequest,
): Promise<RecommendationResponse> {
  const base = apiBase();
  const payload = {
    location: body.location,
    budget: body.budget ?? null,
    cuisine: body.cuisine,
    min_rating: body.min_rating,
    optional_notes: body.optional_notes,
    include_unknown_cost: body.include_unknown_cost,
    max_candidates: body.max_candidates ?? null,
  };

  const res = await fetch(`${base}/v1/recommendations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const text = await res.text();
  let json: unknown = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    throw new RecommendationApiError(text || `HTTP ${res.status}`, res.status, text);
  }

  if (!res.ok) {
    throw new RecommendationApiError(summarizeBody(res.status, json), res.status, json);
  }

  return json as RecommendationResponse;
}
