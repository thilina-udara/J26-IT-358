import type {
  Comparison, Credentials, Farmer, HistoricalScenarioRequest, HistoricalScenarioResponse,
  Personalized, Plan, PlanFields, PlanPage, PlanningRequest, ResearchDemoStatus,
  ProductionConcentrationIndicator, SavedPlanning, Session, Submission, Workflow,
} from "./contracts";

export class ApiError extends Error {
  constructor(public status: number, message: string, public fields: Record<string, string> = {}, public retryAfter: string | null = null) { super(message); this.name = "ApiError"; }
}

function errorDetails(detail: unknown): { message: string; fields: Record<string, string> } {
  if (typeof detail === "string") return { message: detail, fields: {} };
  const fields: Record<string, string> = {};
  if (Array.isArray(detail)) for (const item of detail) {
    if (item && Array.isArray(item.loc) && typeof item.msg === "string") fields[String(item.loc.at(-1))] = item.msg;
  }
  return { message: Object.keys(fields).length ? "Please check the highlighted fields." : "The request could not be completed.", fields };
}

export function createApi(baseUrl: string, token: () => string | null, onUnauthorized: () => void, transport: typeof fetch = fetch) {
  const base = baseUrl.replace(/\/+$/, "");
  async function request<T>(path: string, method = "GET", body?: unknown, authenticated = true, signal?: AbortSignal): Promise<T> {
    const credential = authenticated ? token() : null;
    if (authenticated && !credential) throw new ApiError(401, "Please log in to continue.");
    let response: Response;
    try {
      response = await transport(base + path, {
        method, credentials: "omit", cache: "no-store", signal,
        headers: { Accept: "application/json", ...(body === undefined ? {} : { "Content-Type": "application/json" }), ...(credential ? { Authorization: `Bearer ${credential}` } : {}) },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch (error) {
      if (signal?.aborted) throw error;
      throw new ApiError(0, method === "GET" ? "Cannot reach the backend. Check your connection and backend/CORS configuration." : "No response received. A write may have completed. Check your saved plans before submitting again.");
    }
    if (response.status === 204) return undefined as T;
    if (response.status === 401 && credential && token() === credential) onUnauthorized();
    let payload: unknown;
    try { payload = await response.json(); } catch { throw new ApiError(response.status, "Unexpected server response. Check saved plans before repeating a write."); }
    if (!response.ok) {
      const detail = errorDetails((payload as { detail?: unknown })?.detail);
      throw new ApiError(response.status, detail.message, detail.fields, response.headers.get("Retry-After"));
    }
    return payload as T;
  }
  const id = encodeURIComponent;
  return {
    register: (body: Credentials) => request<Farmer>("/auth/register", "POST", body, false),
    login: (body: Credentials) => request<Session>("/auth/login", "POST", body, false),
    me: () => request<Farmer>("/auth/me"),
    logout: () => request<void>("/auth/logout", "POST"),
    list: (params: URLSearchParams, signal?: AbortSignal) => request<PlanPage>(`/api/cultivation-plans?${params}`, "GET", undefined, true, signal),
    read: (planId: string, signal?: AbortSignal) => request<{ plan: Plan; personalized_plan: SavedPlanning | null }>(`/api/farmer-workflow/plans/${id(planId)}`, "GET", undefined, true, signal),
    productionConcentrationIndicator: (planId: string, signal?: AbortSignal) => request<ProductionConcentrationIndicator>(`/api/cultivation-plans/${id(planId)}/production-concentration-indicator`, "GET", undefined, true, signal),
    create: ({ farmer_declared_season, ...fields }: PlanFields) => request<Submission>("/api/farmer-workflow/plans", "POST", { ...fields, season: farmer_declared_season }),
    update: (planId: string, fields: PlanFields) => request<{ plan: Plan }>(`/api/cultivation-plans/${id(planId)}`, "PUT", fields),
    cancel: (planId: string) => request<{ plan: Plan }>(`/api/cultivation-plans/${id(planId)}`, "DELETE"),
    analyze: (planId: string, season?: string, asOf?: string) => request<Workflow>("/api/farmer-workflow/analyze", "POST", { plan_id: planId, ...(season ? { season } : {}), ...(asOf ? { as_of: asOf } : {}) }),
    compare: (plan: Plan, asOf?: string) => request<Comparison>("/api/cultivation-analysis/alternatives", "POST", {
      selected_crop: plan.crop, district: plan.district, region: plan.region, land_size_acres: plan.land_size_acres,
      planting_date: plan.planting_date, expected_harvest_date: plan.expected_harvest_date, replacing_plan_id: plan.plan_id,
      ...(asOf ? { as_of: asOf } : {}),
    }),
    generate: (body: PlanningRequest) => request<Personalized>("/api/farmer-workflow/select", "POST", { ...body, save: false }),
    save: (body: PlanningRequest) => request<SavedPlanning>("/api/farmer-workflow/select", "POST", { ...body, save: true }),
    saved: (planId: string) => request<SavedPlanning>(`/api/personalized-cultivation-plans/${id(planId)}`),
    researchDemoStatus: (signal?: AbortSignal) => request<ResearchDemoStatus>("/api/research-demo/status", "GET", undefined, false, signal),
    researchDemoEvaluate: (body: HistoricalScenarioRequest, signal?: AbortSignal) => request<HistoricalScenarioResponse>("/api/research-demo/evaluate", "POST", body, false, signal),
  };
}
export type FarmerApi = ReturnType<typeof createApi>;
