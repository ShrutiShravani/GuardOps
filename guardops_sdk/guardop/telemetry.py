import contextvars
from typing import Optional, Any, List
from langfuse import Langfuse
from langfuse import propagate_attributes
import logging

# Standard instantiation automatically reads LANGFUSE_PUBLIC_KEY, SECRET_KEY, & HOST from the env!
langfuse_client: Optional[Langfuse] = None

# Flawless thread-safe isolation context container
active_trace_ctx: contextvars.ContextVar[Optional[Any]] = contextvars.ContextVar("active_trace_ctx", default=None)

class GuardTelemetry:
    """Manages thread-safe trace session initialization and attribute propagation."""
    @classmethod
    def get_global_client(cls)->Langfuse:
        global langfuse_client
        if langfuse_client is None:
            langfuse_client = Langfuse()
        return langfuse_client


    @classmethod
    def start_trace_session(cls, trace_name: str, user_id: str, tags: List[str]) -> Any:
        """Spawns a root observation context for a single transaction string."""
        client= cls.get_global_client()
        context_manager = client.start_as_current_observation(
            name=trace_name,
            as_type="span"
        )
        
        span = context_manager.__enter__()

        attr_context = propagate_attributes(
            trace_name=trace_name,
            user_id=user_id,
            tags=tags
        )
        attr_context.__enter__()

        # Save the span container reference to the isolated ContextVar
        active_trace_ctx.set(span)

        return context_manager
        
    @classmethod
    def get_active_trace(cls) -> Optional[Any]:
        """Fetches the isolated trace context belonging strictly to this execution thread."""
        return active_trace_ctx.get()

    @classmethod
    def log_breach_score(cls, trace_id: str, tag: str, score: float, comment: Optional[str] = None) -> None:
        """
        Pushes a real-time system metric valuation score directly to the 
        Langfuse analytics dashboard for automated security audit logging.
        """
        langfuse_client.create_score(
            trace_id=trace_id,
            name=tag,
            value=score,
            comment=comment or "Automated boundary breach intercepted by GuardOps Engine."
        )
    
    @classmethod
    def flush_records(cls) -> None:
        """Forces the background delivery queue to dispatch records to the server immediately."""
        langfuse_client.flush()