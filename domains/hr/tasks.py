"\"\"\"HR task definitions and deterministic seed data.\"\"\""

from sqlalchemy.orm import Session

from domains.hr import schema

TASKS = [
    {
        "id": "hr_easy",
        "name": "Leave Entitlement Query",
        "difficulty": "easy",
        "max_steps": 5,
        "description": (
            "New hire E-101 (Priya Sharma) wants to know their annual leave entitlement. "
            "Look up the annual leave policy and close the request with an explanation."
        ),
    },
    {
        "id": "hr_medium",
        "name": "Leave Request Filing",
        "difficulty": "medium",
        "max_steps": 12,
        "description": (
            "Employee E-202 (James Okafor) wants to take 5 days annual leave "
            "from 2024-07-15 to 2024-07-19. "
            "Check their leave balance (must be >= 5 days), file the request, "
            "notify their manager, then close the request."
        ),
    },
    {
        "id": "hr_hard",
        "name": "Payroll Deduction Dispute with Conflicting Policies",
        "difficulty": "hard",
        "max_steps": 18,
        "description": (
            "Employee E-303 (Chen Wei) disputes an unexpected payroll deduction. "
            "CRITICAL: The company handbook (OLD policy) and the recent amendment (NEW policy) "
            "conflict on pension deduction rates. You must identify BOTH policies, determine which "
            "is currently active, then correctly explain the deduction to the employee. "
            "Retrieve: (1) employee record; (2) BOTH payroll policies; (3) employee benefits; "
            "file a dispute with correct policy reference; send notification with reference number; "
            "close the dispute. Wrong policy reference = partial credit."
        ),
    },
]


def seed(task_id: str, session: Session) -> dict[str, str]:
    if task_id == "hr_easy":
        session.merge(
            schema.Employee(
                id="E-101", name="Priya Sharma", email="priya@company.com", annual_leave_days=20, leave_used=0
            )
        )
        session.merge(
            schema.Policy(
                id="POL-HR-001",
                topic="annual_leave",
                title="Annual Leave Policy",
                content="Employees are entitled to 20 days of annual leave per fiscal year.",
            )
        )
    elif task_id == "hr_medium":
        session.merge(
            schema.Employee(
                id="E-202",
                name="James Okafor",
                email="james@company.com",
                annual_leave_days=20,
                leave_used=10,
            )
        )
    elif task_id == "hr_hard":
        session.merge(
            schema.Employee(
                id="E-303",
                name="Chen Wei",
                email="chen@company.com",
                annual_leave_days=20,
                leave_used=5,
            )
        )
        # OLD policy (company handbook, effective until 2026-02-28)
        session.merge(
            schema.Policy(
                id="POL-HR-002-OLD",
                topic="payroll",
                title="Payroll Deduction Policy (Legacy - expires 2026-02-28)",
                content="Mandatory pension contribution is 10% of gross salary. Deducted monthly.",
            )
        )
        # NEW policy (effective 2026-03-01, CURRENT)
        session.merge(
            schema.Policy(
                id="POL-HR-002-NEW",
                topic="payroll",
                title="Payroll Deduction Policy (Current - effective 2026-03-01)",
                content="Mandatory pension contribution is 12% of gross salary effective March 2026 (increased from 10%). Deducted monthly.",
            )
        )
        session.merge(
            schema.Benefit(
                id="BEN-303-001",
                employee_id="E-303",
                benefit_type="pension",
                value=180.0,
                description="Mandatory pension contribution — deducted monthly at 12% rate (NEW policy effective 2026-03-01)",
            )
        )
    else:
        raise ValueError(f"Unknown task_id: {task_id}")

    session.flush()
    return {"task_id": task_id}
