"""Task definitions and deterministic seed data for the SaaS domain."""

from __future__ import annotations

from sqlalchemy.orm import Session
try:
    from . import schema
except ImportError:
    from domains.saas import schema

TASKS = [
    {
        "id": "saas_easy",
        "name": "Billing Ticket Resolution",
        "difficulty": "easy",
        "max_steps": 6,
        "description": (
            "Customer C-1042 (Jane Smith at Northstar Design) has several historical "
            "support records, but only one currently open billing issue about an "
            "incorrect annual renewal charge. Find the correct open ticket for that "
            "customer and close it with a clear billing resolution."
        ),
    },
    {
        "id": "saas_medium",
        "name": "Double Charge Refund",
        "difficulty": "medium",
        "max_steps": 12,
        "description": (
            "Customer C-2077 (Bob Chen at LaunchLedger) reports a duplicate monthly "
            "subscription charge. Review the account and transaction history, refund "
            "only the duplicate November charge, send a confirmation email, then close "
            "the related billing ticket."
        ),
    },
    {
        "id": "saas_hard",
        "name": "VIP Multi-Ticket Triage",
        "difficulty": "hard",
        "max_steps": 20,
        "description": (
            "VIP enterprise customer C-9001 (Alice Corp) has multiple active issues. "
            "There is one urgent fraud-related billing concern that must be escalated, "
            "one duplicate charge that should be refunded, and one open billing ticket "
            "that can be closed after resolution. Review the account carefully, refund "
            "the correct duplicate transaction, escalate the urgent fraud ticket to Tier 2, "
            "close the resolved billing ticket, and send a customer update email."
        ),
    },
]


def _seed_customers(session: Session, customers: list[dict]) -> None:
    for customer in customers:
        session.merge(schema.Customer(**customer))


def _seed_tickets(session: Session, tickets: list[dict]) -> None:
    for ticket in tickets:
        session.merge(schema.Ticket(**ticket))


def _seed_transactions(session: Session, transactions: list[dict]) -> None:
    for transaction in transactions:
        session.merge(schema.Transaction(**transaction))


