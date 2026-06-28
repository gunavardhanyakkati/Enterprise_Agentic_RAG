"""Enterprise document intelligence agent schemas."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

DOCUMENT_CATEGORIES = [
    "Employment Contract",
    "Invoice",
    "Resume",
    "Email",
    "HR Policy",
    "Technical Document",
    "Legal Agreement",
    "Purchase Order",
    "Employee Handbook",
    "Compliance Document",
]

DocumentCategory = Literal[
    "Employment Contract",
    "Invoice",
    "Resume",
    "Email",
    "HR Policy",
    "Technical Document",
    "Legal Agreement",
    "Purchase Order",
    "Employee Handbook",
    "Compliance Document",
]


class AgentExecutionRecord(BaseModel):
    agent: str
    execution_time_ms: int
    confidence: Optional[float] = None
    tokens_used: Optional[int] = None
    status: Literal["success", "error"] = "success"
    detail: Optional[str] = None
    timestamp: Optional[str] = None
    trace_id: Optional[str] = None


class ClassificationResult(BaseModel):
    document_type: DocumentCategory
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: List[str] = Field(default_factory=list)
    confidence_reasoning: Dict[str, float] = Field(default_factory=dict)


class ComplianceCheckItem(BaseModel):
    clause: str
    status: Literal["present", "missing", "partial"]
    evidence: str = ""


class ComplianceReport(BaseModel):
    document_type: str
    checks: List[ComplianceCheckItem]
    risk_score: int = Field(ge=0, le=100)
    summary: str = ""
    recommendations: List[str] = Field(default_factory=list)
    reasoning: List[str] = Field(default_factory=list)


class SummarizationResult(BaseModel):
    executive_summary: str


class QuestionAnswerResult(BaseModel):
    answer: str
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class AgentRunRequest(BaseModel):
    document_id: str
    question: Optional[str] = None


class AgentRunResponse(BaseModel):
    document_id: str
    document_type: str
    classification: Optional[ClassificationResult] = None
    extracted_metadata: Optional[Dict[str, Any]] = None
    compliance_report: Optional[ComplianceReport] = None
    summary: Optional[str] = None
    answer: Optional[QuestionAnswerResult] = None
    agent_executions: List[AgentExecutionRecord] = Field(default_factory=list)


class DocumentIdRequest(BaseModel):
    document_id: str


class ChatRequest(BaseModel):
    document_id: Optional[str] = None
    query: str
    top_k: int = Field(default=5, ge=1, le=20)


class WorkflowNodeSchema(BaseModel):
    id: str
    label: str
    agent: str
    description: str
    on_demand: bool = False


class WorkflowEdgeSchema(BaseModel):
    source: str
    target: str


class WorkflowDefinitionSchema(BaseModel):
    nodes: List[WorkflowNodeSchema]
    edges: List[WorkflowEdgeSchema]
