import logging
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from langfuse import Langfuse
from src.config import Settings

logger = logging.getLogger(__name__)


class LangfuseTracer:
    """Wrapper for Langfuse v3 tracing client with enhanced audit logging capabilities."""

    def __init__(self, settings: Settings):
        self.settings = settings.langfuse
        self.client: Optional[Langfuse] = None

        if self.settings.enabled and self.settings.public_key and self.settings.secret_key:
            try:
                self.client = Langfuse(
                    public_key=self.settings.public_key,
                    secret_key=self.settings.secret_key,
                    host=self.settings.host,
                    flush_at=self.settings.flush_at,
                    flush_interval=self.settings.flush_interval,
                    debug=self.settings.debug,
                )
                logger.info(f"Langfuse v3 tracing initialized (host: {self.settings.host})")
            except Exception as e:
                logger.error(f"Failed to initialize Langfuse: {e}")
                self.client = None
        else:
            logger.info("Langfuse tracing disabled or missing credentials")

    def get_callback_handler(
        self,
        trace_name: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[list[str]] = None,
    ):
        """
        Get a CallbackHandler for LangChain/LangGraph integration.

        Args:
            trace_name: Optional name for the trace
            user_id: Optional user identifier
            session_id: Optional session identifier
            metadata: Additional metadata to attach to the trace
            tags: Optional tags for the trace

        Returns:
            CallbackHandler instance if Langfuse is enabled, None otherwise
        """
        if not self.client:
            return None

        try:
            from langfuse.langchain import CallbackHandler

            handler = CallbackHandler(
                trace_name=trace_name,
                user_id=user_id,
                session_id=session_id,
                metadata=metadata,
                tags=tags,
            )
            return handler
        except Exception as e:
            logger.error(f"Error creating CallbackHandler: {e}")
            return None

    @contextmanager
    def trace_langgraph_agent(
        self,
        name: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[list[str]] = None,
    ):
        """
        Context manager to wrap LangGraph agent execution with a top-level trace span.

        Args:
            name: Name for the trace span (e.g., "agentic_rag_graph")
            user_id: Optional user identifier
            session_id: Optional session identifier
            metadata: Additional metadata to attach
            tags: Optional tags for the trace

        Yields:
            Tuple of (trace_context, callback_handler) for graph execution
        """
        if not self.client:
            yield (None, None)
            return

        try:
            handler = self.get_callback_handler(
                trace_name=name,
                user_id=user_id,
                session_id=session_id,
                metadata=metadata,
                tags=tags,
            )
            yield (None, handler)
        except Exception as e:
            logger.error(f"Error in trace_langgraph_agent context manager: {e}")
            yield (None, None)

    def get_trace_id(self, trace=None) -> Optional[str]:
        """
        Get the current trace ID from Langfuse context.

        Args:
            trace: Deprecated parameter (not used in v3)

        Returns:
            Trace ID string or None if trace is disabled
        """
        if not self.client:
            return None

        try:
            trace_id = self.client.get_current_trace_id()
            return trace_id
        except Exception as e:
            logger.error(f"Error getting trace ID: {e}")
            return None

    def log_document_access(self, user_id: str, document_id: str, action: str = "read", details: Optional[Dict[str, Any]] = None):
        """Log document access events for audit compliance.
        
        Args:
            user_id: ID of the user accessing the document
            document_id: ID of the accessed document
            action: Type of access (read, search, download)
            details: Additional metadata (access_level, department, etc.)
        """
        if not self.client:
            return

        try:
            self.client.event(
                name=f"document_{action}",
                user_id=user_id,
                metadata={
                    "document_id": document_id,
                    "action": action,
                    "details": details or {},
                },
            )
            logger.debug(f"Logged document access event: user={user_id}, doc={document_id}, action={action}")
        except Exception as e:
            logger.warning(f"Failed to log document access event: {e}")

    def log_audit_event(self, event_type: str, user_id: str, resource: str, details: Dict[str, Any]):
        """Log generic audit events for compliance tracking.
        
        Args:
            event_type: Type of audit event (document_modification, security_event, retention_policy)
            user_id: ID of the user involved
            resource: Resource identifier (e.g., 'document:abc123')
            details: Event-specific details dictionary
        """
        if not self.client:
            return

        try:
            self.client.event(
                name=event_type,
                user_id=user_id,
                metadata={
                    "resource": resource,
                    "details": details,
                },
            )
            logger.debug(f"Logged audit event: {event_type}, user={user_id}, resource={resource}")
        except Exception as e:
            logger.warning(f"Failed to log audit event: {e}")

    def log_retention_action(self, document_id: str, action: str, reason: str, user_id: Optional[str] = None):
        """Log retention policy enforcement actions.
        
        Args:
            document_id: ID of the affected document
            action: Action taken (archive, delete, extend)
            reason: Reason for the action
            user_id: ID of the user performing the action (None for system)
        """
        if not self.client:
            return

        try:
            self.client.event(
                name="retention_action",
                user_id=user_id or "system",
                metadata={
                    "document_id": document_id,
                    "action": action,
                    "reason": reason,
                    "retention_days": self.settings.document_lifecycle.retention_days,
                },
            )
            logger.debug(f"Logged retention action: doc={document_id}, action={action}")
        except Exception as e:
            logger.warning(f"Failed to log retention event: {e}")

    def log_security_event(self, event: str, user_id: Optional[str], reason: str, severity: str = "medium"):
        """Log security-related events like failed auth or access denied.
        
        Args:
            event: Security event type (auth_failure, access_denied)
            user_id: ID of the user involved (None for system events)
            reason: Explanation of the event
            severity: low, medium, high, critical
        """
        if not self.client:
            return

        try:
            self.client.event(
                name="security_event",
                user_id=user_id or "system",
                metadata={
                    "event": event,
                    "reason": reason,
                    "severity": severity,
                },
            )
            logger.debug(f"Logged security event: {event}, severity={severity}")
        except Exception as e:
            logger.warning(f"Failed to log security event: {e}")

    def submit_feedback(
        self,
        trace_id: str,
        score: float,
        name: str = "user-feedback",
        comment: Optional[str] = None,
    ) -> bool:
        """
        Submit user feedback for a trace (following Langfuse cookbook pattern).

        Args:
            trace_id: Trace ID from get_trace_id()
            score: Feedback score (0-1 or -1 to 1)
            name: Name of the score (default: "user-feedback")
            comment: Optional feedback comment

        Returns:
            True if feedback was submitted successfully, False otherwise
        """
        if not self.client:
            logger.warning("Cannot submit feedback: Langfuse is disabled")
            return False

        try:
            self.client.score(
                trace_id=trace_id,
                name=name,
                value=score,
                comment=comment,
            )
            logger.info(f"Submitted feedback for trace {trace_id}: score={score}")
            return True
        except Exception as e:
            logger.error(f"Error submitting feedback: {e}")
            return False

    def flush(self):
        """Flush any pending traces."""
        if self.client:
            try:
                self.client.flush()
            except Exception as e:
                logger.error(f"Error flushing Langfuse: {e}")

    def shutdown(self):
        """Shutdown the Langfuse client."""
        if self.client:
            try:
                self.client.flush()
                self.client.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down Langfuse: {e}")

    @contextmanager
    def start_generation(
        self,
        name: str,
        model: str,
        input_data: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Start a generation span for LLM calls (following Langfuse cookbook pattern).

        Args:
            name: Name for this generation (e.g., "decision_llm", "grading_llm")
            model: Model identifier (e.g., "llama3.2:1b", "gpt-4o")
            input_data: Input to the LLM (prompt or messages)
            metadata: Additional metadata (temperature, max_tokens, etc.)

        Yields:
            Generation context object for updates
        """
        if not self.client:
            yield None
            return

        try:
            generation = self.client.generation(
                name=name,
                model=model,
                input=input_data,
                metadata=metadata or {},
            )
            yield generation
        except Exception as e:
            logger.error(f"Error creating generation: {e}")
            yield None

    @contextmanager
    def start_span(
        self,
        name: str,
        input_data: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Start a generic span for non-LLM operations.

        Args:
            name: Name for this span (e.g., "retrieve_documents", "grade_documents")
            input_data: Input to this operation
            metadata: Additional metadata

        Yields:
            Span context object for updates
        """
        if not self.client:
            yield None
            return

        try:
            span = self.client.span(
                name=name,
                input=input_data,
                metadata=metadata or {},
            )
            yield span
        except Exception as e:
            logger.error(f"Error creating span: {e}")
            yield None

    def update_generation(
        self,
        generation,
        output: Any,
        usage_metadata: Optional[Dict[str, Any]] = None,
        completion_start_time: Optional[float] = None,
    ):
        """Update a generation span with output and usage metrics.

        Args:
            generation: Generation object from start_generation()
            output: LLM output/response
            usage_metadata: Token usage and timing info
            completion_start_time: Optional start time for latency calculation
        """
        if not generation:
            return

        try:
            update_data = {"output": output}

            if usage_metadata:
                if "prompt_tokens" in usage_metadata:
                    update_data["usage"] = {
                        "input": usage_metadata.get("prompt_tokens", 0),
                        "output": usage_metadata.get("completion_tokens", 0),
                        "total": usage_metadata.get("total_tokens", 0),
                    }

                if "latency_ms" in usage_metadata:
                    update_data["metadata"] = update_data.get("metadata", {})
                    update_data["metadata"]["latency_ms"] = usage_metadata["latency_ms"]

            generation.update(**update_data)
            generation.end()
        except Exception as e:
            logger.error(f"Error updating generation: {e}")

    def update_span(
        self,
        span,
        output: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
        level: Optional[str] = None,
        status_message: Optional[str] = None,
    ):
        """Update a span with output and metadata.

        Args:
            span: Span object from start_span()
            output: Operation output
            metadata: Additional metadata to attach
            level: Log level (e.g., "ERROR", "WARNING") for error tracking
            status_message: Status or error message
        """
        if not span:
            return

        try:
            update_data = {}
            if output is not None:
                update_data["output"] = output
            if metadata:
                update_data["metadata"] = metadata
            if level:
                update_data["level"] = level
            if status_message:
                update_data["status_message"] = status_message

            if update_data:
                span.update(**update_data)
            span.end()
        except Exception as e:
            logger.error(f"Error updating span: {e}")