def seed(task_id: str, session: Session) -> dict[str, str]:
    """Insert deterministic seed data matching the requested task."""

    if task_id == "saas_easy":
        _seed_customers(
            session,
            [
                {
                    "id": "C-1042",
                    "name": "Jane Smith",
                    "email": "jane@northstardesign.com",
                    "company": "Northstar Design",
                    "plan": "pro",
                    "account_status": "active",
                },
                {
                    "id": "C-1043",
                    "name": "Janet Smythe",
                    "email": "janet@northstardesign.co",
                    "company": "Northstar Design Studio",
                    "plan": "starter",
                    "account_status": "active",
                },
                {
                    "id": "C-1100",
                    "name": "Marco Reed",
                    "email": "marco@clearledger.io",
                    "company": "ClearLedger",
                    "plan": "pro",
                    "account_status": "past_due",
                },
                {
                    "id": "C-1199",
                    "name": "Ari Patel",
                    "email": "ari@sprucelabs.dev",
                    "company": "Spruce Labs",
                    "plan": "enterprise",
                    "account_status": "active",
                },
            ],
        )
        _seed_tickets(
            session,
            [
                {
                    "id": "T-5001",
                    "customer_id": "C-1042",
                    "title": "Incorrect annual renewal charge",
                    "body": (
                        "Our account was renewed at $199, but I expected the promotional "
                        "renewal price of $149. Please review the billing line item."
                    ),
                    "status": "open",
                    "priority": "high",
                    "category": "billing",
                    "tier": 1,
                    "created_at": "2026-03-11T09:14:00Z",
                    "updated_at": "2026-03-11T09:14:00Z",
                },
                {
                    "id": "T-5000",
                    "customer_id": "C-1042",
                    "title": "Need invoice PDF for February",
                    "body": "Please resend the February invoice PDF to accounting.",
                    "status": "closed",
                    "priority": "normal",
                    "category": "billing",
                    "tier": 1,
                    "created_at": "2026-02-22T16:40:00Z",
                    "updated_at": "2026-02-22T18:05:00Z",
                    "resolution": "Invoice PDF resent to billing contact.",
                },
                {
                    "id": "T-5006",
                    "customer_id": "C-1043",
                    "title": "Billing question about discount expiration",
                    "body": "Our trial discount disappeared on the March invoice.",
                    "status": "open",
                    "priority": "normal",
                    "category": "billing",
                    "tier": 1,
                    "created_at": "2026-03-12T13:20:00Z",
                    "updated_at": "2026-03-12T13:20:00Z",
                },
                {
                    "id": "T-5010",
                    "customer_id": "C-1100",
                    "title": "Card declined after retry",
                    "body": "Our finance team wants to know why the retry failed twice.",
                    "status": "open",
                    "priority": "high",
                    "category": "billing",
                    "tier": 1,
                    "created_at": "2026-03-08T07:55:00Z",
                    "updated_at": "2026-03-08T07:55:00Z",
                },
                {
                    "id": "T-5022",
                    "customer_id": "C-1199",
                    "title": "Quarterly invoicing setup",
                    "body": "Please switch us to quarterly invoicing next renewal.",
                    "status": "pending",
                    "priority": "low",
                    "category": "billing",
                    "tier": 1,
                    "created_at": "2026-03-10T20:10:00Z",
                    "updated_at": "2026-03-10T20:10:00Z",
                },
            ],
        )
        _seed_transactions(
            session,
            [
                {
                    "id": "TX-5001",
                    "customer_id": "C-1042",
                    "amount": 199.0,
                    "currency": "USD",
                    "description": "Annual Pro renewal",
                    "payment_method": "visa_4242",
                    "created_at": "2026-03-11T09:10:00Z",
                    "status": "charged",
                },
                {
                    "id": "TX-5000",
                    "customer_id": "C-1042",
                    "amount": 149.0,
                    "currency": "USD",
                    "description": "Expected promotional annual renewal",
                    "payment_method": "visa_4242",
                    "created_at": "2025-03-11T09:10:00Z",
                    "status": "charged",
                },
                {
                    "id": "TX-5010",
                    "customer_id": "C-1043",
                    "amount": 49.0,
                    "currency": "USD",
                    "description": "Starter monthly renewal",
                    "payment_method": "visa_1881",
                    "created_at": "2026-03-12T13:18:00Z",
                    "status": "charged",
                },
            ],
        )
        session.flush()
    elif task_id == "saas_medium":
        _seed_customers(
            session,
            [
                {
                    "id": "C-2077",
                    "name": "Bob Chen",
                    "email": "bob@launchledger.com",
                    "company": "LaunchLedger",
                    "plan": "pro",
                    "account_status": "active",
                },
                {
                    "id": "C-2078",
                    "name": "Bobby Chen",
                    "email": "bobby@launchledger.co",
                    "company": "LaunchLedger Consulting",
                    "plan": "pro",
                    "account_status": "active",
                },
                {
                    "id": "C-2088",
                    "name": "Rita Gomez",
                    "email": "rita@beamops.io",
                    "company": "BeamOps",
                    "plan": "starter",
                    "account_status": "active",
                },
                {
                    "id": "C-2099",
                    "name": "Devon Hart",
                    "email": "devon@stackyard.ai",
                    "company": "Stackyard AI",
                    "plan": "enterprise",
                    "account_status": "active",
                },
            ],
        )
        _seed_transactions(
            session,
            [
                {
                    "id": "TX-9001",
                    "customer_id": "C-2077",
                    "amount": 49.0,
                    "currency": "USD",
                    "description": "Monthly Pro subscription - November",
                    "payment_method": "visa_9992",
                    "created_at": "2025-11-01T08:00:00Z",
                    "status": "charged",
                },
                {
                    "id": "TX-9002",
                    "customer_id": "C-2077",
                    "amount": 49.0,
                    "currency": "USD",
                    "description": "Monthly Pro subscription - November duplicate retry",
                    "payment_method": "visa_9992",
                    "created_at": "2025-11-01T08:01:00Z",
                    "status": "charged",
                },
                {
                    "id": "TX-9003",
                    "customer_id": "C-2077",
                    "amount": 49.0,
                    "currency": "USD",
                    "description": "Monthly Pro subscription - October",
                    "payment_method": "visa_9992",
                    "created_at": "2025-10-01T08:00:00Z",
                    "status": "charged",
                },
                {
                    "id": "TX-9004",
                    "customer_id": "C-2077",
                    "amount": 15.0,
                    "currency": "USD",
                    "description": "Storage overage adjustment",
                    "payment_method": "visa_9992",
                    "created_at": "2025-11-02T10:30:00Z",
                    "status": "charged",
                },
                {
                    "id": "TX-9010",
                    "customer_id": "C-2078",
                    "amount": 49.0,
                    "currency": "USD",
                    "description": "Monthly Pro subscription - November",
                    "payment_method": "mc_1221",
                    "created_at": "2025-11-01T08:00:00Z",
                    "status": "charged",
                },
                {
                    "id": "TX-9011",
                    "customer_id": "C-2088",
                    "amount": 19.0,
                    "currency": "USD",
                    "description": "Starter monthly subscription",
                    "payment_method": "amex_3030",
                    "created_at": "2025-11-01T06:45:00Z",
                    "status": "refunded",
                },
            ],
        )
        _seed_tickets(
            session,
            [
                {
                    "id": "T-5002",
                    "customer_id": "C-2077",
                    "title": "Charged twice for November renewal",
                    "body": (
                        "I can see two separate $49 subscription charges on 1 Nov. "
                        "Please remove the duplicate."
                    ),
                    "status": "open",
                    "priority": "high",
                    "category": "billing",
                    "tier": 1,
                    "created_at": "2025-11-02T09:15:00Z",
                    "updated_at": "2025-11-02T09:15:00Z",
                },
                {
                    "id": "T-5003",
                    "customer_id": "C-2077",
                    "title": "Invoice still shows storage add-on",
                    "body": "Can you explain the extra storage line item on the invoice?",
                    "status": "pending",
                    "priority": "normal",
                    "category": "billing",
                    "tier": 1,
                    "created_at": "2025-11-02T09:20:00Z",
                    "updated_at": "2025-11-02T09:20:00Z",
                },
                {
                    "id": "T-5004",
                    "customer_id": "C-2078",
                    "title": "Possible duplicate renewal",
                    "body": "I want to confirm whether one of these charges is pending only.",
                    "status": "closed",
                    "priority": "normal",
                    "category": "billing",
                    "tier": 1,
                    "created_at": "2025-10-01T11:15:00Z",
                    "updated_at": "2025-10-01T13:15:00Z",
                    "resolution": "Pending authorization only; no refund needed.",
                },
            ],
        )
        session.flush()
    elif task_id == "saas_hard":
        _seed_customers(
            session,
            [
                {
                    "id": "C-9001",
                    "name": "Alice Corp",
                    "email": "billing@alicecorp.com",
                    "company": "Alice Corp",
                    "plan": "enterprise",
                    "account_status": "active",
                    "is_vip": True,
                },
                {
                    "id": "C-9002",
                    "name": "Alyce Core",
                    "email": "ops@alycecore.com",
                    "company": "Alyce Core",
                    "plan": "enterprise",
                    "account_status": "active",
                    "is_vip": False,
                },
                {
                    "id": "C-9010",
                    "name": "Red Maple Ventures",
                    "email": "finance@redmaple.vc",
                    "company": "Red Maple Ventures",
                    "plan": "enterprise",
                    "account_status": "active",
                    "is_vip": False,
                },
            ],
        )
        _seed_transactions(
            session,
            [
                {
                    "id": "TX-9800",
                    "customer_id": "C-9001",
                    "amount": 499.0,
                    "currency": "USD",
                    "description": "Enterprise platform monthly subscription - February",
                    "payment_method": "wire_9901",
                    "created_at": "2026-02-01T06:00:00Z",
                    "status": "charged",
                },
                {
                    "id": "TX-9801",
                    "customer_id": "C-9001",
                    "amount": 499.0,
                    "currency": "USD",
                    "description": "Enterprise platform monthly subscription - March",
                    "payment_method": "wire_9901",
                    "created_at": "2026-03-01T06:00:00Z",
                    "status": "charged",
                },
                {
                    "id": "TX-9802",
                    "customer_id": "C-9001",
                    "amount": 499.0,
                    "currency": "USD",
                    "description": "Enterprise platform monthly subscription - March duplicate retry",
                    "payment_method": "wire_9901",
                    "created_at": "2026-03-01T06:03:00Z",
                    "status": "charged",
                },
                {
                    "id": "TX-9803",
                    "customer_id": "C-9001",
                    "amount": 120.0,
                    "currency": "USD",
                    "description": "Additional sandbox seats",
                    "payment_method": "wire_9901",
                    "created_at": "2026-03-02T14:00:00Z",
                    "status": "charged",
                },
                {
                    "id": "TX-9810",
                    "customer_id": "C-9002",
                    "amount": 499.0,
                    "currency": "USD",
                    "description": "Enterprise platform monthly subscription - March",
                    "payment_method": "wire_2231",
                    "created_at": "2026-03-01T06:00:00Z",
                    "status": "charged",
                },
            ],
        )
        _seed_tickets(
            session,
            [
                {
                    "id": "T-8001",
                    "customer_id": "C-9001",
                    "title": "Suspicious duplicate billing activity",
                    "body": (
                        "We noticed an unexpected second enterprise billing event and want "
                        "fraud review before month-end close."
                    ),
                    "status": "open",
                    "priority": "urgent",
                    "category": "fraud",
                    "tier": 1,
                    "created_at": "2026-03-03T08:10:00Z",
                    "updated_at": "2026-03-03T08:10:00Z",
                },
                {
                    "id": "T-8002",
                    "customer_id": "C-9001",
                    "title": "Duplicate March subscription charge",
                    "body": (
                        "Our AP team sees two $499 March subscription charges and needs the "
                        "duplicate reversed."
                    ),
                    "status": "open",
                    "priority": "high",
                    "category": "billing",
                    "tier": 1,
                    "created_at": "2026-03-03T08:25:00Z",
                    "updated_at": "2026-03-03T08:25:00Z",
                },
                {
                    "id": "T-8003",
                    "customer_id": "C-9001",
                    "title": "Sandbox seat invoice clarification",
                    "body": "Please confirm whether the sandbox seat add-on is expected.",
                    "status": "pending",
                    "priority": "normal",
                    "category": "billing",
                    "tier": 1,
                    "created_at": "2026-03-02T15:00:00Z",
                    "updated_at": "2026-03-02T15:00:00Z",
                },
                {
                    "id": "T-8010",
                    "customer_id": "C-9002",
                    "title": "Possible double billing on enterprise account",
                    "body": "Can you confirm we were only billed once this cycle?",
                    "status": "open",
                    "priority": "high",
                    "category": "billing",
                    "tier": 1,
                    "created_at": "2026-03-03T09:10:00Z",
                    "updated_at": "2026-03-03T09:10:00Z",
                },
                {
                    "id": "T-8020",
                    "customer_id": "C-9010",
                    "title": "Escalation request for procurement review",
                    "body": "Please route our contract amendment request to procurement.",
                    "status": "open",
                    "priority": "normal",
                    "category": "general",
                    "tier": 1,
                    "created_at": "2026-03-01T12:30:00Z",
                    "updated_at": "2026-03-01T12:30:00Z",
                },
            ],
        )
        session.flush()
    else:
        raise ValueError(f"Unknown task_id: {task_id}")

    return {"task_id": task_id}
