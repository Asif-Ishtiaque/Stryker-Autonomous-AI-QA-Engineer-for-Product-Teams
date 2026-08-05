import type {
  ChatMessageRequest,
  ChatMessageResponse,
  CredentialCreate,
  CredentialOut,
  KnowledgeSourceOut,
  LoginRequest,
  ProjectCreate,
  ProjectOut,
  ProjectStats,
  ProjectUpdate,
  RegisterRequest,
  ReportGenerateRequest,
  ReportOut,
  RequirementAnalysis,
  RequirementCreate,
  RequirementOut,
  RequirementUpdate,
  RunCreate,
  RunOut,
  SemanticSearchRequest,
  SemanticSearchResult,
  TokenResponse,
  UserOut,
} from "./types";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");
const API_PREFIX = "/api/v1";

const TOKEN_KEY = "stryker.access_token";
const REFRESH_KEY = "stryker.refresh_token";

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, message: string, body?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(REFRESH_KEY);
}

export function setTokens(tokens: TokenResponse | null) {
  if (typeof window === "undefined") return;
  if (!tokens) {
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(REFRESH_KEY);
    return;
  }
  window.localStorage.setItem(TOKEN_KEY, tokens.access_token);
  window.localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
}

/** Called on any 401 response so the app can redirect to /login. Wired up by AuthProvider. */
let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(handler: (() => void) | null) {
  onUnauthorized = handler;
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE" | "PUT";
  body?: unknown;
  isForm?: boolean;
  signal?: AbortSignal;
  /** Skip attaching the bearer token — only used for /auth/login, /auth/register, /auth/refresh. */
  skipAuth?: boolean;
  /** Internal: set when this call is itself the one retry after a token refresh, so a second
   * 401 doesn't loop back into another refresh attempt. Not for callers to pass directly. */
  _isRetry?: boolean;
}

// Concurrent requests that all hit a 401 at once (e.g. a page firing several queries on load
// with an expired token) must not each kick off their own refresh — they'd race to consume the
// same refresh token and all but one would get a stale-token error back. Sharing one in-flight
// promise means every caller awaits the same refresh instead of duplicating it.
let refreshPromise: Promise<TokenResponse | null> | null = null;

