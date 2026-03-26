from domains.legal.schema import Clause, Contract, MemoNote, StandardTerm
from domains.legal.tools.definitions import (
    AddMemoNoteArgs,
    CompareClauseArgs,
    ExtractClauseArgs,
    FinalizeMemoArgs,
    FlagRiskArgs,
    GetContractSectionArgs,
    GetStandardTermsArgs,
)
from domains.legal.tools.implementation import (
    add_memo_note,
    compare_clause,
    extract_clause,
    finalize_memo,
    flag_risk,
    get_contract_section,
    get_standard_terms,
)


def _contract(contract_id: str = "NDA-001") -> Contract:
    return Contract(
        id=contract_id,
        title="Mutual NDA",
        contract_type="nda",
        parties="A Corp; B Corp",
        status="under_review",
    )


def _clause(
    clause_id: str = "NDA-001-TERM",
    contract_id: str = "NDA-001",
    clause_type: str = "termination",
    is_standard: bool = True,
) -> Clause:
    return Clause(
        id=clause_id,
        contract_id=contract_id,
        clause_type=clause_type,
        party="all",
        content="Either party may terminate this agreement with 30 days notice.",
        is_standard=is_standard,
        risk_level="none",
    )


def test_get_contract_section_happy_path(session):
    session.add(_contract())
    session.add(_clause())
    session.flush()

    result = get_contract_section(
        GetContractSectionArgs(contract_id="NDA-001", section="termination"),
        session,
    )

    assert "NDA-001-TERM" in result
    assert "termination" in result


def test_get_contract_section_not_found_contract(session):
    result = get_contract_section(
        GetContractSectionArgs(contract_id="NDA-404", section="all"),
        session,
    )
    assert "not found" in result.lower()


def test_extract_clause_happy_path(session):
    session.add(_contract())
    session.add(_clause())
    session.flush()

    result = extract_clause(
        ExtractClauseArgs(contract_id="NDA-001", clause_type="termination"),
        session,
    )

    assert "NDA-001-TERM" in result
    assert "is_standard=True" in result


def test_extract_clause_not_found(session):
    result = extract_clause(
        ExtractClauseArgs(contract_id="NDA-001", clause_type="payment"),
        session,
    )
    assert "No payment clause found" in result


def test_flag_risk_updates_db(session):
    session.add(_contract())
    session.add(_clause())
    session.flush()

    result = flag_risk(
        FlagRiskArgs(
            clause_id="NDA-001-TERM",
            risk_level="high",
            description="Termination is too broad.",
        ),
        session,
    )

    clause = session.get(Clause, "NDA-001-TERM")
    assert "flagged as high risk" in result
    assert clause.risk_level == "high"


def test_flag_risk_not_found(session):
    result = flag_risk(
        FlagRiskArgs(clause_id="MISSING", risk_level="high", description="x"),
        session,
    )
    assert "not found" in result.lower()


def test_get_standard_terms_happy_path(session):
    session.add(
        StandardTerm(
            id="STD-PAY",
            clause_type="payment",
            content="Invoices are due within 30 days.",
            notes="Standard payment language.",
        )
    )
    session.flush()

    result = get_standard_terms(GetStandardTermsArgs(clause_type="payment"), session)

    assert "Invoices are due within 30 days." in result
    assert "Notes:" in result


def test_get_standard_terms_not_found(session):
    result = get_standard_terms(GetStandardTermsArgs(clause_type="payment"), session)
    assert "No standard terms found" in result


def test_compare_clause_shows_deviation(session):
    session.add(_contract("VC-001"))
    session.add(
        Clause(
            id="VC-001-PAY",
            contract_id="VC-001",
            clause_type="payment",
            party="vendor",
            content="Customer must pay within 7 days.",
            is_standard=False,
            risk_level="none",
        )
    )
    session.add(
        StandardTerm(
            id="STD-PAY",
            clause_type="payment",
            content="Invoices are due within 30 days.",
            notes="Net 30 standard.",
        )
    )
    session.flush()

    result = compare_clause(
        CompareClauseArgs(clause_id="VC-001-PAY", standard_clause_type="payment"),
        session,
    )

    assert "Standard:" in result
    assert "No" in result


def test_compare_clause_not_found(session):
    result = compare_clause(
        CompareClauseArgs(clause_id="MISSING", standard_clause_type="payment"),
        session,
    )
    assert "not found" in result.lower()


def test_add_memo_note_happy_path(session):
    session.add(_contract())
    session.flush()

    result = add_memo_note(
        AddMemoNoteArgs(
            contract_id="NDA-001",
            section="termination",
            note="Termination clause is acceptable.",
        ),
        session,
    )

    note = session.query(MemoNote).filter(MemoNote.contract_id == "NDA-001").one()
    assert "Note added" in result
    assert note.section == "termination"


def test_add_memo_note_not_found(session):
    result = add_memo_note(
        AddMemoNoteArgs(contract_id="NDA-404", section="risk", note="Missing"),
        session,
    )
    assert "not found" in result.lower()


def test_finalize_memo_requires_notes(session):
    session.add(_contract())
    session.flush()

    result = finalize_memo(
        FinalizeMemoArgs(contract_id="NDA-001", summary="Done"),
        session,
    )

    assert "Memo is empty" in result


def test_finalize_memo_result_contains_finalized(session):
    session.add(_contract())
    session.add(MemoNote(contract_id="NDA-001", section="summary", note="Reviewed"))
    session.flush()

    result = finalize_memo(
        FinalizeMemoArgs(contract_id="NDA-001", summary="All good"),
        session,
    )

    contract = session.get(Contract, "NDA-001")
    assert "finalized" in result.lower()
    assert contract.status == "reviewed"
