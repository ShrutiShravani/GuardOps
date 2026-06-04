import contextvars
from typing import Optional, Any, List
from langfuse import Langfuse
from langfuse import get_client
from langfuse import propagate_attributes
import logging
from opentelemetry import trace

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
            langfuse_client = get_client() 
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
    def log_score(cls,score_name:str,score_value:float,comment:str):
        """
        Pushes a real-time system metric valuation score directly to the 
        Langfuse analytics dashboard for automated security audit logging.
        """
        current_span= trace.get_current_span()

        if current_span.is_recording():
            current_span.set_attribute("guardops.interception_triggered", True)
        current_span.add_event(
            name="langfuse.score",
            attributes={
                "langfuse.score.name":str(score_name),
                "langfuse.score.value":float(score_value),
                "langfuse.score.comment":str(comment)

            }
        )
    
    @classmethod
    def flush_records(cls) -> None:
        """Forces the background delivery queue to dispatch records to the server immediately."""
        client = cls.get_global_client()
        client.flush()