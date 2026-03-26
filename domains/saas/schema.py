"""SQLAlchemy schema for the SaaS domain tables."""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from server.utils.db import Base


class Customer(Base):
    """SaaS customer record."""

    __tablename__ = "saas_customers"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    company = Column(String, default="", nullable=False)
    plan = Column(String, default="pro", nullable=False)
    account_status = Column(String, default="active", nullable=False)
    is_vip = Column(Boolean, default=False, nullable=False)

    tickets = relationship("Ticket", back_populates="customer", cascade="all, delete-orphan")
    transactions = relationship(
        "Transaction", back_populates="customer", cascade="all, delete-orphan"
    )


class Ticket(Base):
    """Customer support ticket."""

    __tablename__ = "saas_tickets"

    id = Column(String, primary_key=True)
    customer_id = Column(String, ForeignKey("saas_customers.id"), nullable=False)
    title = Column(String, nullable=False)
    body = Column(Text, default="", nullable=False)
    status = Column(String, default="open", nullable=False)
    priority = Column(String, default="normal", nullable=False)
    category = Column(String, default="general", nullable=False)
    tier = Column(Integer, default=1, nullable=False)
    created_at = Column(String, default="", nullable=False)
    updated_at = Column(String, default="", nullable=False)
    resolution = Column(Text, default="", nullable=False)

    customer = relationship("Customer", back_populates="tickets")


class Transaction(Base):
    """Billing transaction tied to a customer."""

    __tablename__ = "saas_transactions"

    id = Column(String, primary_key=True)
    customer_id = Column(String, ForeignKey("saas_customers.id"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD", nullable=False)
    description = Column(String, default="", nullable=False)
    payment_method = Column(String, default="card", nullable=False)
    created_at = Column(String, default="", nullable=False)
    status = Column(String, default="charged", nullable=False)

    customer = relationship("Customer", back_populates="transactions")


class Email(Base):
    """Tracking emails sent to customers."""

    __tablename__ = "saas_emails"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
