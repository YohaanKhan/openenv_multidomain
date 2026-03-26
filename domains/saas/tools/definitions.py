"""Tool argument schemas for SaaS domain tools."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SearchTicketsArgs(BaseModel):
    """Search support tickets by keyword with optional filters."""

    query: str = Field(..., description="Keyword to search in ticket title and body")
    customer_id: Optional[str] = Field(
        None, description="Filter by customer ID e.g. C-1042"
    )
    status: Optional[str] = Field(
        None, description="Filter by status: open | closed | escalated"
    )
    category: Optional[str] = Field(
        None, description="Filter by category: billing | access | fraud | downgrade"
    )


class GetAccountArgs(BaseModel):
    """Retrieve full account details for a customer including plan and VIP status."""

    customer_id: str = Field(..., description="Customer ID e.g. C-1042")


class GetTransactionsArgs(BaseModel):
    """List all transactions for a customer account."""

    customer_id: str = Field(
        ..., description="Customer ID to retrieve transactions for"
    )
    limit: Optional[int] = Field(
        10, description="Maximum number of most recent transactions to return", ge=1, le=50
    )


class IssueRefundArgs(BaseModel):
    """Issue a monetary refund to a customer."""

    customer_id: str = Field(..., description="Customer ID to issue the refund to")
    transaction_id: str = Field(
        ..., description="Transaction ID to refund e.g. TX-9001"
    )
    amount: float = Field(
        ..., description="Refund amount in USD. Cannot exceed the original charge.", gt=0
    )
    reason: str = Field(..., description="Brief reason for issuing the refund")


class SendEmailArgs(BaseModel):
    """Send an email notification to a customer."""

    customer_id: str = Field(..., description="Customer ID to send the email to")
    subject: str = Field(..., description="Email subject line")
    body: str = Field(..., description="Full email body text")


class EscalateTicketArgs(BaseModel):
    """Escalate a support ticket to a higher tier for specialist handling."""

    ticket_id: str = Field(..., description="Ticket ID to escalate e.g. T-5001")
    tier: int = Field(2, description="Target support tier: 2 or 3", ge=2, le=3)
    reason: str = Field(..., description="Reason for escalation")


class CloseTicketArgs(BaseModel):
    """Mark a ticket as resolved and close it."""

    ticket_id: str = Field(..., description="Ticket ID to close e.g. T-5001")
    resolution: str = Field(..., description="Summary of how the issue was resolved")
