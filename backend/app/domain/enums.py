from __future__ import annotations

from enum import StrEnum


class Platform(StrEnum):
    WEB = "web"
    REST_API = "rest_api"
    GRAPHQL = "graphql"
    MOBILE = "mobile"
    DESKTOP = "desktop"


class ProjectEnvironment(StrEnum):
    PRODUCTION = "production"
    STAGING = "staging"
    QA = "qa"
    DEVELOPMENT = "development"


class ProjectStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    PAUSED = "paused"


class UserRole(StrEnum):
    """Platform-level role — who may operate Stryker itself."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class KnowledgeSourceType(StrEnum):
    MARKDOWN = "markdown"
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    CSV = "csv"
    IMAGE = "image"
    SWAGGER = "swagger"
    OPENAPI = "openapi"
    POSTMAN = "postman"
    SQL = "sql"
    SCREENSHOT = "screenshot"
    VIDEO = "video"


class KnowledgeIndexStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class RunStatus(StrEnum):
    QUEUED = "queued"
    PLANNING = "planning"
    RUNNING = "running"
    RETRYING = "retrying"
    VALIDATING = "validating"
    PASSED = "passed"
    FAILED = "failed"
    ERRORED = "errored"
    CANCELLED = "cancelled"


class StepStatus(StrEnum):
    WAITING = "waiting"
    RUNNING = "running"
    RETRYING = "retrying"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EvidenceType(StrEnum):
    SCREENSHOT = "screenshot"
    VIDEO = "video"
    CONSOLE_LOG = "console_log"
    NETWORK_LOG = "network_log"
    DOM_SNAPSHOT = "dom_snapshot"
    ACCESSIBILITY_TREE = "accessibility_tree"
    API_REQUEST = "api_request"
    API_RESPONSE = "api_response"
    TIMING = "timing"


class ReportFormat(StrEnum):
    MARKDOWN = "markdown"
    PDF = "pdf"
    JSON = "json"
    JIRA = "jira"
