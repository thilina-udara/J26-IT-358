"""Standalone governance checks; all identities and evidence are fictional."""
import sqlite3
import pytest
from fastapi import HTTPException
from app.schemas.reference_governance import ReviewerRegistration, RubricRegistration
from app.services.reference_governance import ReferenceStore
from app.services.expert_reviews import create_case


def test_immutable_reviewer_registration(tmp_path):
    store = ReferenceStore(tmp_path / "fictional.sqlite3")
    reviewer = ReviewerRegistration(reviewer_id="fictional-reviewer",
        credential_evidence="fictional-evidence", agricultural_role="fictional-role",
        organization="fictional-organization")
    assert store.record("reviewers", reviewer, "fictional-admin")["training_eligible"] is False
    with pytest.raises(HTTPException) as error:
        store.record("reviewers", reviewer, "fictional-admin")
    assert error.value.status_code == 409
    with pytest.raises(sqlite3.IntegrityError):
        with store.connection() as db:
            db.execute("DELETE FROM reviewers")
    with store.connection() as db:
        assert store.require(db, "reviewers", "fictional-reviewer")["verified"] is False


def test_rubric_approval_requires_evidence(tmp_path):
    store = ReferenceStore(tmp_path / "fictional.sqlite3")
    rubric = RubricRegistration(rubric_version="fictional-v1", rubric_text="Fictional rubric", approved=True)
    with pytest.raises(HTTPException) as error:
        store.record("rubrics", rubric, "fictional-admin")
    assert error.value.status_code == 422
    rubric.approval_evidence = "fictional-attestation"
    assert store.record("rubrics", rubric, "fictional-admin")["training_eligible"] is False


def test_private_cases_cannot_be_exported():
    with pytest.raises(ValueError):
        create_case({"indicators": {"status": "suppressed_or_insufficient"}})
