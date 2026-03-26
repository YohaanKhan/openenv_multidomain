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
        "name": "SaaS Agreement Multi-Party Review",
        "difficulty": "hard",
        "max_steps": 20,
        "description": (
            "Review SaaS agreement SA-001 (3 parties). "
            "Extract all clauses, identify the two non-standard clauses "
            "(indemnity and liability), compare each against standard terms, "
            "flag both with correct risk levels (indemnity=high, liability=medium), "
            "add memo notes for each finding, then finalize."
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
                title="SaaS Multi-Tenant Agreement",
                contract_type="saas_agreement",
                parties="Provider Corp, Customer A, Customer B",
            )
        )
        clauses = [
            schema.Clause(
                id="SA-001-CONF",
                contract_id="SA-001",
                clause_type="confidentiality",
                party="all",
                content="Each party must protect confidential information with industry-standard measures.",
                is_standard=True,
            ),
            schema.Clause(
                id="SA-001-OBL",
                contract_id="SA-001",
                clause_type="obligations",
                party="provider",
                content="Provider agrees to maintain 99.99% uptime.",
                is_standard=True,
            ),
            schema.Clause(
                id="SA-001-INDEMNITY",
                contract_id="SA-001",
                clause_type="indemnity",
                party="customer",
                content="Indemnity capped at 1x annual contract value.",
                is_standard=False,
            ),
            schema.Clause(
                id="SA-001-LIABILITY",
                contract_id="SA-001",
                clause_type="liability",
                party="all",
                content="Liability exclusion applies to indirect damages only.",
                is_standard=False,
            ),
        ]
        for clause in clauses:
            session.merge(clause)
        standard_terms = [
            schema.StandardTerm(
                id="STD-TERM",
                clause_type="termination",
                content="Standard termination clause.",
                notes="Ensure notice periods are documented.",
            ),
            schema.StandardTerm(
                id="STD-INDEMNITY",
                clause_type="indemnity",
                content="Indemnity capped at 2x annual contract value.",
                notes="Higher caps protect the provider.",
            ),
            schema.StandardTerm(
                id="STD-LIABILITY",
                clause_type="liability",
                content="Liability exclusion applies to all consequential and indirect damages.",
                notes="Ensure liability caps are explicit.",
            ),
            schema.StandardTerm(
                id="STD-PAY",
                clause_type="payment",
                content="Payment due within 30 days of invoice.",
                notes="Shorter payment windows reduce working capital risk.",
            ),
        ]
        for term in standard_terms:
            session.merge(term)
    else:
        raise ValueError(f"Unknown task_id: {task_id}")
    session.flush()
    return {"task_id": task_id}
