"\"\"\"Legal tool argument schemas.\"\"\""

from pydantic import BaseModel, Field


class GetContractSectionArgs(BaseModel):
    """Retrieve a named section or all clauses from a contract."""

    contract_id: str = Field(..., description="Contract ID e.g. NDA-001")
    section: str = Field(default="all", description="Clause type to retrieve, or 'all' for every clause")


class ExtractClauseArgs(BaseModel):
    """Extract a specific clause type from a contract for detailed review."""

    contract_id: str = Field(..., description="Contract ID")
    clause_type: str = Field(
        ...,
        description="Clause type: termination | payment | indemnity | liability | confidentiality | obligations",
    )


class FlagRiskArgs(BaseModel):
    """Flag a clause as carrying legal risk for the memo."""

    clause_id: str = Field(..., description="Clause ID to flag e.g. NDA-001-TERM")
    risk_level: str = Field(..., description="Risk level: low | medium | high")
    description: str = Field(..., description="Description of the risk")


class GetStandardTermsArgs(BaseModel):
    """Retrieve the standard template for a given clause type to use as a reference."""

    clause_type: str = Field(..., description="Clause type to get standard terms for")


class CompareClauseArgs(BaseModel):
    """Compare a contract clause against the standard terms for that clause type."""

    clause_id: str = Field(..., description="Clause ID from the contract")
    standard_clause_type: str = Field(..., description="Clause type to compare against")


class AddMemoNoteArgs(BaseModel):
    """Add a note to the contract review memo under a named section."""

    contract_id: str = Field(..., description="Contract ID this note applies to")
    section: str = Field(..., description="Memo section e.g. termination, risk_summary, recommendations")
    note: str = Field(..., description="Note text to add")


class FinalizeMemoArgs(BaseModel):
    """Finalize the review memo and complete the contract review. Ends the episode."""

    contract_id: str = Field(..., description="Contract ID being finalized")
    summary: str = Field(..., description="Executive summary of the review findings")
