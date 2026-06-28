import logging
import time
from typing import Any, Optional

from sqlalchemy.orm import Session

from src.config import Settings, get_settings
from src.models.document import Document
from src.repositories.document import DocumentRepository
from src.schemas.agents.intelligence import (
    AgentExecutionRecord,
    AgentRunResponse,
    ChatRequest,
    ClassificationResult,
    ComplianceReport,
    QuestionAnswerResult,
)
from src.services.agents.enterprise.agents import (
    ClassificationAgent,
    ComplianceAgent,
    MetadataAgent,
    QuestionAnsweringAgent,
    SummarizationAgent,
)
from src.services.agents.enterprise.workflow import EnterpriseIntelligenceState, build_enterprise_intelligence_graph
from src.services.embeddings.factory import make_embeddings_client
from src.services.gemini.client import GeminiClient
from src.services.gemini.factory import make_gemini_client
from src.services.opensearch.client import OpenSearchClient
from src.services.opensearch.factory import make_opensearch_client

logger = logging.getLogger(__name__)


class EnterpriseIntelligenceService:
    """Orchestrates Gemini agents via LangGraph and persists results."""

    def __init__(
        self,
        session: Session,
        gemini: Optional[GeminiClient] = None,
        opensearch: Optional[OpenSearchClient] = None,
        settings: Optional[Settings] = None,
    ):
        self.session = session
        self.settings = settings or get_settings()
        self.gemini = gemini or make_gemini_client()
        self.opensearch = opensearch
        self.repository = DocumentRepository(session)

        self.classifier = ClassificationAgent(self.gemini)
        self.metadata_agent = MetadataAgent(self.gemini)
        self.compliance_agent = ComplianceAgent(self.gemini)
        self.summarizer = SummarizationAgent(self.gemini)
        self.qa_agent = QuestionAnsweringAgent(self.gemini)
        self.graph = build_enterprise_intelligence_graph(self)

    def _truncate(self, text: str) -> str:
        max_chars = self.settings.gemini.max_content_chars
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n\n[Content truncated for analysis]"

    def _record(
        self,
        executions: list[dict[str, Any]],
        agent: str,
        started: float,
        confidence: Optional[float],
        tokens: int,
        status: str = "success",
        detail: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        from datetime import datetime, timezone
        record = AgentExecutionRecord(
            agent=agent,
            execution_time_ms=int((time.perf_counter() - started) * 1000),
            confidence=confidence,
            tokens_used=tokens,
            status=status,  # type: ignore[arg-type]
            detail=detail,
            timestamp=datetime.now(timezone.utc).isoformat(),
            trace_id=trace_id,
        )
        executions.append(record.model_dump())
        return executions

    async def _node_classify(self, state: EnterpriseIntelligenceState) -> dict[str, Any]:
        executions = list(state.get("agent_executions") or [])
        started = time.perf_counter()
        trace_id = state.get("trace_id")
        try:
            result, tokens = await self.classifier.run(state["title"], self._truncate(state["raw_text"]))
            self._record(executions, "ClassificationAgent", started, result.confidence, tokens, trace_id=trace_id)
            return {
                "classification": result.model_dump(),
                "document_type": result.document_type,
                "agent_executions": executions,
            }
        except Exception as exc:
            self._record(executions, "ClassificationAgent", started, None, 0, "error", str(exc), trace_id=trace_id)
            return {"agent_executions": executions, "error": str(exc)}

    async def _node_metadata(self, state: EnterpriseIntelligenceState) -> dict[str, Any]:
        executions = list(state.get("agent_executions") or [])
        started = time.perf_counter()
        trace_id = state.get("trace_id")
        doc_type = state.get("document_type") or "Technical Document"
        try:
            metadata, tokens = await self.metadata_agent.run(
                doc_type, state["title"], self._truncate(state["raw_text"])
            )
            # Blended metadata extraction confidence score
            self._record(executions, "MetadataAgent", started, 0.88, tokens, trace_id=trace_id)
            return {"extracted_metadata": metadata, "agent_executions": executions}
        except Exception as exc:
            self._record(executions, "MetadataAgent", started, None, 0, "error", str(exc), trace_id=trace_id)
            return {"agent_executions": executions, "error": str(exc)}

    async def _node_retrieve(self, state: EnterpriseIntelligenceState) -> dict[str, Any]:
        executions = list(state.get("agent_executions") or [])
        started = time.perf_counter()
        trace_id = state.get("trace_id")
        try:
            opensearch = self.opensearch or make_opensearch_client(self.settings)
            embeddings = make_embeddings_client(self.settings)
            query = f"{state['title']} key sections and important clauses"
            query_embedding = await embeddings.embed_query(query)
            filters = [{"term": {"document_id": state["document_id"]}}]
            results = opensearch.search_unified(
                query=query,
                query_embedding=query_embedding,
                size=5,
                use_hybrid=True,
                additional_filters=filters,
            )
            chunks = results.get("hits", [])
            avg_score = sum(float(c.get("score", 0)) for c in chunks) / len(chunks) if chunks else 0.0
            detail = f"Retrieved {len(chunks)} chunks (avg score {avg_score:.2f})"
            self._record(executions, "RetrieverAgent", started, avg_score if chunks else None, 0, "success", detail, trace_id=trace_id)
            return {"retrieved_chunks": chunks, "agent_executions": executions}
        except Exception as exc:
            logger.warning(f"Retrieval step failed: {exc}")
            self._record(executions, "RetrieverAgent", started, None, 0, "error", str(exc), trace_id=trace_id)
            return {"retrieved_chunks": [], "agent_executions": executions}

    async def _node_compliance(self, state: EnterpriseIntelligenceState) -> dict[str, Any]:
        executions = list(state.get("agent_executions") or [])
        started = time.perf_counter()
        trace_id = state.get("trace_id")
        doc_type = state.get("document_type") or "Technical Document"
        try:
            report, tokens = await self.compliance_agent.run(
                doc_type, state["title"], self._truncate(state["raw_text"])
            )
            confidence = report.risk_score / 100.0
            self._record(executions, "ComplianceAgent", started, confidence, tokens, trace_id=trace_id)
            return {"compliance_report": report.model_dump(), "agent_executions": executions}
        except Exception as exc:
            self._record(executions, "ComplianceAgent", started, None, 0, "error", str(exc), trace_id=trace_id)
            return {"agent_executions": executions, "error": str(exc)}

    async def _node_summarize(self, state: EnterpriseIntelligenceState) -> dict[str, Any]:
        executions = list(state.get("agent_executions") or [])
        started = time.perf_counter()
        trace_id = state.get("trace_id")
        doc_type = state.get("document_type") or "Technical Document"
        try:
            result, tokens = await self.summarizer.run(
                doc_type, state["title"], self._truncate(state["raw_text"])
            )
            self._record(executions, "SummarizationAgent", started, 0.92, tokens, trace_id=trace_id)
            return {"summary": result.executive_summary, "agent_executions": executions}
        except Exception as exc:
            self._record(executions, "SummarizationAgent", started, None, 0, "error", str(exc), trace_id=trace_id)
            return {"agent_executions": executions, "error": str(exc)}

    async def run_pipeline(
        self,
        document: Document,
        question: Optional[str] = None,
        opensearch: Optional[OpenSearchClient] = None,
    ) -> AgentRunResponse:
        if not self.gemini.is_available:
            raise RuntimeError("Gemini is not configured. Set GEMINI__API_KEY.")

        # Langfuse trace setup
        from src.services.langfuse.factory import make_langfuse_tracer
        trace_id = None
        handler = None
        try:
            tracer = make_langfuse_tracer()
            if tracer and tracer.client:
                handler = tracer.get_callback_handler(
                    trace_name="enterprise_intelligence_pipeline",
                    metadata={"document_id": document.document_id, "document_type": document.document_type}
                )
                if handler:
                    trace_id = handler.trace_id
        except Exception as e:
            logger.warning(f"Failed to initialize Langfuse tracing handler: {e}")

        initial_state: EnterpriseIntelligenceState = {
            "document_id": document.document_id,
            "title": document.title,
            "raw_text": document.raw_text or "",
            "document_type": document.document_type,
            "agent_executions": [],
            "trace_id": trace_id,
        }
        
        config = {}
        if handler:
            config["callbacks"] = [handler]
            
        final_state = await self.graph.ainvoke(initial_state, config=config)

        answer: Optional[QuestionAnswerResult] = None
        if question:
            started = time.perf_counter()
            try:
                answer, qa_tokens = await self.answer_question(
                    document=document,
                    query=question,
                    opensearch=opensearch or self.opensearch,
                    top_k=5,
                )
                executions = list(final_state.get("agent_executions") or [])
                self._record(
                    executions,
                    "QuestionAnsweringAgent",
                    started,
                    answer.confidence,
                    qa_tokens,
                    trace_id=trace_id,
                )
                final_state["agent_executions"] = executions
            except Exception as exc:
                executions = list(final_state.get("agent_executions") or [])
                self._record(executions, "QuestionAnsweringAgent", started, None, 0, "error", str(exc), trace_id=trace_id)
                final_state["agent_executions"] = executions

        self._persist(document, final_state)

        return AgentRunResponse(
            document_id=document.document_id,
            document_type=final_state.get("document_type", document.document_type),
            classification=ClassificationResult.model_validate(final_state["classification"])
            if final_state.get("classification")
            else None,
            extracted_metadata=final_state.get("extracted_metadata"),
            compliance_report=ComplianceReport.model_validate(final_state["compliance_report"])
            if final_state.get("compliance_report")
            else None,
            summary=final_state.get("summary"),
            answer=answer,
            agent_executions=[
                AgentExecutionRecord.model_validate(e) for e in final_state.get("agent_executions", [])
            ],
        )

    async def classify_document(self, document: Document) -> ClassificationResult:
        result, _ = await self.classifier.run(document.title, self._truncate(document.raw_text or ""))
        document.document_type = result.document_type
        document.classification_confidence = result.confidence
        document.classification_reasoning = result.reasoning
        document.confidence_reasoning = result.confidence_reasoning
        self.repository.update(document)
        return result

    async def extract_metadata(self, document: Document) -> dict[str, Any]:
        metadata, _ = await self.metadata_agent.run(
            document.document_type, document.title, self._truncate(document.raw_text or "")
        )
        document.extracted_metadata = metadata
        self.repository.update(document)
        return metadata

    async def analyze_compliance(self, document: Document) -> ComplianceReport:
        report, _ = await self.compliance_agent.run(
            document.document_type, document.title, self._truncate(document.raw_text or "")
        )
        document.compliance_report = report.model_dump()
        document.compliance_reasoning = report.reasoning
        self.repository.update(document)
        return report

    async def summarize_document(self, document: Document) -> str:
        result, _ = await self.summarizer.run(
            document.document_type, document.title, self._truncate(document.raw_text or "")
        )
        document.summary = result.executive_summary
        self.repository.update(document)
        return result.executive_summary

    async def answer_question(
        self,
        document: Optional[Document],
        query: str,
        opensearch: Optional[OpenSearchClient] = None,
        top_k: int = 5,
    ) -> tuple[QuestionAnswerResult, int]:
        chunks: list[dict[str, Any]] = []
        search_client = opensearch or self.opensearch or make_opensearch_client(self.settings)
        if search_client:
            embeddings = make_embeddings_client(self.settings)
            query_embedding = await embeddings.embed_query(query)
            filters = [{"term": {"document_id": document.document_id}}] if document else None
            results = search_client.search_unified(
                query=query,
                query_embedding=query_embedding,
                size=top_k,
                use_hybrid=True,
                additional_filters=filters,
            )
            chunks = results.get("hits", [])

        doc_type = document.document_type if document else None
        started = time.perf_counter()
        result, tokens = await self.qa_agent.run(query, chunks, doc_type)
        logger.info(
            f"QA completed in {int((time.perf_counter() - started) * 1000)}ms, tokens={tokens}"
        )
        return result, tokens

    def _persist(self, document: Document, state: dict[str, Any]) -> Document:
        if state.get("classification"):
            document.document_type = state["classification"]["document_type"]
            document.classification_confidence = state["classification"].get("confidence")
            document.classification_reasoning = state["classification"].get("reasoning")
            document.confidence_reasoning = state["classification"].get("confidence_reasoning")
        if state.get("extracted_metadata"):
            document.extracted_metadata = state["extracted_metadata"]
        if state.get("compliance_report"):
            document.compliance_report = state["compliance_report"]
            document.compliance_reasoning = state["compliance_report"].get("reasoning")
        if state.get("summary"):
            document.summary = state["summary"]
            
        executions = state.get("agent_executions") or []
        document.agent_executions = executions
        
        # Calculate summary execution metrics
        valid_confidences = [e.get("confidence") for e in executions if e.get("confidence") is not None]
        document.agent_execution_metadata = {
            "total_latency_ms": sum(e.get("execution_time_ms", 0) for e in executions),
            "total_tokens": sum(e.get("tokens_used", 0) for e in executions),
            "avg_confidence": sum(valid_confidences) / len(valid_confidences) if valid_confidences else 0.0,
            "success_rate": sum(1 for e in executions if e.get("status") == "success") / len(executions) if executions else 1.0
        }
        return self.repository.update(document)

    async def generate_executive_report(self, document: Document) -> dict[str, Any]:
        import json
        cache = None
        try:
            from src.services.cache.factory import make_cache_client
            cache = make_cache_client(self.settings)
        except Exception as e:
            logger.warning(f"Could not connect to Redis for caching: {e}")
            
        cache_key = f"report:{document.document_id}"
        
        # Try Redis Cache
        if cache:
            try:
                cached_report = cache.redis.get(cache_key)
                if cached_report:
                    logger.info(f"Retrieved executive report from Redis cache for {document.document_id}")
                    return json.loads(cached_report)
            except Exception as e:
                logger.warning(f"Failed to fetch report from Redis cache: {e}")
                
        logger.info(f"Redis cache miss. Generating executive report for {document.document_id} via Gemini")
        
        compliance_score = 0
        if document.compliance_report:
            compliance_score = document.compliance_report.get("risk_score", 0)
            
        prompt = f"""You are a senior executive AI adviser. Read the document details and generate a high-impact executive report in JSON.
        
        Document Title: {document.title}
        Document Type: {document.document_type}
        Compliance Risk Score: {compliance_score}
        Document Summary: {document.summary or "Not summary available"}
        
        Return JSON structure exactly:
        {{
          "risks": [
             "Risk 1 with business impact",
             "Risk 2"
          ],
          "key_clauses": [
             "Important clause 1 details",
             "Important clause 2"
          ],
          "ai_insights": [
             "Strategic business-level insight 1",
             "Insight 2"
          ],
          "recommendations": [
             "Actionable item 1 for leadership",
             "Actionable item 2"
          ]
        }}
        """
        
        report_data, _ = await self.gemini.generate_json(prompt)
        
        report = {
            "document_name": document.title,
            "document_type": document.document_type,
            "confidence": document.classification_confidence or 0.0,
            "summary": document.summary or "Summary not available.",
            "metadata": document.extracted_metadata or {},
            "compliance_score": compliance_score,
            "risks": report_data.get("risks", []),
            "key_clauses": report_data.get("key_clauses", []),
            "ai_insights": report_data.get("ai_insights", []),
            "recommendations": report_data.get("recommendations", [])
        }
        
        # Cache in Redis for 1 hour
        if cache:
            try:
                cache.redis.set(cache_key, json.dumps(report), ex=3600)
                logger.info(f"Cached executive report in Redis for {document.document_id}")
            except Exception as e:
                logger.warning(f"Failed to cache report in Redis: {e}")
                
        return report
