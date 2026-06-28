"""LangGraph workflow for enterprise document intelligence."""

from typing import TYPE_CHECKING, Any, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

if TYPE_CHECKING:
    from src.services.agents.enterprise.service import EnterpriseIntelligenceService


class EnterpriseIntelligenceState(TypedDict, total=False):
    document_id: str
    title: str
    raw_text: str
    document_type: str
    classification: dict[str, Any]
    extracted_metadata: dict[str, Any]
    retrieved_chunks: list[dict[str, Any]]
    compliance_report: dict[str, Any]
    summary: str
    agent_executions: list[dict[str, Any]]
    error: Optional[str]
    trace_id: Optional[str]


WORKFLOW_NODES = [
    {
        "id": "classify",
        "label": "Classification",
        "agent": "ClassificationAgent",
        "description": "Determines enterprise document category with confidence score.",
    },
    {
        "id": "metadata",
        "label": "Metadata",
        "agent": "MetadataAgent",
        "description": "Extracts structured fields based on document type.",
    },
    {
        "id": "retrieve",
        "label": "Retrieval",
        "agent": "RetrieverAgent",
        "description": "Hybrid semantic search over indexed document chunks.",
    },
    {
        "id": "compliance",
        "label": "Compliance",
        "agent": "ComplianceAgent",
        "description": "Checks required clauses and computes risk score.",
    },
    {
        "id": "summarize",
        "label": "Summary",
        "agent": "SummarizationAgent",
        "description": "Generates executive summary for stakeholders.",
    },
    {
        "id": "qa",
        "label": "Question Answering",
        "agent": "QuestionAnsweringAgent",
        "description": "RAG-based Q&A with citations (on-demand via chat or agents/run).",
        "on_demand": True,
    },
]

WORKFLOW_EDGES = [
    {"source": "classify", "target": "metadata"},
    {"source": "metadata", "target": "retrieve"},
    {"source": "retrieve", "target": "compliance"},
    {"source": "compliance", "target": "summarize"},
    {"source": "summarize", "target": "qa"},
]


def build_enterprise_intelligence_graph(service: "EnterpriseIntelligenceService"):
    graph = StateGraph(EnterpriseIntelligenceState)

    async def classify_node(state: EnterpriseIntelligenceState) -> dict[str, Any]:
        return await service._node_classify(state)

    async def metadata_node(state: EnterpriseIntelligenceState) -> dict[str, Any]:
        return await service._node_metadata(state)

    async def retrieve_node(state: EnterpriseIntelligenceState) -> dict[str, Any]:
        return await service._node_retrieve(state)

    async def compliance_node(state: EnterpriseIntelligenceState) -> dict[str, Any]:
        return await service._node_compliance(state)

    async def summarize_node(state: EnterpriseIntelligenceState) -> dict[str, Any]:
        return await service._node_summarize(state)

    graph.add_node("classify", classify_node)
    graph.add_node("metadata", metadata_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("compliance", compliance_node)
    graph.add_node("summarize", summarize_node)

    graph.add_edge(START, "classify")
    graph.add_edge("classify", "metadata")
    graph.add_edge("metadata", "retrieve")
    graph.add_edge("retrieve", "compliance")
    graph.add_edge("compliance", "summarize")
    graph.add_edge("summarize", END)

    return graph.compile()
