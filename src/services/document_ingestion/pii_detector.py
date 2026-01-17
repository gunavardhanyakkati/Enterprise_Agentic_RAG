"""
PII (Personally Identifiable Information) detection service.
Scans document content for sensitive data patterns for GDPR/CCPA compliance.
"""

import logging
import re
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)


class PIIDetectorService:
    """
    Detects personally identifiable information in document text.
    Uses pattern matching for common PII like emails, SSNs, credit cards.
    """
    
    def __init__(self, enabled: bool = True, confidence_threshold: float = 0.8):
        """
        Initialize PII detector.
        
        :param enabled: Whether PII detection is enabled
        :param confidence_threshold: Minimum confidence to flag as PII (0-1)
        """
        self.enabled = enabled
        self.confidence_threshold = confidence_threshold
        
        # Common PII patterns
        self.patterns = {
            "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
            "us_ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
            "credit_card": re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
            "phone_us": re.compile(r"\b(?:\+1\s*)?\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4}\b"),
            "ip_address": re.compile(r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"),
        }
        
        logger.info(f"PII detector initialized: {len(self.patterns)} patterns")
    
    async def scan_text(self, text: str) -> List[Tuple[str, str, int]]:
        """
        Scan text for PII patterns.
        
        :param text: Document text to scan
        :returns: List of (pattern_name, matched_text, position) tuples
        """
        if not self.enabled or not text:
            return []
        
        findings = []
        
        try:
            for pattern_name, pattern in self.patterns.items():
                for match in pattern.finditer(text):
                    findings.append((pattern_name, match.group(), match.start()))
            
            logger.debug(f"PII scan complete: {len(findings)} findings")
            return findings
            
        except Exception as e:
            logger.error(f"PII scan error: {e}")
            return []
    
    async def scan_file(self, file_path: Path) -> List[Tuple[str, str, int]]:
        """
        Scan file content for PII patterns.
        
        :param file_path: Path to the file to scan
        :returns: List of PII findings
        """
        if not self.enabled:
            logger.debug("PII detection disabled, skipping scan")
            return []
        
        try:
            # Read file as text (assuming text-based documents)
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            
            findings = await self.scan_text(content)
            
            if findings:
                logger.warning(
                    f"PII detected in {file_path}: {len(findings)} matches. "
                    f"Patterns: {set(p[0] for p in findings)}"
                )
            
            return findings
            
        except Exception as e:
            logger.error(f"Error reading file for PII scan {file_path}: {e}")
            return []
    
    def generate_report(self, findings: List[Tuple[str, str, int]]) -> dict:
        """
        Generate a compliance report from PII findings.
        
        :param findings: List of findings from scan_text/scan_file
        :returns: Summary report dictionary
        """
        pattern_counts = {}
        for pattern_name, _, _ in findings:
            pattern_counts[pattern_name] = pattern_counts.get(pattern_name, 0) + 1
        
        return {
            "total_findings": len(findings),
            "pattern_breakdown": pattern_counts,
            "risk_level": "high" if len(findings) > 10 else "medium" if len(findings) > 0 else "low",
            "recommendation": "Redact or encrypt document" if findings else "No action needed",
        }
