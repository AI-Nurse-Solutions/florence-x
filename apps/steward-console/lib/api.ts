// Typed client for the Florence-X API.
//
// Identity is the dev stand-in (X-Florence-* headers) the API's Zero-Trust
// middleware expects; real OIDC arrives later. Server Components call these
// directly; mutations run from Client Components via the same functions.
import type {
  AgentDefinition,
  EvidenceBundle,
  Incident,
  ReviewDecisionRequest,
  ReviewItem,
  ToolUsage,
  WorkflowRun,
} from "./types";

export const API_URL =
  process.env.NEXT_PUBLIC_FLORENCE_API_URL ?? "http://localhost:8000";

const IDENTITY = process.env.NEXT_PUBLIC_FLORENCE_IDENTITY ?? "steward-console";
const ROLE = process.env.NEXT_PUBLIC_FLORENCE_ROLE ?? "rn";

function headers(): HeadersInit {
  return {
    "Content-Type": "application/json",
    "X-Florence-Identity": IDENTITY,
    "X-Florence-Role": ROLE,
  };
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: headers(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`GET ${path} -> ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  listReviews: () => get<ReviewItem[]>("/reviews"),
  getReview: (id: string) => get<ReviewItem>(`/reviews/${id}`),
  getRun: (id: string) => get<WorkflowRun>(`/runs/${id}`),
  getEvidence: (id: string) => get<EvidenceBundle>(`/runs/${id}/evidence`),
  listIncidents: () => get<Incident[]>("/incidents"),
  listAgents: () => get<AgentDefinition[]>("/agents"),
  listTools: () => get<ToolUsage[]>("/tools"),

  async submitReview(id: string, decision: ReviewDecisionRequest): Promise<EvidenceBundle> {
    const res = await fetch(`${API_URL}/reviews/${id}`, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify(decision),
    });
    if (!res.ok) throw new Error(`POST /reviews/${id} -> ${res.status}`);
    return res.json() as Promise<EvidenceBundle>;
  },
};

export function eventStreamUrl(): string {
  const base = API_URL.replace(/^http/, "ws");
  const q = new URLSearchParams({ identity: IDENTITY, role: ROLE });
  return `${base}/events/ws?${q.toString()}`;
}
