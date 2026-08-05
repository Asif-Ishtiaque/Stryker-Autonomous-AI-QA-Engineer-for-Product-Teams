// Mirrors backend/app/domain/enums.py exactly (StrEnum values are the wire format).

export const Platform = {
  WEB: "web",
  REST_API: "rest_api",
  GRAPHQL: "graphql",
  MOBILE: "mobile",
  DESKTOP: "desktop",
} as const;
export type Platform = (typeof Platform)[keyof typeof Platform];

export const ProjectEnvironment = {
  PRODUCTION: "production",
  STAGING: "staging",
  QA: "qa",
  DEVELOPMENT: "development",
} as const;
export type ProjectEnvironment = (typeof ProjectEnvironment)[keyof typeof ProjectEnvironment];

export const ProjectStatus = {
  ACTIVE: "active",
  ARCHIVED: "archived",
  PAUSED: "paused",
} as const;
export type ProjectStatus = (typeof ProjectStatus)[keyof typeof ProjectStatus];

export const UserRole = {
  OWNER: "owner",
  ADMIN: "admin",
  MEMBER: "member",
  VIEWER: "viewer",
} as const;
export type UserRole = (typeof UserRole)[keyof typeof UserRole];

export const KnowledgeSourceType = {
  MARKDOWN: "markdown",
  PDF: "pdf",
  DOCX: "docx",
  TXT: "txt",
  CSV: "csv",
  IMAGE: "image",
  SWAGGER: "swagger",
  OPENAPI: "openapi",
  POSTMAN: "postman",
  SQL: "sql",
  SCREENSHOT: "screenshot",
  VIDEO: "video",
} as const;
export type KnowledgeSourceType = (typeof KnowledgeSourceType)[keyof typeof KnowledgeSourceType];

export const KnowledgeIndexStatus = {
  PENDING: "pending",
  PROCESSING: "processing",
  INDEXED: "indexed",
  FAILED: "failed",
} as const;
export type KnowledgeIndexStatus = (typeof KnowledgeIndexStatus)[keyof typeof KnowledgeIndexStatus];

export const RunStatus = {
  QUEUED: "queued",
  PLANNING: "planning",
  RUNNING: "running",
  RETRYING: "retrying",
  VALIDATING: "validating",
  PASSED: "passed",
  FAILED: "failed",
  ERRORED: "errored",
  CANCELLED: "cancelled",
} as const;
export type RunStatus = (typeof RunStatus)[keyof typeof RunStatus];

export const TERMINAL_RUN_STATUSES: RunStatus[] = [
  RunStatus.PASSED,
  RunStatus.FAILED,
  RunStatus.ERRORED,
  RunStatus.CANCELLED,
];

export const StepStatus = {
  WAITING: "waiting",
  RUNNING: "running",
  RETRYING: "retrying",
  PASSED: "passed",
  FAILED: "failed",
  SKIPPED: "skipped",
} as const;
export type StepStatus = (typeof StepStatus)[keyof typeof StepStatus];

export const Severity = {
  LOW: "low",
  MEDIUM: "medium",
  HIGH: "high",
  CRITICAL: "critical",
} as const;
export type Severity = (typeof Severity)[keyof typeof Severity];

export const EvidenceType = {
  SCREENSHOT: "screenshot",
  VIDEO: "video",
  CONSOLE_LOG: "console_log",
  NETWORK_LOG: "network_log",
  DOM_SNAPSHOT: "dom_snapshot",
  ACCESSIBILITY_TREE: "accessibility_tree",
  API_REQUEST: "api_request",
  API_RESPONSE: "api_response",
  TIMING: "timing",
} as const;
export type EvidenceType = (typeof EvidenceType)[keyof typeof EvidenceType];

export const ReportFormat = {
  MARKDOWN: "markdown",
  PDF: "pdf",
  JSON: "json",
  JIRA: "jira",
} as const;
export type ReportFormat = (typeof ReportFormat)[keyof typeof ReportFormat];

// ---------------------------------------------------------------------------
// auth.py
// ---------------------------------------------------------------------------

