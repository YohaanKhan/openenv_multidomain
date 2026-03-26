"\"\"\"Legal tool implementations working on structured clause data.\"\"\""

from __future__ import annotations

from sqlalchemy.orm import Session

try:
    from ..schema import Clause, Contract, StandardTerm, MemoNote
    from .definitions import (
        AddMemoNoteArgs,
        CompareClauseArgs,
        ExtractClauseArgs,
        FlagRiskArgs,
        FinalizeMemoArgs,
        GetContractSectionArgs,
        GetStandardTermsArgs,
    )
except ImportError:
    from domains.legal.schema import Clause, Contract, StandardTerm, MemoNote
    from domains.legal.tools.definitions import (
        AddMemoNoteArgs,
        CompareClauseArgs,
        ExtractClauseArgs,
        FlagRiskArgs,
        FinalizeMemoArgs,
        GetContractSectionArgs,
        GetStandardTermsArgs,
    )


def _format_clause_summary(clause: Clause) -> str:
    snippet = clause.content[:300]
    return (
        f"{clause.id} | {clause.clause_type} | party={clause.party} | "
        f"is_standard={clause.is_standard}\n{snippet}"
    )


def get_contract_section(args: GetContractSectionArgs, session: Session) -> str:
    """Retrieve clauses for the requested section or entire contract."""
    contract = session.get(Contract, args.contract_id)
    if not contract:
        return f"Contract '{args.contract_id}' not found."
    clauses = contract.clauses
    if args.section != "all":
        clauses = [c for c in clauses if c.clause_type == args.section]
    if not clauses:
        return f"No clauses found for section '{args.section}'."
    blocks = [_format_clause_summary(clause) for clause in clauses]
    return "\n\n".join(blocks)


def extract_clause(args: ExtractClauseArgs, session: Session) -> str:
    """Return the full text of a specific clause."""
    clause = (
        session.query(Clause)
        .filter(
            Clause.contract_id == args.contract_id,
            Clause.clause_type == args.clause_type,
        )
        .first()
    )
    if not clause:
        return f"No {args.clause_type} clause found in contract {args.contract_id}."
    return (
        f"{clause.id} | {clause.clause_type} | is_standard={clause.is_standard}\n"
        f"{clause.content}"
    )


def flag_risk(args: FlagRiskArgs, session: Session) -> str:
    """Mark a clause with a risk level."""
    clause = session.get(Clause, args.clause_id)
    if not clause:
        return f"Clause '{args.clause_id}' not found."
    level = args.risk_level.lower()
    if level not in ("low", "medium", "high"):
        return f"Invalid risk level '{args.risk_level}'."
    clause.risk_level = level
    session.flush()
    return f"Clause {args.clause_id} flagged as {level} risk. Note: {args.description}"


def get_standard_terms(args: GetStandardTermsArgs, session: Session) -> str:
    """Return the standard clause template for a clause type."""
    term = session.query(StandardTerm).filter(StandardTerm.clause_type == args.clause_type).first()
    if not term:
        return f"No standard terms found for clause type '{args.clause_type}'."
    return f"{term.content}\nNotes: {term.notes}"


def compare_clause(args: CompareClauseArgs, session: Session) -> str:
    """Compare a clause against its standard term."""
    clause = session.get(Clause, args.clause_id)
    if not clause:
        return f"Clause '{args.clause_id}' not found."
    term = session.query(StandardTerm).filter(StandardTerm.clause_type == args.standard_clause_type).first()
    if not term:
        return f"No standard terms found for clause type '{args.standard_clause_type}'."
    standard_flag = "Yes" if clause.is_standard else "No"
    return (
        f"Contract clause: {clause.content}\n"
        f"Standard terms: {term.content}\n"
        f"Standard: {standard_flag}\n"
        f"Notes: {term.notes}"
    )


def add_memo_note(args: AddMemoNoteArgs, session: Session) -> str:
    """Record a new memo note."""
    contract = session.get(Contract, args.contract_id)
    if not contract:
        return f"Contract '{args.contract_id}' not found."
    note = MemoNote(contract_id=args.contract_id, section=args.section, note=args.note)
    session.add(note)
    session.flush()
    return f"Note added to memo under '{args.section}'."


def finalize_memo(args: FinalizeMemoArgs, session: Session) -> str:
    """Finalize the memo, mark the contract reviewed."""
    contract = session.get(Contract, args.contract_id)
    if not contract:
        return f"Contract '{args.contract_id}' not found."
    notes = (
        session.query(MemoNote)
        .filter(MemoNote.contract_id == args.contract_id)
        .all()
    )
    if not notes:
        return f"Memo is empty for contract {args.contract_id}. Add notes before finalizing."
    contract.status = "reviewed"
    session.flush()
    return f"Memo finalized for contract {args.contract_id}. Summary: {args.summary}"
