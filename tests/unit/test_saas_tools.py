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
from domains.saas.tools.implementation import (
    close_ticket,
    escalate_ticket,
    get_account,
    get_transactions,
    issue_refund,
    search_tickets,
    send_email,
)


def _customer(customer_id: str = "C-1") -> Customer:
    return Customer(id=customer_id, name="Test User", email="test@example.com", plan="pro")


def test_search_tickets_keyword_match(session):
    session.add(_customer())
    session.add(
        Ticket(
            id="T-1",
            customer_id="C-1",
            title="Billing problem",
            body="wrong charge on invoice",
            status="open",
            priority="normal",
            category="billing",
        )
    )
    session.flush()

    result = search_tickets(SearchTicketsArgs(query="billing"), session)

    assert "T-1" in result
    assert "Billing problem" in result


def test_search_tickets_not_found(session):
    result = search_tickets(SearchTicketsArgs(query="missing"), session)
    assert "No tickets found" in result


def test_get_account_happy_path(session):
    session.add(Customer(id="C-1", name="Ava", email="ava@example.com", plan="enterprise", is_vip=True))
    session.flush()

    result = get_account(GetAccountArgs(customer_id="C-1"), session)

    assert "Ava" in result
    assert "enterprise" in result
    assert "VIP: Yes" in result


def test_get_account_not_found(session):
    result = get_account(GetAccountArgs(customer_id="C-404"), session)
    assert "No customer found" in result


def test_get_transactions_happy_path(session):
    session.add(_customer())
    session.add(
        Transaction(
            id="TX-1",
            customer_id="C-1",
            amount=49.0,
            description="Monthly Pro subscription",
            status="charged",
        )
    )
    session.flush()

    result = get_transactions(GetTransactionsArgs(customer_id="C-1"), session)

    assert "Transactions:" in result
    assert "TX-1" in result


def test_get_transactions_not_found(session):
    result = get_transactions(GetTransactionsArgs(customer_id="C-404"), session)
    assert "No transactions found" in result


def test_issue_refund_happy_path(session):
    session.add(_customer())
    session.add(
        Transaction(
            id="TX-1",
            customer_id="C-1",
            amount=49.0,
            description="Duplicate charge",
            status="charged",
        )
    )
    session.flush()

    result = issue_refund(
        IssueRefundArgs(
            customer_id="C-1",
            transaction_id="TX-1",
            amount=49.0,
            reason="Duplicate billing",
        ),
        session,
    )

    assert "Refund issued" in result
    assert session.get(Transaction, "TX-1").status == "refunded"


def test_issue_refund_transaction_not_found(session):
    result = issue_refund(
        IssueRefundArgs(
            customer_id="C-1",
            transaction_id="TX-404",
            amount=10.0,
            reason="Missing tx",
        ),
        session,
    )
    assert "not found" in result.lower()


def test_issue_refund_prevents_double_refund(session):
    session.add(_customer())
    session.add(
        Transaction(
            id="TX-1",
            customer_id="C-1",
            amount=49.0,
            description="Already refunded",
            status="refunded",
        )
    )
    session.flush()

    result = issue_refund(
        IssueRefundArgs(
            customer_id="C-1",
            transaction_id="TX-1",
            amount=49.0,
            reason="Retry",
        ),
        session,
    )

    assert "already been refunded" in result


def test_issue_refund_prevents_overcharge(session):
    session.add(_customer())
    session.add(
        Transaction(
            id="TX-1",
            customer_id="C-1",
            amount=49.0,
            description="Monthly charge",
            status="charged",
        )
    )
    session.flush()

    result = issue_refund(
        IssueRefundArgs(
            customer_id="C-1",
            transaction_id="TX-1",
            amount=50.0,
            reason="Too high",
        ),
        session,
    )

    assert "exceeds original charge" in result
    assert session.get(Transaction, "TX-1").status == "charged"


def test_issue_refund_wrong_customer(session):
    session.add(_customer("C-1"))
    session.add(_customer("C-2"))
    session.add(
        Transaction(
            id="TX-1",
            customer_id="C-1",
            amount=49.0,
            description="Monthly charge",
            status="charged",
        )
    )
    session.flush()

    result = issue_refund(
        IssueRefundArgs(
            customer_id="C-2",
            transaction_id="TX-1",
            amount=10.0,
            reason="Wrong customer",
        ),
        session,
    )

    assert "does not belong" in result
    assert session.get(Transaction, "TX-1").status == "charged"


def test_send_email_returns_confirmation(session):
    session.add(_customer())
    session.flush()

    result = send_email(
        SendEmailArgs(
            customer_id="C-1",
            subject="Refund processed",
            body="Your refund has been issued.",
        ),
        session,
    )

    email = session.query(Email).filter(Email.customer_id == "C-1").one()
    assert "Email sent" in result
    assert email.subject == "Refund processed"


def test_escalate_ticket_updates_tier(session):
    session.add(_customer())
    session.add(
        Ticket(
            id="T-1",
            customer_id="C-1",
            title="Fraud concern",
            body="Unknown charges",
            status="open",
            tier=1,
        )
    )
    session.flush()

    result = escalate_ticket(
        EscalateTicketArgs(ticket_id="T-1", tier=2, reason="Fraud review"),
        session,
    )

    ticket = session.get(Ticket, "T-1")
    assert "escalated" in result.lower()
    assert ticket.status == "escalated"
    assert ticket.tier == 2


def test_escalate_ticket_not_found(session):
    result = escalate_ticket(
        EscalateTicketArgs(ticket_id="T-404", tier=2, reason="Missing"),
        session,
    )
    assert "not found" in result.lower()


def test_close_ticket_result_contains_closed(session):
    session.add(_customer())
    session.add(Ticket(id="T-1", customer_id="C-1", title="Issue", body="Need help"))
    session.flush()

    result = close_ticket(
        CloseTicketArgs(ticket_id="T-1", resolution="Fixed"),
        session,
    )

    ticket = session.get(Ticket, "T-1")
    assert "closed" in result.lower()
    assert ticket.status == "closed"
    assert ticket.resolution == "Fixed"


def test_close_ticket_not_found(session):
    result = close_ticket(
        CloseTicketArgs(ticket_id="T-404", resolution="No-op"),
        session,
    )
    assert "not found" in result.lower()