export interface RegisterRequest {
  email: string;
  name: string;
  password: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserOut {
  id: string;
  email: string;
  name: string;
  role: UserRole;
}

// ---------------------------------------------------------------------------
// project.py
// ---------------------------------------------------------------------------

export interface ProjectCreate {
  name: string;
  description?: string;
  platform: Platform;
  environment?: ProjectEnvironment;
  base_url: string;
  tags?: string[];
}

export interface ProjectUpdate {
  name?: string;
  description?: string;
  environment?: ProjectEnvironment;
  base_url?: string;
  tags?: string[];
  status?: ProjectStatus;
}

export interface ProjectOut {
  id: string;
  name: string;
  description: string;
  platform: Platform;
  environment: ProjectEnvironment;
  base_url: string;
  tags: string[];
  status: ProjectStatus;
}

export interface ProjectStats {
  requirement_count: number;
  run_count: number;
  pass_rate: number;
  average_duration_ms: number | null;
  open_bugs: number;
  average_confidence: number | null;
}

// ---------------------------------------------------------------------------
// credential.py
// ---------------------------------------------------------------------------

export interface CredentialCreate {
  label: string;
  username?: string | null;
  password?: string | null;
  api_token?: string | null;
  bearer_token?: string | null;
  cookies?: Record<string, string> | null;
  headers?: Record<string, string> | null;
  env_vars?: Record<string, string> | null;
}

export interface CredentialOut {
  id: string;
  project_id: string;
  label: string;
  has_username: boolean;
  has_password: boolean;
  has_api_token: boolean;
  has_bearer_token: boolean;
  has_cookies: boolean;
  has_headers: boolean;
}

// ---------------------------------------------------------------------------
// knowledge.py
// ---------------------------------------------------------------------------

export interface KnowledgeSourceOut {
  id: string;
  project_id: string;
  filename: string;
  source_type: KnowledgeSourceType;
  status: KnowledgeIndexStatus;
  chunk_count: number;
  error_message: string | null;
}

export interface SemanticSearchRequest {
  query: string;
  top_k?: number;
}

export interface SemanticSearchResult {
  source_filename: string;
  chunk_text: string;
  score: number;
  metadata: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// requirement.py
// ---------------------------------------------------------------------------

export interface RequirementCreate {
  text: string;
  credential_profile_id?: string | null;
}

export interface RequirementUpdate {
  credential_profile_id: string | null;
}

export interface RequirementAnalysis {
  understood_intent: string;
  expected_outcomes: string[];
  inferred_validations: string[];
  identified_risks: string[];
  predicted_edge_cases: string[];
  confidence: number;
}

export interface RequirementOut {
  id: string;
  project_id: string;
  text: string;
  credential_profile_id: string | null;
  ai_analysis: RequirementAnalysis | null;
}

// ---------------------------------------------------------------------------
// run.py
// ---------------------------------------------------------------------------

export interface RunCreate {
  requirement_id: string;
}

export interface EvidenceOut {
  id: string;
  evidence_type: EvidenceType;
  storage_key: string | null;
  inline_data: Record<string, unknown> | null;
  content_type: string | null;
}

export interface StepOut {
  id: string;
  sequence: number;
  name: string;
  action_type: string;
  parameters: Record<string, unknown>;
  status: StepStatus;
  retry_count: number;
  started_at: string | null;
  finished_at: string | null;
  result: Record<string, unknown> | null;
  error_message: string | null;
  evidence: EvidenceOut[];
}

export interface RunOut {
  id: string;
  project_id: string;
  requirement_id: string;
  status: RunStatus;
  plan: Record<string, unknown> | null;
  validation_checklist: Record<string, unknown> | null;
  confidence_score: number | null;
  severity: string | null;
  root_cause_hypothesis: string | null;
  error_message: string | null;
  report_markdown: string | null;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  steps: StepOut[];
}

/** Payload pushed over the run's WebSocket channel — see backend/app/schemas/run.py RunStepEvent. */
export interface RunStepEvent {
  run_id: string;
  step_id?: string | null;
  run_status: RunStatus;
  step_status?: StepStatus | null;
  sequence?: number | null;
  name?: string | null;
  message?: string | null;
  confidence_score?: number | null;
  /** Mission Control additions — see backend/app/execution/tasks.py on_event. */
  reasoning?: string | null;
  console?: { type: string; text: string } | null;
  network?: { url: string; method: string } | null;
  evidence?: { id: string; evidence_type: EvidenceType }[] | null;
}

// ---------------------------------------------------------------------------
// report.py
// ---------------------------------------------------------------------------

export interface ReportOut {
  id: string;
  run_id: string;
  format: ReportFormat;
  storage_key: string;
}

export interface ReportGenerateRequest {
  formats: ReportFormat[];
}

// ---------------------------------------------------------------------------
// chat.py
// ---------------------------------------------------------------------------

export interface ChatMessageRequest {
  project_id: string;
  message: string;
  conversation_id?: string | null;
}

export interface ChatSource {
  kind: "run" | "knowledge" | string;
  ref_id: string;
  snippet: string;
}

export interface ChatMessageResponse {
  conversation_id: string;
  answer: string;
  sources: ChatSource[];
}