async function refreshAccessToken(): Promise<TokenResponse | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;
  if (!refreshPromise) {
    refreshPromise = request<TokenResponse>("/auth/refresh", {
      method: "POST",
      body: { refresh_token: refreshToken },
      skipAuth: true,
    })
      .catch(() => null)
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, isForm = false, signal, skipAuth = false, _isRetry = false } = options;

  const headers: Record<string, string> = {};
  if (!isForm && body !== undefined) headers["Content-Type"] = "application/json";

  if (!skipAuth) {
    const token = getAccessToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const url = `${API_BASE}${API_PREFIX}${path}`;

  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers,
      body: isForm ? (body as FormData) : body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (err) {
    throw new ApiError(0, "Network error — is the Stryker backend reachable?", err);
  }

  if (response.status === 401) {
    // skipAuth calls are /auth/login, /auth/register, or /auth/refresh itself — a 401 there is a
    // normal rejected credential/token, not an expired session, so it's left to the caller (the
    // login form shows "invalid email or password"; refreshAccessToken() above just returns null).
    // A retry that still 401s means the refresh token itself is no good — nothing left to try.
    if (!skipAuth && !_isRetry) {
      const refreshed = await refreshAccessToken();
      if (refreshed) {
        setTokens(refreshed);
        return request<T>(path, { ...options, _isRetry: true });
      }
    }
    if (!skipAuth) {
      setTokens(null);
      onUnauthorized?.();
    }
    throw new ApiError(401, "Unauthorized");
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  const data = text ? safeJsonParse(text) : undefined;

  if (!response.ok) {
    const message = extractErrorMessage(data) ?? `Request failed with status ${response.status}`;
    throw new ApiError(response.status, message, data);
  }

  return data as T;
}

function safeJsonParse(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function extractErrorMessage(data: unknown): string | null {
  if (data && typeof data === "object" && "detail" in data) {
    const detail = (data as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((d) => (typeof d === "object" && d && "msg" in d ? String((d as { msg: unknown }).msg) : String(d)))
        .join(", ");
    }
  }
  return null;
}

// ---------------------------------------------------------------------------
// auth
// ---------------------------------------------------------------------------

export const authApi = {
  register: (payload: RegisterRequest) =>
    request<UserOut>("/auth/register", { method: "POST", body: payload, skipAuth: true }),
  login: (payload: LoginRequest) =>
    request<TokenResponse>("/auth/login", { method: "POST", body: payload, skipAuth: true }),
  me: () => request<UserOut>("/auth/me"),
};

// ---------------------------------------------------------------------------
// projects
// ---------------------------------------------------------------------------

export const projectsApi = {
  list: () => request<ProjectOut[]>("/projects"),
  get: (projectId: string) => request<ProjectOut>(`/projects/${projectId}`),
  create: (payload: ProjectCreate) => request<ProjectOut>("/projects", { method: "POST", body: payload }),
  update: (projectId: string, payload: ProjectUpdate) =>
    request<ProjectOut>(`/projects/${projectId}`, { method: "PATCH", body: payload }),
  remove: (projectId: string) => request<void>(`/projects/${projectId}`, { method: "DELETE" }),
  stats: (projectId: string) => request<ProjectStats>(`/projects/${projectId}/stats`),
};

// ---------------------------------------------------------------------------
// credentials
// ---------------------------------------------------------------------------

export const credentialsApi = {
  list: (projectId: string) => request<CredentialOut[]>(`/projects/${projectId}/credentials`),
  create: (projectId: string, payload: CredentialCreate) =>
    request<CredentialOut>(`/projects/${projectId}/credentials`, { method: "POST", body: payload }),
  remove: (projectId: string, credentialId: string) =>
    request<void>(`/projects/${projectId}/credentials/${credentialId}`, { method: "DELETE" }),
};

// ---------------------------------------------------------------------------
// knowledge
// ---------------------------------------------------------------------------

export const knowledgeApi = {
  list: (projectId: string) => request<KnowledgeSourceOut[]>(`/projects/${projectId}/knowledge`),
  upload: (projectId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<KnowledgeSourceOut>(`/projects/${projectId}/knowledge/upload`, {
      method: "POST",
      body: form,
      isForm: true,
    });
  },
  remove: (projectId: string, sourceId: string) =>
    request<void>(`/projects/${projectId}/knowledge/${sourceId}`, { method: "DELETE" }),
  search: (projectId: string, payload: SemanticSearchRequest) =>
    request<SemanticSearchResult[]>(`/projects/${projectId}/knowledge/search`, { method: "POST", body: payload }),
};

// ---------------------------------------------------------------------------
// requirements
// ---------------------------------------------------------------------------

export const requirementsApi = {
  list: (projectId: string) => request<RequirementOut[]>(`/projects/${projectId}/requirements`),
  get: (projectId: string, requirementId: string) =>
    request<RequirementOut>(`/projects/${projectId}/requirements/${requirementId}`),
  create: (projectId: string, payload: RequirementCreate) =>
    request<RequirementOut>(`/projects/${projectId}/requirements`, { method: "POST", body: payload }),
  update: (projectId: string, requirementId: string, payload: RequirementUpdate) =>
    request<RequirementOut>(`/projects/${projectId}/requirements/${requirementId}`, {
      method: "PATCH",
      body: payload,
    }),
  analyze: (projectId: string, requirementId: string) =>
    request<RequirementAnalysis>(`/projects/${projectId}/requirements/${requirementId}/analyze`, {
      method: "POST",
    }),
};

// ---------------------------------------------------------------------------
// runs
// ---------------------------------------------------------------------------

export const runsApi = {
  list: (projectId: string) => request<RunOut[]>(`/projects/${projectId}/runs`),
  get: (projectId: string, runId: string) => request<RunOut>(`/projects/${projectId}/runs/${runId}`),
  create: (projectId: string, payload: RunCreate) =>
    request<RunOut>(`/projects/${projectId}/runs`, { method: "POST", body: payload }),
  cancel: (projectId: string, runId: string) =>
    request<RunOut>(`/projects/${projectId}/runs/${runId}/cancel`, { method: "POST" }),
  evidenceUrl: (projectId: string, runId: string, evidenceId: string) =>
    request<{ url: string }>(`/projects/${projectId}/runs/${runId}/evidence/${evidenceId}/url`),
};

// ---------------------------------------------------------------------------
// reports
// ---------------------------------------------------------------------------

export const reportsApi = {
  list: (projectId: string, runId: string) => request<ReportOut[]>(`/projects/${projectId}/runs/${runId}/reports`),
  generate: (projectId: string, runId: string, payload: ReportGenerateRequest) =>
    request<ReportOut[]>(`/projects/${projectId}/runs/${runId}/reports`, { method: "POST", body: payload }),
  url: (projectId: string, runId: string, reportId: string) =>
    request<{ url: string }>(`/projects/${projectId}/runs/${runId}/reports/${reportId}/url`),
};

// ---------------------------------------------------------------------------
// chat
// ---------------------------------------------------------------------------

export const chatApi = {
  send: (payload: ChatMessageRequest) => request<ChatMessageResponse>("/chat/message", { method: "POST", body: payload }),
};
