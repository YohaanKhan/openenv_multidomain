from domains.hr.schema import Benefit, Employee, LeaveRequest, Policy
from domains.hr.tools.definitions import (
    CheckLeaveBalanceArgs,
    CloseHRRequestArgs,
    FileLeaveRequestArgs,
    GetBenefitsSummaryArgs,
    GetEmployeeRecordArgs,
    LookupPolicyArgs,
    SendHRNotificationArgs,
)
from domains.hr.tools.implementation import (
    check_leave_balance,
    close_hr_request,
    file_leave_request,
    get_benefits_summary,
    get_employee_record,
    lookup_policy,
    send_hr_notification,
)


def _employee(employee_id: str = "E-101", leave_used: int = 5) -> Employee:
    return Employee(
        id=employee_id,
        name="Alex Doe",
        email="alex@example.com",
        department="engineering",
        role="manager",
        annual_leave_days=20,
        leave_used=leave_used,
        salary=120000.0,
    )


def test_lookup_policy_happy_path(session):
    session.add(
        Policy(
            id="P-1",
            topic="annual_leave",
            title="Annual Leave Policy",
            content="Employees receive annual leave each calendar year.",
            version="2.0",
        )
    )
    session.flush()

    result = lookup_policy(LookupPolicyArgs(topic="annual_leave"), session)

    assert "Matching policies:" in result
    assert "Annual Leave Policy" in result


def test_lookup_policy_not_found(session):
    result = lookup_policy(LookupPolicyArgs(topic="payroll"), session)
    assert "No policy found" in result


def test_get_employee_record_happy_path(session):
    session.add(_employee())
    session.flush()

    result = get_employee_record(GetEmployeeRecordArgs(employee_id="E-101"), session)

    assert "Alex Doe" in result
    assert "Leave remaining: 15" in result


def test_get_employee_record_not_found(session):
    result = get_employee_record(GetEmployeeRecordArgs(employee_id="E-404"), session)
    assert "No employee found" in result


def test_check_leave_balance_happy_path(session):
    session.add(_employee())
    session.flush()

    result = check_leave_balance(
        CheckLeaveBalanceArgs(employee_id="E-101", leave_type="annual"),
        session,
    )

    assert "15 days available" in result


def test_check_leave_balance_not_found(session):
    result = check_leave_balance(
        CheckLeaveBalanceArgs(employee_id="E-404", leave_type="annual"),
        session,
    )
    assert "No employee found" in result


def test_file_leave_request_returns_ref_number(session):
    session.add(_employee(employee_id="E-202", leave_used=3))
    session.flush()

    result = file_leave_request(
        FileLeaveRequestArgs(
            employee_id="E-202",
            leave_type="annual",
            start_date="2024-07-15",
            end_date="2024-07-19",
            days_requested=5,
            reason="Family trip",
        ),
        session,
    )

    request = session.query(LeaveRequest).filter(LeaveRequest.employee_id == "E-202").one()
    assert "Reference number:" in result
    assert "LR-" in result
    assert request.ref_number in result
    assert request.status == "pending"


def test_file_leave_request_insufficient_balance(session):
    session.add(_employee(employee_id="E-202", leave_used=18))
    session.flush()

    result = file_leave_request(
        FileLeaveRequestArgs(
            employee_id="E-202",
            leave_type="annual",
            start_date="2024-07-15",
            end_date="2024-07-19",
            days_requested=5,
            reason="Trip",
        ),
        session,
    )

    assert any(word in result.lower() for word in ["insufficient", "not enough", "only"])
    assert session.query(LeaveRequest).count() == 0


def test_file_leave_request_not_found(session):
    result = file_leave_request(
        FileLeaveRequestArgs(
            employee_id="E-404",
            leave_type="annual",
            start_date="2024-07-15",
            end_date="2024-07-19",
            days_requested=1,
            reason="Trip",
        ),
        session,
    )
    assert "No employee found" in result


def test_get_benefits_summary_happy_path(session):
    session.add(_employee())
    session.add(
        Benefit(
            id="B-1",
            employee_id="E-101",
            benefit_type="health",
            value=500.0,
            description="Health insurance",
        )
    )
    session.flush()

    result = get_benefits_summary(GetBenefitsSummaryArgs(employee_id="E-101"), session)

    assert "Benefits summary:" in result
    assert "health" in result


def test_get_benefits_summary_not_found(session):
    result = get_benefits_summary(GetBenefitsSummaryArgs(employee_id="E-101"), session)
    assert "No benefits found" in result


def test_send_hr_notification_returns_confirmation(session):
    result = send_hr_notification(
        SendHRNotificationArgs(
            employee_id="E-101",
            recipient="manager",
            message="Leave request submitted for review.",
        ),
        session,
    )

    assert "Notification sent" in result
    assert "manager" in result


def test_close_hr_request_not_found(session):
    result = close_hr_request(
        CloseHRRequestArgs(request_ref="LR-FAKE", resolution="x"),
        session,
    )
    assert "No request found" in result


def test_close_hr_request_result_contains_closed(session):
    session.add(_employee())
    request = LeaveRequest(
        ref_number="LR-2024-TEST",
        employee_id="E-101",
        leave_type="annual",
        start_date="2024-07-15",
        end_date="2024-07-19",
        days_requested=5,
        status="pending",
        reason="Trip",
    )
    session.add(request)
    session.flush()

    result = close_hr_request(
        CloseHRRequestArgs(request_ref="LR-2024-TEST", resolution="done"),
        session,
    )

    refreshed = (
        session.query(LeaveRequest)
        .filter(LeaveRequest.ref_number == "LR-2024-TEST")
        .one()
    )
    assert "closed" in result.lower()
    assert refreshed.status == "approved"
