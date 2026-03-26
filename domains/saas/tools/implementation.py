"""Pure tool logic for the SaaS domain."""

from __future__ import annotations

from sqlalchemy.orm import Session

try:
    from ..schema import Customer, Email, Ticket, Transaction
    from .definitions import (
        CloseTicketArgs,
        EscalateTicketArgs,
        GetAccountArgs,
        GetTransactionsArgs,
        IssueRefundArgs,
        SearchTicketsArgs,
        SendEmailArgs,
    )
except ImportError:
    from domains.saas.schema import Customer, Email, Ticket, Transaction
    from domains.saas.tools.definitions import (
        CloseTicketArgs,
        EscalateTicketArgs,
        GetAccountArgs,
        GetTransactionsArgs,
        IssueRefundArgs,
        SearchTicketsArgs,
        SendEmailArgs,
    )


def search_tickets(args: SearchTicketsArgs, session: Session) -> str:
    """Search tickets matching the query and optional filters."""
    query = session.query(Ticket)
    filters = []
    if args.customer_id:
        filters.append(Ticket.customer_id == args.customer_id)
    if args.status:
        filters.append(Ticket.status == args.status)
    if args.category:
        filters.append(Ticket.category == args.category)
    keyword = f"%{args.query}%"
    filters.append(
        (Ticket.title.ilike(keyword)) | (Ticket.body.ilike(keyword))
    )
    results = query.filter(*filters).order_by(Ticket.priority.desc(), Ticket.id).all()
    if not results:
        return f"No tickets found matching '{args.query}'."
    lines = [
        (
            f"{ticket.id}: {ticket.title} | status={ticket.status} | priority={ticket.priority} "
            f"| category={ticket.category} | customer={ticket.customer_id} | tier={ticket.tier} "
            f"| updated={ticket.updated_at or 'n/a'}"
        )
        for ticket in results
    ]
    return "Found tickets:\n" + "\n".join(lines)


def get_account(args: GetAccountArgs, session: Session) -> str:
    """Retrieve customer profile details."""
    customer = session.get(Customer, args.customer_id)
    if not customer:
        return f"No customer found with ID '{args.customer_id}'."
    vip = "Yes" if customer.is_vip else "No"
    return (
        f"Customer {customer.name} ({customer.id})\n"
        f"Company: {customer.company or 'Individual'}\n"
        f"Email: {customer.email}\n"
        f"Plan: {customer.plan}\n"
        f"Account Status: {customer.account_status}\n"
        f"VIP: {vip}"
    )


def get_transactions(args: GetTransactionsArgs, session: Session) -> str:
    """List transactions for a customer."""
    txs = (
        session.query(Transaction)
        .filter(Transaction.customer_id == args.customer_id)
        .order_by(Transaction.created_at.desc(), Transaction.id.desc())
        .limit(args.limit or 10)
        .all()
    )
    if not txs:
        return f"No transactions found for customer '{args.customer_id}'."
    lines = [
        (
            f"{tx.id}: ${tx.amount:.2f} {tx.currency} | {tx.description} | "
            f"status={tx.status} | method={tx.payment_method} | created={tx.created_at or 'n/a'}"
        )
        for tx in txs
    ]
    return "Transactions:\n" + "\n".join(lines)


def issue_refund(args: IssueRefundArgs, session: Session) -> str:
    """Refund a transaction and mark it refunded."""
    tx = session.get(Transaction, args.transaction_id)
    if not tx:
        return f"Transaction '{args.transaction_id}' not found."
    customer = session.get(Customer, args.customer_id)
    if not customer:
        return f"No customer found with ID '{args.customer_id}'."
    if tx.customer_id != args.customer_id:
        return f"Transaction '{args.transaction_id}' does not belong to '{args.customer_id}'."
    if tx.status == "refunded":
        return f"Transaction '{args.transaction_id}' has already been refunded."
    if args.amount > tx.amount:
        return f"Refund amount exceeds original charge of ${tx.amount:.2f}."
    tx.status = "refunded"
    session.flush()
    return (
        f"Refund issued for ${args.amount:.2f} on transaction {tx.id} for customer "
        f"{args.customer_id}. Original charge=${tx.amount:.2f}. Reason: {args.reason}"
    )


def send_email(args: SendEmailArgs, session: Session) -> str:
    """Log an email sent to the customer."""
    customer = session.get(Customer, args.customer_id)
    if not customer:
        return f"No customer found with ID '{args.customer_id}'."
    email = Email(customer_id=args.customer_id, subject=args.subject, body=args.body)
    session.add(email)
    session.flush()
    return (
        f"Email sent to customer {args.customer_id} ({customer.email}). "
        f"Subject: '{args.subject}'"
    )


def escalate_ticket(args: EscalateTicketArgs, session: Session) -> str:
    """Escalate a ticket to a higher support tier."""
    ticket = session.get(Ticket, args.ticket_id)
    if not ticket:
        return f"Ticket '{args.ticket_id}' not found."
    ticket.status = "escalated"
    ticket.tier = args.tier
    ticket.updated_at = ticket.updated_at or ""
    session.flush()
    return (
        f"Ticket {ticket.id} escalated to tier {args.tier} for customer {ticket.customer_id} "
        f"because: {args.reason}"
    )


def close_ticket(args: CloseTicketArgs, session: Session) -> str:
    """Close a ticket with a resolution note."""
    ticket = session.get(Ticket, args.ticket_id)
    if not ticket:
        return f"Ticket '{args.ticket_id}' not found."
    ticket.status = "closed"
    ticket.resolution = args.resolution
    ticket.updated_at = ticket.updated_at or ""
    session.flush()
    return (
        f"Ticket {ticket.id} closed for customer {ticket.customer_id}. "
        f"Resolution: {ticket.resolution}"
    )
