"""
MedAI Assistant - Chat Models
Chat sessions and messages with conversational memory.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), default="New Conversation")
    language: Mapped[str] = mapped_column(String(10), default="en")  # en | hi
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship(
        "ChatMessage",
        back_populates="session",
        order_by="ChatMessage.created_at",
        cascade="all, delete-orphan",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chat_sessions.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # user | assistant | system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[str] = mapped_column(
        Text, nullable=True
    )  # JSON string for confidence, sources, emergency flags
    is_emergency: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    session = relationship("ChatSession", back_populates="messages")
