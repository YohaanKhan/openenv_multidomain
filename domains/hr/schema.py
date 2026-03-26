"""HR domain ORM schema (shared Base with SaaS)."""

from sqlalchemy import Column, String, Float, Integer, Text, Boolean
from sqlalchemy import Date, ForeignKey
from sqlalchemy.orm import relationship

from server.utils.db import Base


class Employee(Base):
    __tablename__ = "hr_employees"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    department = Column(String, nullable=False, default="general")
    role = Column(String, nullable=False, default="employee")
    annual_leave_days = Column(Integer, nullable=False, default=20)
    leave_used = Column(Integer, nullable=False, default=0)
    salary = Column(Float, nullable=False, default=0.0)

    leave_requests = relationship("LeaveRequest", back_populates="employee")


class Policy(Base):
    __tablename__ = "hr_policies"

    id = Column(String, primary_key=True)
    topic = Column(String, nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    version = Column(String, nullable=False, default="1.0")


class LeaveRequest(Base):
    __tablename__ = "hr_leave_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ref_number = Column(String, nullable=False, unique=True)
    employee_id = Column(String, ForeignKey("hr_employees.id"), nullable=False)
    leave_type = Column(String, nullable=False)
    start_date = Column(String, nullable=False)
    end_date = Column(String, nullable=False)
    days_requested = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="pending")
    reason = Column(String, nullable=False, default="")

    employee = relationship("Employee", back_populates="leave_requests")


class Benefit(Base):
    __tablename__ = "hr_benefits"

    id = Column(String, primary_key=True)
    employee_id = Column(String, ForeignKey("hr_employees.id"), nullable=False)
    benefit_type = Column(String, nullable=False)
    value = Column(Float, nullable=False, default=0.0)
    description = Column(String, nullable=False, default="")
