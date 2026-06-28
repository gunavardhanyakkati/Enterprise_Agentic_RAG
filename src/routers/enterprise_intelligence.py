import logging
from io import BytesIO
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import StreamingResponse

from src.services.security.auth_service import AuthService
from src.repositories.user import UserRepository
from src.dependencies import OpenSearchDep, SessionDep, UserDep
from src.repositories.document import DocumentRepository
from src.schemas.agents.intelligence import (
    AgentRunRequest,
    AgentRunResponse,
    ChatRequest,
    ClassificationResult,
    ComplianceReport,
    DocumentIdRequest,
    QuestionAnswerResult,
    WorkflowDefinitionSchema,
    WorkflowEdgeSchema,
    WorkflowNodeSchema,
)
from src.services.agents.enterprise.service import EnterpriseIntelligenceService
from src.services.agents.enterprise.workflow import WORKFLOW_EDGES, WORKFLOW_NODES
from src.services.security.access_control_service import AccessControlService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["enterprise-intelligence"])


def _get_document(session: SessionDep, document_id: str, user: UserDep):
    repository = DocumentRepository(session)
    document = repository.get_by_document_id(document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    access = AccessControlService()
    if not access.can_access_document(user, document):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return document


@router.get("/agents/workflow", response_model=WorkflowDefinitionSchema)
async def get_agent_workflow():
    """Return LangGraph enterprise workflow structure for visualization."""
    return WorkflowDefinitionSchema(
        nodes=[WorkflowNodeSchema.model_validate(node) for node in WORKFLOW_NODES],
        edges=[WorkflowEdgeSchema.model_validate(edge) for edge in WORKFLOW_EDGES],
    )


@router.post("/agents/run", response_model=AgentRunResponse)
async def run_agent_pipeline(
    request: AgentRunRequest,
    user: UserDep,
    session: SessionDep,
    opensearch: OpenSearchDep,
):
    """Run full enterprise intelligence pipeline on a document."""
    document = _get_document(session, request.document_id, user)
    service = EnterpriseIntelligenceService(session=session, opensearch=opensearch)
    try:
        return await service.run_pipeline(document, question=request.question, opensearch=opensearch)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.post("/classify", response_model=ClassificationResult)
async def classify_document(request: DocumentIdRequest, user: UserDep, session: SessionDep):
    document = _get_document(session, request.document_id, user)
    service = EnterpriseIntelligenceService(session=session)
    try:
        return await service.classify_document(document)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.post("/metadata")
async def extract_metadata(request: DocumentIdRequest, user: UserDep, session: SessionDep):
    document = _get_document(session, request.document_id, user)
    service = EnterpriseIntelligenceService(session=session)
    try:
        return await service.extract_metadata(document)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.post("/compliance", response_model=ComplianceReport)
async def compliance_analysis(request: DocumentIdRequest, user: UserDep, session: SessionDep):
    document = _get_document(session, request.document_id, user)
    service = EnterpriseIntelligenceService(session=session)
    try:
        return await service.analyze_compliance(document)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.post("/summarize")
async def summarize_document(request: DocumentIdRequest, user: UserDep, session: SessionDep):
    document = _get_document(session, request.document_id, user)
    service = EnterpriseIntelligenceService(session=session)
    try:
        summary = await service.summarize_document(document)
        return {"document_id": document.document_id, "summary": summary}
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.post("/chat", response_model=QuestionAnswerResult)
async def chat_with_documents(
    request: ChatRequest,
    user: UserDep,
    session: SessionDep,
    opensearch: OpenSearchDep,
):
    """Answer a question using retrieved document chunks and Gemini."""
    document = None
    if request.document_id:
        document = _get_document(session, request.document_id, user)

    service = EnterpriseIntelligenceService(session=session, opensearch=opensearch)
    try:
        result, _tokens = await service.answer_question(
            document=document,
            query=request.query,
            opensearch=opensearch,
            top_k=request.top_k,
        )
        return result
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


from fastapi import Query
from fastapi.responses import StreamingResponse
from io import BytesIO
import json
from src.services.security.auth_service import AuthService
from src.repositories.user import UserRepository
from uuid import UUID


@router.get("/analytics/agents")
async def get_agent_analytics(
    user: UserDep,
    session: SessionDep,
):
    """Calculate and return corpus-wide agent execution analytics."""
    repository = DocumentRepository(session)
    documents = repository.get_all(limit=1000)
    
    total_runs = 0
    total_tokens = 0
    success_runs = 0
    total_latency_ms = 0
    confidence_values = []
    agent_specific_stats = {}
    
    for doc in documents:
        executions = doc.agent_executions or []
        for exec in executions:
            agent_name = exec.get("agent")
            if not agent_name:
                continue
                
            total_runs += 1
            latency = exec.get("execution_time_ms", 0)
            tokens = exec.get("tokens_used", 0) or 0
            status = exec.get("status", "success")
            conf = exec.get("confidence")
            
            total_latency_ms += latency
            total_tokens += tokens
            if status == "success":
                success_runs += 1
            if conf is not None:
                confidence_values.append(conf)
                
            if agent_name not in agent_specific_stats:
                agent_specific_stats[agent_name] = {
                    "runs": 0,
                    "total_ms": 0,
                    "total_tokens": 0,
                    "success_runs": 0,
                    "confidence_sum": 0.0,
                    "confidence_count": 0,
                }
                
            stats = agent_specific_stats[agent_name]
            stats["runs"] += 1
            stats["total_ms"] += latency
            stats["total_tokens"] += tokens
            if status == "success":
                stats["success_runs"] += 1
            if conf is not None:
                stats["confidence_sum"] += conf
                stats["confidence_count"] += 1

    # Blended token rate: $0.15 / 1,000 tokens ($0.00015 per token)
    estimated_cost = total_tokens * 0.00015
    avg_latency_ms = total_latency_ms / total_runs if total_runs else 0
    avg_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0.0
    overall_success_rate = success_runs / total_runs if total_runs else 1.0
    
    formatted_agent_stats = []
    for agent, stats in agent_specific_stats.items():
        formatted_agent_stats.append({
            "agent": agent,
            "runs": stats["runs"],
            "avg_latency_ms": int(stats["total_ms"] / stats["runs"]) if stats["runs"] else 0,
            "total_tokens": stats["total_tokens"],
            "avg_confidence": stats["confidence_sum"] / stats["confidence_count"] if stats["confidence_count"] else None,
            "success_rate": stats["success_runs"] / stats["runs"] if stats["runs"] else 1.0,
        })
        
    from datetime import datetime, timedelta
    timeline = []
    today = datetime.now()
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        day_docs = [d for d in documents if d.created_at.strftime("%Y-%m-%d") == day_str]
        day_tokens = sum(sum(e.get("tokens_used", 0) or 0 for e in (d.agent_executions or [])) for d in day_docs)
        day_latency = sum(sum(e.get("execution_time_ms", 0) for e in (d.agent_executions or [])) for d in day_docs)
        timeline.append({
            "date": day_str,
            "tokens": day_tokens,
            "latency": int(day_latency / len(day_docs)) if day_docs and day_latency else 0,
            "documents_processed": len(day_docs)
        })

    return {
        "total_runs": total_runs,
        "total_tokens": total_tokens,
        "estimated_cost": round(estimated_cost, 4),
        "average_latency_ms": int(avg_latency_ms),
        "average_confidence": round(avg_confidence, 4),
        "success_rate": round(overall_success_rate, 4),
        "agent_performance": formatted_agent_stats,
        "timeline": timeline,
    }


@router.post("/documents/{document_id}/executive-report")
async def generate_executive_report(
    document_id: str,
    user: UserDep,
    session: SessionDep,
):
    """Generate and return an executive intelligence report cached in Redis."""
    document = _get_document(session, document_id, user)
    service = EnterpriseIntelligenceService(session=session)
    try:
        return await service.generate_executive_report(document)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate executive report: {str(exc)}")


@router.get("/documents/{document_id}/executive-report/pdf")
async def export_executive_report_pdf(
    document_id: str,
    session: SessionDep,
    token: Optional[str] = Query(None),
):
    """Generate a premium formatted PDF for the executive report."""
    user = None
    if token:
        try:
            auth_service = AuthService()
            token_payload = auth_service.verify_token(token)
            if token_payload:
                user_repo = UserRepository(session)
                user = user_repo.get_by_id(UUID(token_payload.sub))
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")
            
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
        
    document = _get_document(session, document_id, user)
    service = EnterpriseIntelligenceService(session=session)
    
    try:
        report_data = await service.generate_executive_report(document)
        pdf_buffer = build_executive_pdf(report_data)
        
        filename = f"executive_report_{document.title.replace(' ', '_').lower()}.pdf"
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to build PDF: {str(exc)}")


def build_executive_pdf(report_data: dict) -> BytesIO:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=15
    )
    
    section_style = ParagraphStyle(
        'DocSection',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#1e40af'),
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155')
    )
    
    bullet_style = ParagraphStyle(
        'DocBullet',
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )
    
    story.append(Paragraph("EXECUTIVE DOCUMENT REPORT", title_style))
    story.append(Spacer(1, 10))
    
    metadata_data = [
        [Paragraph(f"<b>Document:</b> {report_data.get('document_name')}", body_style),
         Paragraph(f"<b>Classification:</b> {report_data.get('document_type')}", body_style)],
        [Paragraph(f"<b>Classification Confidence:</b> {int((report_data.get('confidence') or 0) * 100)}%", body_style),
         Paragraph(f"<b>Compliance Score:</b> {report_data.get('compliance_score')}/100", body_style)]
    ]
    t = Table(metadata_data, colWidths=[250, 250])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('PADDING', (0,0), (-1,-1), 10),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#f1f5f9')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("Executive Summary", section_style))
    story.append(Paragraph(report_data.get('summary', 'No summary available.'), body_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("Key Risks & Exposure", section_style))
    for risk in report_data.get('risks', []):
        story.append(Paragraph(f"• {risk}", bullet_style))
    if not report_data.get('risks'):
        story.append(Paragraph("No significant risks identified.", body_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("Significant Clauses & Provisions", section_style))
    for clause in report_data.get('key_clauses', []):
        story.append(Paragraph(f"• {clause}", bullet_style))
    if not report_data.get('key_clauses'):
        story.append(Paragraph("No key clauses extracted.", body_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("AI Business Insights", section_style))
    for insight in report_data.get('ai_insights', []):
        story.append(Paragraph(f"• {insight}", bullet_style))
    if not report_data.get('ai_insights'):
        story.append(Paragraph("No insights generated.", body_style))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph("Recommendations", section_style))
    for rec in report_data.get('recommendations', []):
        story.append(Paragraph(f"• {rec}", bullet_style))
    if not report_data.get('recommendations'):
        story.append(Paragraph("No recommendations provided.", body_style))
        
    doc.build(story)
    buffer.seek(0)
    return buffer
