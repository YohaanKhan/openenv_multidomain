"""Legal task definitions and deterministic seed data."""

from sqlalchemy.orm import Session

from domains.legal import schema

TASKS = [
    {
        "id": "legal_easy",
        "name": "NDA Termination Clause Review",
        "difficulty": "easy",
        "max_steps": 6,
        "description": (
            "Review contract NDA-001. Extract the termination clause, "
            "add it to the memo under the 'termination' section, "
            "then finalize the memo."
        ),
    },
    {
        "id": "legal_medium",
        "name": "Vendor Contract Payment Terms",
        "difficulty": "medium",
        "max_steps": 12,
        "description": (
            "Review vendor contract VC-001. Extract the payment terms clause, "
            "compare it against the standard payment terms, "
            "flag any deviation with the appropriate risk level, "
            "add a note to the memo about your finding, "
            "then finalize the memo."
        ),
    },
    {
        "id": "legal_hard",
        "name": "SaaS Agreement Multi-Party Review with Conflicting Liability Caps",
        "difficulty": "hard",
        "max_steps": 20,
        "description": (
            "Review SaaS agreement SA-001 (3 parties with conflicting data). "
            "WARNING: Main contract (Section 4.2) specifies LIABILITY CAP A. "
            "Schedule A (Addendum) specifies LIABILITY CAP B (different amount). "
            "Schedule B (Data DPA) specifies LIABILITY CAP C (unlimited for data breaches). "
            "NO explicit conflict resolution clause exists. "
            "You must: (1) Extract all three liability clauses; (2) Compare each against standards; "
            "(3) Flag the CONFLICT with HIGH risk; (4) Add memo explaining the issue; "
            "(5) Recommend specific precedence language; (6) Finalize memo. "
            "Missing the conflict = major deduction."
        ),
    },
]


def seed(task_id: str, session: Session) -> dict[str, str]:
    if task_id == "legal_easy":
        session.merge(
            schema.Contract(id="NDA-001", title="Mutual NDA", contract_type="nda", parties="Party A, Party B")
        )
        session.merge(
            schema.Clause(
                id="NDA-001-TERM",
                contract_id="NDA-001",
                clause_type="termination",
                party="all",
                content="Either party may terminate with 30 days notice.",
                is_standard=True,
            )
        )
    elif task_id == "legal_medium":
        session.merge(
            schema.Contract(
                id="VC-001",
                title="Vendor Agreement",
                contract_type="vendor",
                parties="Vendor LLC, Buyer Inc.",
            )
        )
        session.merge(
            schema.Clause(
                id="VC-001-PAY",
                contract_id="VC-001",
                clause_type="payment",
                party="vendor",
                content="Payment due within 90 days of invoice.",
                is_standard=False,
            )
        )
        session.merge(
            schema.StandardTerm(
                id="STD-PAY",
                clause_type="payment",
                content="Payment due within 30 days of invoice.",
                notes="Shorter payment windows reduce working capital risk.",
            )
        )
    elif task_id == "legal_hard":
        session.merge(
            schema.Contract(
                id="SA-001",
                title="SaaS Multi-Tenant Agreement (3-Party with Conflicting Schedules)",
                contract_type="saas_agreement",
                parties="Provider Corp, Customer A, Customer B",
            )
        )
        clauses = [
            # Main contract - Section 4.2
            schema.Clause(
                id="SA-001-LIABILITY-MAIN",
                contract_id="SA-001",
                clause_type="liability",
                party="all",
                content="[SECTION 4.2] Liability cap is 3x annual fees paid in the 12 months preceding the claim. Applies to all claims.",
                is_standard=False,
            ),
            # Schedule A (Addendum) - different cap
            schema.Clause(
                id="SA-001-LIABILITY-SCHED-A",
                contract_id="SA-001",
                clause_type="liability",
                party="all",
                content="[SCHEDULE A - Addendum, signed 2026-02-15] Liability cap is $50,000 flat for all claims. Overrides prior understanding.",
                is_standard=False,
            ),
            # Schedule B (Data Processing Addendum) - unlimited for data breaches
            schema.Clause(
                id="SA-001-LIABILITY-SCHED-B",
                contract_id="SA-001",
                clause_type="liability",
                party="all",
                content="[SCHEDULE B - Data Processing Addendum (GDPR), signed 2026-03-01] Liability is UNLIMITED for data breaches and personal data violations. Regular operations capped at 3x fees.",
                is_standard=False,
            ),
            # NO conflict resolution clause
            schema.Clause(
                id="SA-001-NO-PRECEDENCE",
                contract_id="SA-001",
                clause_type="precedence",
                party="all",
                content="[MISSING CLAUSE] This agreement does not specify which schedule or section takes precedence in case of conflict.",
                is_standard=False,
            ),
            schema.Clause(
                id="SA-001-CONF",
                contract_id="SA-001",
                clause_type="confidentiality",
                party="all",
                content="Each party must protect confidential information with industry-standard measures.",
                is_standard=True,
            ),
            schema.Clause(
                id="SA-001-INDEMNITY",
                contract_id="SA-001",
                clause_type="indemnity",
                party="customer",
                content="Indemnity capped at 2x annual contract value.",
                is_standard=False,
            ),
        ]
        for clause in clauses:
            session.merge(clause)
        standard_terms = [
            schema.StandardTerm(
                id="STD-LIABILITY",
                clause_type="liability",
                content="Standard: Liability cap is 1x annual fees OR explicit dollar amount. Data breach liability should align with GDPR.",
                notes="Conflicting liability caps across schedules create enforceability risk.",
            ),
            schema.StandardTerm(
                id="STD-INDEMNITY",
                clause_type="indemnity",
                content="Indemnity capped at 2x annual contract value.",
                notes="Higher caps protect the provider.",
            ),
        ]
        for term in standard_terms:
            session.merge(term)
    else:
        raise ValueError(f"Unknown task_id: {task_id}")
    session.flush()
    return {"task_id": task_id}
