from datetime import date, datetime

from sqlalchemy import Computed, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.models.tag import Tag


class Entry(Base):
    __tablename__ = "entries"
    __table_args__ = (
        Index("ix_entries_search_vector", "search_vector", postgresql_using="gin"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    mood: Mapped[int]
    entry_date: Mapped[date]
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    tags: Mapped[list["Tag"]] = relationship(secondary="entry_tags", lazy="selectin")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english', title || ' ' || content)", persisted=True),
        nullable=True,
    )