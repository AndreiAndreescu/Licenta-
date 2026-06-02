from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.utcnow()


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(String(500), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    max_depth = Column(Integer, nullable=False)
    max_pages = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=lambda ctx: utcnow())
    pages_crawled = Column(Integer, nullable=False, default=0)
    pages_analyzed = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    verdict = Column(String(20), nullable=True)
    verdict_confidence = Column(Integer, nullable=True)
    verdict_evidence = Column(Text, nullable=True)

    pages = relationship("Page", back_populates="job", cascade="all, delete-orphan")


class Page(Base):
    __tablename__ = "pages"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    url = Column(String(2048), nullable=False)
    title = Column(String(500), nullable=True)
    http_status = Column(Integer, nullable=True)
    fetched_at = Column(DateTime, nullable=False, default=utcnow)
    language = Column(String(10), nullable=True)

    job = relationship("Job", back_populates="pages")
    extraction = relationship("Extraction", back_populates="page", uselist=False, cascade="all, delete-orphan")
    analysis = relationship("Analysis", back_populates="page", uselist=False, cascade="all, delete-orphan")


class Extraction(Base):
    __tablename__ = "extractions"

    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(Integer, ForeignKey("pages.id", ondelete="CASCADE"), nullable=False, unique=True)
    clean_text = Column(Text, nullable=False)
    author = Column(String(200), nullable=True)
    publish_date = Column(String(100), nullable=True)

    page = relationship("Page", back_populates="extraction")


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(Integer, ForeignKey("pages.id", ondelete="CASCADE"), nullable=False, unique=True)
    summary = Column(Text, nullable=True)
    keywords = Column(Text, nullable=True)
    sentiment_label = Column(String(20), nullable=True)
    sentiment_score = Column(Float, nullable=True)
    entities = Column(Text, nullable=True)

    page = relationship("Page", back_populates="analysis")
