from __future__ import annotations

"""SQLAlchemy ORM models."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def _utcnow():
    return datetime.now(timezone.utc)


class Project(Base):
    """A bid document that has been imported."""

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_name = Column(String(500), nullable=True, comment="提取的项目名称")
    bidder_name = Column(String(300), nullable=True, comment="招标人名称")
    submission_deadline = Column(DateTime, nullable=True, comment="投标截止日期")
    source_file_name = Column(String(500), nullable=False, comment="原始文件名")
    source_file_path = Column(String(1000), nullable=False, comment="存储路径")
    source_format = Column(String(10), nullable=False, comment="pdf 或 docx")
    total_chars = Column(Integer, default=0, comment="文档总字符数")
    raw_text = Column(Text, nullable=True, comment="解析后的纯文本")
    status = Column(
        String(20), default="imported", comment="imported|extracted|completed"
    )
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    documents = relationship(
        "Document", back_populates="project", cascade="all, delete-orphan"
    )
    calendar_events = relationship(
        "CalendarEvent", back_populates="project", cascade="all, delete-orphan"
    )


class Document(Base):
    """Generated file artifact (markdown, excel, etc.)."""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    doc_type = Column(String(20), nullable=False, comment="markdown|excel|raw")
    file_name = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utcnow)

    project = relationship("Project", back_populates="documents")


class CalendarEvent(Base):
    """Feishu calendar reminder event."""

    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    feishu_event_id = Column(String(200), nullable=True, comment="飞书 Event ID")
    calendar_id = Column(String(200), nullable=True, comment="飞书日历 ID")
    event_title = Column(String(500), nullable=True)
    event_date = Column(DateTime, nullable=True, comment="提醒日期(截止前4天)")
    slot_start = Column(DateTime, nullable=True, comment="分配的起始时间")
    slot_end = Column(DateTime, nullable=True, comment="分配的结束时间")
    status = Column(
        String(20), default="pending", comment="pending|created|failed"
    )
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    project = relationship("Project", back_populates="calendar_events")


class AppConfig(Base):
    """Key-value configuration store."""

    __tablename__ = "app_config"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
