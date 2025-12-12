"""SQLAlchemy models.

Note: Products and Orders are NOT stored locally.
They are fetched from CHICX backend API in real-time.
"""

from app.models.user import User
from app.models.conversation import Conversation, Message
from app.models.knowledge import FAQ, Embedding
from app.models.voice import Call, CallTranscript
from app.models.system import Template, AnalyticsEvent, SearchLog

__all__ = [
    "User",
    "Conversation",
    "Message",
    "FAQ",
    "Embedding",
    "Call",
    "CallTranscript",
    "Template",
    "AnalyticsEvent",
    "SearchLog",
]
