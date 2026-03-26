"\"\"\"HR tool argument schemas.\"\"\""

from pydantic import BaseModel, Field


class LookupPolicyArgs(BaseModel):
    """Search HR policy documents by topic keyword."""

    topic: str = Field(
        ...,
        description="Policy topic to search e.g. annual_leave, payroll, benefits, overtime",
    )


class GetEmployeeRecordArgs(BaseModel):
    """Retrieve an employee's full record including leave balance and role."""

    employee_id: str = Field(..., description="Employee ID e.g. E-101")


class CheckLeaveBalanceArgs(BaseModel):
    """Check how many leave days an employee has available."""

    employee_id: str = Field(..., description="Employee ID to check")
    leave_type: str = Field(..., description="Leave type: annual | sick | unpaid")


class FileLeaveRequestArgs(BaseModel):
    """File a leave request for an employee. Returns a reference number on success."""

    employee_id: str = Field(..., description="Employee ID filing the request")
    leave_type: str = Field(..., description="Leave type: annual | sick | unpaid")
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format")
    days_requested: int = Field(
        ...,
        description="Number of working days requested",
        gt=0,
    )
    reason: str = Field(default="", description="Optional reason for the request")


class GetBenefitsSummaryArgs(BaseModel):
    """Retrieve a summary of all benefits for an employee."""

    employee_id: str = Field(..., description="Employee ID to get benefits for")


class SendHRNotificationArgs(BaseModel):
    """Send an HR notification to an employee or their manager."""

    employee_id: str = Field(..., description="Employee ID involved")
    recipient: str = Field(
        ...,
        description="Who to notify: employee | manager | hr_team",
    )
    message: str = Field(..., description="Notification message text")


class CloseHRRequestArgs(BaseModel):
    """Close and resolve an HR request or dispute. Ends the episode."""

    request_ref: str = Field(
        ...,
        description="Reference number of the request e.g. LR-2024-0042",
    )
    resolution: str = Field(..., description="How the request was resolved")
