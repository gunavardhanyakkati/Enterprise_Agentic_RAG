"""Gemini-powered enterprise document intelligence agents."""

import logging
from typing import Any, Optional

from src.schemas.agents.intelligence import (
    DOCUMENT_CATEGORIES,
    ClassificationResult,
    ComplianceReport,
    QuestionAnswerResult,
    SummarizationResult,
)
from src.services.gemini.client import GeminiClient

logger = logging.getLogger(__name__)

METADATA_FIELDS: dict[str, list[str]] = {
    "Employment Contract": ["employee_name", "salary", "duration", "notice_period", "department"],
    "Invoice": ["invoice_number", "vendor", "amount", "date"],
    "Resume": ["candidate_name", "email", "phone", "skills", "experience_years"],
    "Email": ["sender", "receiver", "subject", "date"],
    "HR Policy": ["policy_name", "department", "effective_date"],
    "Technical Document": ["product_name", "version", "author", "topic"],
    "Legal Agreement": ["parties", "effective_date", "jurisdiction", "term_length"],
    "Purchase Order": ["po_number", "vendor", "amount", "delivery_date"],
    "Employee Handbook": ["company_name", "effective_date", "version"],
    "Compliance Document": ["regulation", "scope", "effective_date", "owner"],
}

COMPLIANCE_RULES: dict[str, list[str]] = {
    "Employment Contract": [
        "salary clause",
        "termination clause",
        "confidentiality clause",
        "notice period",
        "duration",
    ],
    "Legal Agreement": ["parties", "termination", "confidentiality", "governing law"],
    "HR Policy": ["scope", "effective date", "acknowledgment"],
    "Compliance Document": ["requirements", "scope", "review date"],
}


class ClassificationAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def run(self, title: str, content: str) -> tuple[ClassificationResult, int]:
        categories = "\n".join(f"- {c}" for c in DOCUMENT_CATEGORIES)
        prompt = f"""You are an enterprise document classifier.

Classify the document into exactly ONE category from this list:
{categories}

Document title: {title}

Document content:
{content}

Return JSON matching this structure:
{{
  "document_type": "<category from list>",
  "confidence": <0.0-1.0>,
  "reasoning": [
     "detected element A (e.g., contains salary clauses)",
     "detected element B (e.g., contains employee identifiers)",
     ...
  ],
  "confidence_reasoning": {{
     "document_structure": <0.0-1.0 estimate of how typical this structure is for the category>,
     "keyword_match": <0.0-1.0 estimate based on keyword density>,
     "semantic_similarity": <0.0-1.0 estimate of thematic similarity>,
     "llm_consistency": <0.0-1.0 confidence of prompt validation>
  }}
}}"""
        data, tokens = await self.gemini.generate_json(prompt)
        return ClassificationResult.model_validate(data), tokens


class MetadataAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def run(
        self, document_type: str, title: str, content: str
    ) -> tuple[dict[str, Any], int]:
        fields = METADATA_FIELDS.get(document_type, ["title", "author", "date", "summary"])
        field_list = ", ".join(fields)
        prompt = f"""Extract structured metadata from this {document_type}.
For each metadata field, you MUST return a JSON object with:
- "value": The extracted metadata value (or null if not found)
- "confidence": A confidence score between 0.0 and 1.0
- "source": A brief snippet or section name showing where it was found in the document (or null)

Required fields: {field_list}

Document title: {title}

Document content:
{content}

Return a JSON object where the keys are the required fields, and the values are objects matching this format:
{{
  "<field_name>": {{
     "value": "extracted value",
     "confidence": 0.92,
     "source": "Section 3.2"
  }}
}}"""
        data, tokens = await self.gemini.generate_json(prompt)
        return data, tokens


class ComplianceAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def run(
        self, document_type: str, title: str, content: str
    ) -> tuple[ComplianceReport, int]:
        rules = COMPLIANCE_RULES.get(document_type, ["purpose", "scope", "responsibilities"])
        rules_text = "\n".join(f"- {r}" for r in rules)
        prompt = f"""You are an enterprise compliance analyst reviewing a {document_type}.

Required clauses to verify:
{rules_text}

Document title: {title}

Document content:
{content}

For each required clause return present/missing/partial with evidence snippet.
Compute risk_score 0-100 (100 = fully compliant).

Also generate a list of explanation reasons explaining why the risk score is what it is (e.g. what clauses are missing, what phrasing is ambiguous).

Return JSON:
{{
  "document_type": "{document_type}",
  "checks": [{{"clause": "...", "status": "present|missing|partial", "evidence": "..."}}],
  "risk_score": <0-100>,
  "summary": "<brief compliance summary>",
  "recommendations": ["..."],
  "reasoning": [
     "reason 1 (e.g. missing termination clause)",
     "reason 2",
     ...
  ]
}}"""
        data, tokens = await self.gemini.generate_json(prompt)
        return ComplianceReport.model_validate(data), tokens


class SummarizationAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def run(self, document_type: str, title: str, content: str) -> tuple[SummarizationResult, int]:
        prompt = f"""Write a concise executive summary (3-5 sentences) for this {document_type}.

Title: {title}

Content:
{content}

Return JSON: {{"executive_summary": "..."}}"""
        data, tokens = await self.gemini.generate_json(prompt)
        return SummarizationResult.model_validate(data), tokens


class QuestionAnsweringAgent:
    def __init__(self, gemini: GeminiClient):
        self.gemini = gemini

    async def run(
        self,
        query: str,
        context_chunks: list[dict[str, Any]],
        document_type: Optional[str] = None,
    ) -> tuple[QuestionAnswerResult, int]:
        context = "\n\n---\n\n".join(
            f"[Source: {c.get('title', 'Unknown')} | Score: {c.get('score', 0):.2f}]\n{c.get('chunk_text', '')}"
            for c in context_chunks
        ) or "No context retrieved."
        prompt = f"""Answer the question using ONLY the provided document excerpts.
If the answer is not in the context, say you cannot find it in the documents.

Document type: {document_type or 'Unknown'}

Context:
{context}

Question: {query}

Return JSON:
{{
  "answer": "...",
  "confidence": <0.0-1.0>
}}"""
        data, tokens = await self.gemini.generate_json(prompt)
        sources = [
            {
                "document_id": c.get("document_id", ""),
                "title": c.get("title", ""),
                "chunk_id": c.get("chunk_id", ""),
                "section": c.get("section_name", ""),
                "score": c.get("score", 0.0),
            }
            for c in context_chunks
        ]
        return QuestionAnswerResult(answer=data["answer"], confidence=data.get("confidence", 0.0), sources=sources), tokens


def json_keys(fields: list[str]) -> str:
    return ", ".join(f'"{f}": "..."' for f in fields)
