"\"\"\"HR tool implementations.\"\"\""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

try:
    from ..schema import Employee, Policy, LeaveRequest, Benefit
    from .definitions import (
        CheckLeaveBalanceArgs,
        CloseHRRequestArgs,
        FileLeaveRequestArgs,
        GetBenefitsSummaryArgs,
        GetEmployeeRecordArgs,
        LookupPolicyArgs,
        SendHRNotificationArgs,
    )
except ImportError:
    from domains.hr.schema import Employee, Policy, LeaveRequest, Benefit
    from domains.hr.tools.definitions import (
        CheckLeaveBalanceArgs,
        CloseHRRequestArgs,
        FileLeaveRequestArgs,
        GetBenefitsSummaryArgs,
        GetEmployeeRecordArgs,
        LookupPolicyArgs,
        SendHRNotificationArgs,
    )


def lookup_policy(args: LookupPolicyArgs, session: Session) -> str:
    """Search for policies matching the topic keyword."""
    keyword = f"%{args.topic}%"
    matches = (
        session.query(Policy)
        .filter(
            (Policy.topic.ilike(keyword))
            | (Policy.title.ilike(keyword))
        )
        .order_by(Policy.id)
        .all()
    )
    if not matches:
        return f"No policy found for topic '{args.topic}'."
    lines = []
    for policy in matches:
        snippet = policy.content[:200]
        lines.append(
            f"{policy.id}: {policy.title} (v{policy.version}) — {snippet}"
        )
    return "Matching policies:\n" + "\n".join(lines)


def get_employee_record(args: GetEmployeeRecordArgs, session: Session) -> str:
    """Return employee data, leave balance, and role info."""
    employee = session.get(Employee, args.employee_id)
    if not employee:
        return f"No employee found with ID '{args.employee_id}'."
    remaining = employee.annual_leave_days - employee.leave_used
    return (
        f"{employee.name} ({employee.id})\n"
        f"Department: {employee.department}\n"
        f"Role: {employee.role}\n"
        f"Annual leave days: {employee.annual_leave_days}\n"
        f"Leave used: {employee.leave_used}\n"
        f"Leave remaining: {remaining}"
    )


def check_leave_balance(args: CheckLeaveBalanceArgs, session: Session) -> str:
    """Report leave availability for the requested leave type."""
    employee = session.get(Employee, args.employee_id)
    if not employee:
        return f"No employee found with ID '{args.employee_id}'."
    leave_type = args.leave_type.lower()
    if leave_type == "annual":
        remaining = employee.annual_leave_days - employee.leave_used
    elif leave_type == "sick":
        remaining = 10
    else:  # unpaid
        remaining = float("inf")
    available = f"{remaining if remaining != float('inf') else 'unlimited'}"
    return (
        f"Employee {employee.id}: {leave_type} leave — {available} days available."
    )


def file_leave_request(args: FileLeaveRequestArgs, session: Session) -> str:
    """Record a leave request if balances allow."""
    employee = session.get(Employee, args.employee_id)
    if not employee:
        return f"No employee found with ID '{args.employee_id}'."
    leave_type = args.leave_type.lower()
    if leave_type == "annual":
        remaining = employee.annual_leave_days - employee.leave_used
        if args.days_requested > remaining:
            return (
                f"Insufficient annual leave balance. Only {remaining} days remain."
            )
    ref_number = f"LR-{datetime.now().year}-{str(uuid4())[:4].upper()}"
    request = LeaveRequest(
        ref_number=ref_number,
        employee_id=employee.id,
        leave_type=args.leave_type,
        start_date=args.start_date,
        end_date=args.end_date,
        days_requested=args.days_requested,
        status="pending",
        reason=args.reason,
    )
    session.add(request)
    session.flush()
    return (
        f"Leave request filed. Reference number: {ref_number}. Status: pending."
    )


def get_benefits_summary(args: GetBenefitsSummaryArgs, session: Session) -> str:
    """List benefits associated with the employee."""
    benefits = (
        session.query(Benefit)
        .filter(Benefit.employee_id == args.employee_id)
        .order_by(Benefit.benefit_type)
        .all()
    )
    if not benefits:
        return f"No benefits found for employee '{args.employee_id}'."
    lines = [
        f"{benefit.benefit_type}: ${benefit.value:.2f} — {benefit.description}"
        for benefit in benefits
    ]
    return "Benefits summary:\n" + "\n".join(lines)


def send_hr_notification(args: SendHRNotificationArgs, session: Session) -> str:
    """Acknowledge a notification dispatch."""
    snippet = args.message[:80]
    return (
        f"Notification sent to {args.recipient} for employee "
        f"{args.employee_id}: '{snippet}...'"
    )


def close_hr_request(args: CloseHRRequestArgs, session: Session) -> str:
    """Resolve a leave request and mark it closed."""
    request = (
        session.query(LeaveRequest)
        .filter(LeaveRequest.ref_number == args.request_ref)
        .one_or_none()
    )
    if not request:
        return f"No request found with reference '{args.request_ref}'."
    request.status = "approved"
    session.flush()
    return f"Request {args.request_ref} closed. Resolution: {args.resolution}"
