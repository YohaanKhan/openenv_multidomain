"\"\"\"Legal domain ORM schema with clause-structured contracts.\"\"\""

from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey
from sqlalchemy.orm import relationship

from server.utils.db import Base


class Contract(Base):
    __tablename__ = "legal_contracts"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    contract_type = Column(String, nullable=False)
    parties = Column(String, nullable=False)
    status = Column(String, nullable=False, default="under_review")

    clauses = relationship("Clause", back_populates="contract")
    memos = relationship("MemoNote", back_populates="contract")


class Clause(Base):
    __tablename__ = "legal_clauses"

    id = Column(String, primary_key=True)
    contract_id = Column(String, ForeignKey("legal_contracts.id"), nullable=False)
    clause_type = Column(String, nullable=False)
    party = Column(String, nullable=False, default="all")
    content = Column(Text, nullable=False)
    is_standard = Column(Boolean, nullable=False, default=True)
    risk_level = Column(String, nullable=False, default="none")

    contract = relationship("Contract", back_populates="clauses")


class StandardTerm(Base):
    __tablename__ = "legal_standard_terms"

    id = Column(String, primary_key=True)
    clause_type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    notes = Column(String, nullable=False, default="")


class MemoNote(Base):
    __tablename__ = "legal_memo_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(String, ForeignKey("legal_contracts.id"), nullable=False)
    section = Column(String, nullable=False)
    note = Column(Text, nullable=False)

    contract = relationship("Contract", back_populates="memos")
