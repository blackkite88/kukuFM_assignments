"""Unit tests covering retrieval, citation validation, language detection, and document drafting."""

from pathlib import Path

from src.draft import generate_document
from src.flow import CaseFile, detect_language
from src.retrieve import LegalChunk, LegalRetriever
from src.validator import (
    Citation,
    LegalAnswer,
    check_scope_and_escalation,
    validate_citations,
)


def test_language_detection():
    assert detect_language("Hello, my landlord has not returned my deposit.") == "english"
    assert detect_language("मकान मालिक ने मेरा किराया और डिपॉजिट नहीं दिया।") == "hindi"
    assert detect_language("Mera security deposit refund nahi mila, kya karoon?") == "hinglish"


def test_retriever_finds_relevant_sections():
    retriever = LegalRetriever()
    assert len(retriever.chunks) >= 15

    tenancy_results = retriever.retrieve("security deposit rent", top_k=2)
    assert len(tenancy_results) > 0
    assert any("Tenancy" in c.act or "11" in c.section for c in tenancy_results)

    wage_results = retriever.retrieve("unpaid wages salary delay deduction", top_k=2)
    assert len(wage_results) > 0
    assert any("Wages" in c.act for c in wage_results)

    consumer_results = retriever.retrieve("defective television refund product", top_k=2)
    assert len(consumer_results) > 0
    assert any("Consumer" in c.act for c in consumer_results)


def test_citation_validator_rejects_hallucinations():
    retrieved = [
        LegalChunk(
            act="Consumer Protection Act, 2019",
            section="Section 35",
            text="Manner in which complaint shall be made",
            source_url="https://consumeraffairs.gov.in",
        )
    ]
    valid_ans = LegalAnswer(
        answer="File via e-Daakhil",
        citations=[Citation(act="Consumer Protection Act, 2019", section="Section 35")],
        confidence="high",
        needs_lawyer=False,
        reason="Grounding confirmed",
    )
    is_valid, missing = validate_citations(valid_ans, retrieved)
    assert is_valid
    assert len(missing) == 0

    fake_ans = LegalAnswer(
        answer="File under fake law",
        citations=[Citation(act="Fictitious Act, 2099", section="Section 999")],
        confidence="high",
        needs_lawyer=False,
        reason="Hallucination",
    )
    is_fake_valid, fake_missing = validate_citations(fake_ans, retrieved)
    assert not is_fake_valid
    assert len(fake_missing) == 1


def test_escalation_rules_detect_criminal_and_large_claims():
    is_esc, _ = check_scope_and_escalation("He assaulted me and stole my car, file an FIR")
    assert is_esc

    is_esc_court, _ = check_scope_and_escalation("I have a court date tomorrow morning")
    assert is_esc_court

    is_esc_amt, _ = check_scope_and_escalation("My claim is for", amount_inr=5000000.0)
    assert is_esc_amt

    is_normal, _ = check_scope_and_escalation("My landlord didn't return 20000 rupees")
    assert not is_normal


def test_document_drafting_creates_docx(tmp_path: Path):
    cf = CaseFile(
        issue_type="deposit",
        parties="Landlord Sharma",
        amount="₹50,000",
        dates="January 2024 to December 2024",
        timeline=["Lease ended Dec 31", "Keys handed Jan 2"],
        evidence=["Bank transfer receipt", "Handover WhatsApp chat"],
        what_user_wants="Full refund of security deposit with interest",
    )
    assert len(cf.timeline) == 2
    out_file = tmp_path / "test_notice.docx"
    generated_path = generate_document(cf, out_file)
    assert Path(generated_path).exists()
    assert Path(generated_path).stat().st_size > 1000
