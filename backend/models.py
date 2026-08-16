from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float, Enum, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base
import enum

class AutomationPotential(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"

class Industry(Base):
    __tablename__ = "industries"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_analyzed_at = Column(DateTime(timezone=True), onupdate=func.now())

    stages = relationship("ValueChainStage", back_populates="industry", cascade="all, delete-orphan")
    queries = relationship("QueryLog", back_populates="industry", cascade="all, delete-orphan")

class ValueChainStage(Base):
    __tablename__ = "value_chain_stages"

    id = Column(Integer, primary_key=True, index=True)
    industry_id = Column(Integer, ForeignKey("industries.id"))
    name = Column(String, index=True)
    sequence_order = Column(Integer)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    industry = relationship("Industry", back_populates="stages")
    processes = relationship("Process", back_populates="stage", cascade="all, delete-orphan")

class Process(Base):
    __tablename__ = "processes"

    id = Column(Integer, primary_key=True, index=True)
    stage_id = Column(Integer, ForeignKey("value_chain_stages.id"))
    name = Column(String, index=True)
    business_purpose = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    stage = relationship("ValueChainStage", back_populates="processes")
    finding = relationship("ProcessFinding", back_populates="process", uselist=False, cascade="all, delete-orphan")
    evidence = relationship("EvidenceSource", back_populates="process", cascade="all, delete-orphan")
    priority_score = relationship("PriorityScore", back_populates="process", uselist=False, cascade="all, delete-orphan")

class ProcessFinding(Base):
    __tablename__ = "process_findings"

    id = Column(Integer, primary_key=True, index=True)
    process_id = Column(Integer, ForeignKey("processes.id"))
    current_challenges = Column(Text)
    ai_opportunity = Column(Text)
    relevant_ai_capabilities = Column(Text)
    potential_benefit = Column(Text)
    risk = Column(Text)
    automation_potential = Column(Enum(AutomationPotential))
    confidence_score = Column(Float)

    process = relationship("Process", back_populates="finding")
    supported_by = relationship("EvidenceSource", back_populates="finding")

class EvidenceSource(Base):
    __tablename__ = "evidence_sources"

    id = Column(Integer, primary_key=True, index=True)
    process_id = Column(Integer, ForeignKey("processes.id"))
    source_url = Column(String)
    source_title = Column(String)
    retrieved_at = Column(DateTime(timezone=True), server_default=func.now())
    extracted_snippet = Column(Text)
    supports_finding_id = Column(Integer, ForeignKey("process_findings.id"), nullable=True)

    process = relationship("Process", back_populates="evidence")
    finding = relationship("ProcessFinding", back_populates="supported_by")

class PriorityScore(Base):
    __tablename__ = "priority_scores"

    id = Column(Integer, primary_key=True, index=True)
    process_id = Column(Integer, ForeignKey("processes.id"))
    business_impact_score = Column(Float)
    feasibility_score = Column(Float)
    risk_score = Column(Float)
    evidence_confidence = Column(Float)
    final_priority_score = Column(Float)
    rank = Column(Integer, nullable=True)
    computed_at = Column(DateTime(timezone=True), server_default=func.now())

    process = relationship("Process", back_populates="priority_score")

class QueryLog(Base):
    __tablename__ = "query_log"

    id = Column(Integer, primary_key=True, index=True)
    industry_id = Column(Integer, ForeignKey("industries.id"))
    question = Column(Text)
    answer = Column(Text)
    retrieved_evidence_ids = Column(Text) # JSON string of IDs
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    industry = relationship("Industry", back_populates="queries")
